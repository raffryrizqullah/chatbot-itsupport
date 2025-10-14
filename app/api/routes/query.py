"""
Query endpoints for RAG-based question answering.

Handles user queries against indexed documents using retrieval-augmented generation.
"""

from typing import Union, Optional, Dict, Any, List
from functools import lru_cache
import uuid
from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryWithSourcesResponse,
    ErrorResponse,
)
from app.services.vectorstore import VectorStoreService
from app.services.rag_chain import RAGChainService
from app.services.chat_memory import ChatMemoryService
from app.core.dependencies import get_current_user_flexible
from app.core.rate_limit import limiter, RATE_LIMITS
from app.db.models import User, UserRole
from app.utils.intent import is_smalltalk, wants_sources
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache()
def get_vectorstore() -> VectorStoreService:
    """Get or create vectorstore service instance (cached)."""
    return VectorStoreService()


@lru_cache()
def get_rag_chain() -> RAGChainService:
    """Get or create RAG chain service instance (cached)."""
    return RAGChainService()


@lru_cache()
def get_chat_memory() -> ChatMemoryService:
    """Get or create chat memory service instance (cached)."""
    return ChatMemoryService()


def build_metadata_filter(user: Optional[User]) -> Optional[Dict[str, Any]]:
    """
    Build metadata filter based on user role.

    Args:
        user: Current authenticated user (None for anonymous).

    Returns:
        Metadata filter dictionary for Pinecone search, or None for no filtering.

    Rules:
        - Admin: Access all data (no filter)
        - Lecturer: Access public + internal data
        - Student/Anonymous: Access public data only
    """
    if not user:
        # Anonymous user - only public data
        return {"sensitivity": "public"}

    if user.role == UserRole.ADMIN:
        # Admin - no filter, access all
        return None
    elif user.role == UserRole.LECTURER:
        # Lecturer - public and internal
        return {"sensitivity": {"$in": ["public", "internal"]}}
    else:
        # Student - public only
        return {"sensitivity": "public"}


@router.post(
    "/query",
    response_model=Union[QueryResponse, QueryWithSourcesResponse],
    tags=["query"],
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["query"])
async def query_documents(
    request: Request,
    query_req: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_flexible),
) -> Union[QueryResponse, QueryWithSourcesResponse]:
    """
    Query indexed documents with a question.

    Retrieves relevant document chunks and generates an answer using RAG.
    Supports conversation history via session_id for multi-turn conversations.

    **Authentication**: Supports both JWT token and API key.
    - **JWT Token**: `Authorization: Bearer <token>`
    - **API Key**: `X-API-Key: sk-proj-xxxxx`

    **Role-Based Data Access**:
    - Anonymous/Student: Public data only
    - Lecturer: Public + Internal data
    - Admin: All data

    Args:
        request: Query request with question and optional parameters.
        current_user: Current authenticated user (optional, supports JWT or API key).

    Returns:
        QueryResponse with generated answer and metadata.

    Raises:
        HTTPException: If query processing fails.
    """
    try:
        logger.info(f"Processing query: {query_req.question[:50]}...")

        # Get or generate session_id for conversation tracking
        session_id = query_req.session_id or f"anon_{uuid.uuid4()}"
        logger.info(f"Using session_id: {session_id}")

        # Get service instances
        vectorstore = get_vectorstore()
        rag_chain = get_rag_chain()
        chat_memory = get_chat_memory()

        # Load chat history from Redis
        chat_history = chat_memory.get_history(session_id)
        logger.info(f"Loaded {len(chat_history)} messages from chat history")

        # Build metadata filter based on user role
        metadata_filter = build_metadata_filter(current_user)
        if current_user:
            logger.info(f"User {current_user.username} ({current_user.role}) - Filter: {metadata_filter}")
        else:
            logger.info(f"Anonymous user - Filter: {metadata_filter}")

        # Retrieve relevant documents with role-based filtering
        k = query_req.top_k if query_req.top_k is not None else None
        retrieved_docs, summary_docs = vectorstore.search(
            query_req.question,
            k=k,
            metadata_filter=metadata_filter,
            return_metadata=True,
            include_scores=True,
        )
        retrieved_documents_metadata = []
        similarity_scores: List[float] = []
        for summary_doc in summary_docs:
            doc_metadata = getattr(summary_doc, "metadata", None)
            if not doc_metadata:
                continue
            score = doc_metadata.get("similarity_score")
            if isinstance(score, (int, float)):
                similarity_scores.append(score)
            retrieved_documents_metadata.append(
                {
                    "document_id": doc_metadata.get("document_id"),
                    "document_name": doc_metadata.get("document_name"),
                    "source_link": doc_metadata.get("source_link"),
                    "content_type": doc_metadata.get("content_type"),
                    "similarity_score": score,
                }
            )

        # Collect unique source links (preserve order)
        source_links = []
        seen_links = set()
        for item in retrieved_documents_metadata:
            link = item.get("source_link")
            if link and link not in seen_links:
                seen_links.add(link)
                source_links.append(link)

        # Check if no documents found - could be due to authorization or truly no data
        from app.core.config import settings
        if not retrieved_docs:
            # Double-check: is data restricted or truly non-existent?
            # Only check if user has restrictions (Student/Anonymous) and feature is enabled
            should_check_authorization = (
                settings.rag_enable_authorization_check
                and current_user
                and current_user.role in [UserRole.STUDENT]
            )

            if should_check_authorization:
                logger.info("No docs found with filter, checking if data exists without filter...")
                try:
                    unrestricted_docs, _ = vectorstore.search(
                        query_req.question,
                        k=1,
                        metadata_filter=None,  # No filter - check if data exists
                        return_metadata=False,
                        include_scores=False,
                    )

                    if unrestricted_docs:
                        # Data exists but user doesn't have access
                        msg = f"Access denied: User {current_user.username} ({current_user.role}) attempted to access restricted data"
                        logger.warning(msg)
                        answer = "Maaf, pertanyaan Anda memerlukan akses ke data internal yang tidak tersedia untuk role Anda. Silakan hubungi administrator atau dosen jika Anda memerlukan akses."

                        chat_memory.add_exchange(session_id, query_req.question, answer)

                        return QueryResponse(
                            answer=answer,
                            session_id=session_id,
                            metadata={
                                "num_documents_retrieved": 0,
                                "include_sources": query_req.include_sources,
                                "has_chat_history": len(chat_history) > 0,
                                "retrieved_documents": [],
                                "similarity_scores": [],
                                "rejection_reason": "insufficient_permissions",
                            },
                        )
                except Exception as e:
                    logger.error(f"Error during authorization check: {str(e)}")
                    # Continue with normal "no documents found" response

            # Normal "no documents found" response
            msg = "No relevant documents found"
            logger.warning(msg)
            answer = "Maaf, saya tidak menemukan informasi yang relevan dalam knowledge base untuk menjawab pertanyaan Anda."

            # Save to chat history even for no results
            chat_memory.add_exchange(session_id, query_req.question, answer)

            return QueryResponse(
                answer=answer,
                session_id=session_id,
                metadata={
                    "num_documents_retrieved": 0,
                    "include_sources": query_req.include_sources,
                    "has_chat_history": len(chat_history) > 0,
                    "retrieved_documents": [],
                    "similarity_scores": [],
                    "rejection_reason": "no_documents_found",
                },
            )

        # Check similarity score threshold - reject if max score too low
        if similarity_scores and max(similarity_scores) < settings.rag_similarity_threshold:
            msg = f"No relevant documents found (max similarity: {max(similarity_scores):.2f} < threshold: {settings.rag_similarity_threshold})"
            logger.warning(msg)
            answer = "Maaf, saya tidak menemukan informasi yang cukup relevan dalam knowledge base untuk menjawab pertanyaan Anda."

            # Save to chat history
            chat_memory.add_exchange(session_id, query_req.question, answer)

            return QueryResponse(
                answer=answer,
                session_id=session_id,
                metadata={
                    "num_documents_retrieved": len(retrieved_docs),
                    "include_sources": query_req.include_sources,
                    "has_chat_history": len(chat_history) > 0,
                    "retrieved_documents": retrieved_documents_metadata,
                    "similarity_scores": similarity_scores,
                    "max_similarity_score": max(similarity_scores),
                    "avg_similarity_score": sum(similarity_scores) / len(similarity_scores),
                    "rejection_reason": "low_similarity",
                },
            )

        # Generate answer with or without chat history
        if chat_history:
            # Use history-aware generation
            result = rag_chain.generate_answer_with_history(
                query_req.question, retrieved_docs, chat_history
            )
        else:
            # First message in conversation
            if query_req.include_sources:
                result = rag_chain.generate_answer_with_sources(
                    query_req.question, retrieved_docs
                )
            else:
                result = rag_chain.generate_answer(query_req.question, retrieved_docs)

        # Decide whether to append sources inline in the answer text
        add_sources = (query_req.include_sources or wants_sources(query_req.question)) and not is_smalltalk(query_req.question)

        # Append source links directly into the answer text, if applicable
        if add_sources and source_links:
            sources_block = "\n\nSumber:\n" + "\n".join([f"- {link}" for link in source_links])
            result["answer"] = f"{result['answer']}{sources_block}"

        # Save conversation exchange to Redis
        chat_memory.add_exchange(session_id, query_req.question, result["answer"])
        logger.info(f"Saved conversation exchange to session {session_id}")

        score_summary: Dict[str, Any] = {
            "similarity_scores": similarity_scores,
        }
        if similarity_scores:
            score_summary.update(
                {
                    "max_similarity_score": max(similarity_scores),
                    "min_similarity_score": min(similarity_scores),
                    "avg_similarity_score": sum(similarity_scores) / len(similarity_scores),
                }
            )

        # Return response based on include_sources
        if query_req.include_sources and "sources" in result:
            return QueryWithSourcesResponse(
                answer=result["answer"],
                session_id=session_id,
                sources=result["sources"],
                metadata={
                    **result["metadata"],
                    "num_documents_retrieved": len(retrieved_docs),
                    "retrieved_documents": retrieved_documents_metadata,
                    "source_links": source_links,
                    **score_summary,
                },
            )
        else:
            return QueryResponse(
                answer=result["answer"],
                session_id=session_id,
                metadata={
                    **result.get("context", result.get("metadata", {})),
                    "num_documents_retrieved": len(retrieved_docs),
                    "retrieved_documents": retrieved_documents_metadata,
                    "source_links": source_links,
                    **score_summary,
                },
            )

    except Exception as e:
        msg = f"Query processing failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
