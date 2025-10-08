"""
Query endpoints for RAG-based question answering.

Handles user queries against indexed documents using retrieval-augmented generation.
"""

from typing import Union, Optional, Dict, Any
from functools import lru_cache
import uuid
from fastapi import APIRouter, HTTPException, status, Depends
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
from app.db.models import User, UserRole
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
        500: {"model": ErrorResponse},
    },
)
async def query_documents(
    request: QueryRequest,
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
        logger.info(f"Processing query: {request.question[:50]}...")

        # Get or generate session_id for conversation tracking
        session_id = request.session_id or f"anon_{uuid.uuid4()}"
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
        k = request.top_k if request.top_k is not None else None
        retrieved_docs = vectorstore.search(request.question, k=k, metadata_filter=metadata_filter)

        if not retrieved_docs:
            logger.warning("No relevant documents found")
            answer = "I couldn't find any relevant information to answer your question."

            # Save to chat history even for no results
            chat_memory.add_exchange(session_id, request.question, answer)

            return QueryResponse(
                answer=answer,
                session_id=session_id,
                metadata={
                    "num_documents_retrieved": 0,
                    "include_sources": request.include_sources,
                    "has_chat_history": len(chat_history) > 0,
                },
            )

        # Generate answer with or without chat history
        if chat_history:
            # Use history-aware generation
            result = rag_chain.generate_answer_with_history(
                request.question, retrieved_docs, chat_history
            )
        else:
            # First message in conversation
            if request.include_sources:
                result = rag_chain.generate_answer_with_sources(
                    request.question, retrieved_docs
                )
            else:
                result = rag_chain.generate_answer(request.question, retrieved_docs)

        # Save conversation exchange to Redis
        chat_memory.add_exchange(session_id, request.question, result["answer"])
        logger.info(f"Saved conversation exchange to session {session_id}")

        # Return response based on include_sources
        if request.include_sources and "sources" in result:
            return QueryWithSourcesResponse(
                answer=result["answer"],
                session_id=session_id,
                sources=result["sources"],
                metadata={
                    **result["metadata"],
                    "num_documents_retrieved": len(retrieved_docs),
                },
            )
        else:
            return QueryResponse(
                answer=result["answer"],
                session_id=session_id,
                metadata={
                    **result.get("context", result.get("metadata", {})),
                    "num_documents_retrieved": len(retrieved_docs),
                },
            )

    except Exception as e:
        msg = f"Query processing failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
