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
from app.services.langgraph_rag import LangGraphRAGService
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
def get_langgraph_rag() -> LangGraphRAGService:
    """Get or create LangGraph RAG service instance (cached)."""
    return LangGraphRAGService()


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
        logger.info(f"Processing query (LangGraph): {query_req.question[:50]}...")

        # Get or generate session_id for conversation tracking
        session_id = query_req.session_id or f"anon_{uuid.uuid4()}"
        logger.info(f"Using session_id: {session_id}")

        # Get service instances
        langgraph_rag = get_langgraph_rag()
        chat_memory = get_chat_memory()

        # Build metadata filter based on user role for RBAC
        metadata_filter = build_metadata_filter(current_user)
        if current_user:
            logger.info(f"User {current_user.username} ({current_user.role}) - Filter: {metadata_filter}")
        else:
            logger.info(f"Anonymous user - Filter: {metadata_filter}")

        # Check if there's chat history for this session
        chat_history = chat_memory.get_history(session_id)
        has_chat_history = len(chat_history) > 0

        # Call LangGraph RAG service
        # LangGraph automatically handles:
        # - Query rewriting based on chat history
        # - Tool-calling decision (retrieve vs direct answer)
        # - Short-circuiting for greetings
        # - Context-aware answer generation
        result = langgraph_rag.query(
            question=query_req.question,
            thread_id=session_id,  # Maps to LangGraph memory
            metadata_filter=metadata_filter,
        )

        answer = result["answer"]
        langgraph_metadata = result.get("metadata", {})

        # Save to Redis chat memory for backward compatibility
        chat_memory.add_exchange(session_id, query_req.question, answer)
        logger.info(f"Saved conversation exchange to session {session_id}")

        # Build complete metadata response
        response_metadata = {
            "langgraph_enabled": True,
            "used_tools": langgraph_metadata.get("used_tools", False),
            "message_count": langgraph_metadata.get("message_count", 0),
            "has_chat_history": has_chat_history,
        }

        # Add retrieved documents metadata if available
        if "num_documents_retrieved" in langgraph_metadata:
            response_metadata.update({
                "num_documents_retrieved": langgraph_metadata["num_documents_retrieved"],
                "retrieved_documents": langgraph_metadata.get("retrieved_documents", []),
                "source_links": langgraph_metadata.get("source_links", []),
                "similarity_scores": langgraph_metadata.get("similarity_scores", []),
            })

            # Add score summary if available
            if "max_similarity_score" in langgraph_metadata:
                response_metadata.update({
                    "max_similarity_score": langgraph_metadata["max_similarity_score"],
                    "min_similarity_score": langgraph_metadata.get("min_similarity_score"),
                    "avg_similarity_score": langgraph_metadata.get("avg_similarity_score"),
                })

        # Return response
        return QueryResponse(
            answer=answer,
            session_id=session_id,
            metadata=response_metadata,
        )

    except Exception as e:
        msg = f"Query processing failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
