"""
Chat history management endpoints.

Provides endpoints for viewing and managing conversation history stored in Redis.
"""

from typing import List, Dict, Any, Optional
from functools import lru_cache
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from app.models.schemas import ErrorResponse
from app.services.chat_memory import ChatMemoryService
from app.core.rate_limit import limiter, RATE_LIMITS
from app.core.dependencies import require_role
from app.db.models import UserRole
from pydantic import BaseModel, Field
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache()
def get_chat_memory() -> ChatMemoryService:
    """Get or create chat memory service instance (cached)."""
    return ChatMemoryService()


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""

    session_id: str = Field(..., description="Session identifier")
    messages: List[Dict[str, str]] = Field(..., description="List of messages with role and content")
    message_count: int = Field(..., description="Number of messages in history")
    ttl: int = Field(..., description="Time to live in seconds")


class SessionInfoResponse(BaseModel):
    """Response schema for session information."""

    session_id: str = Field(..., description="Session identifier")
    exists: bool = Field(..., description="Whether session exists")
    message_count: int = Field(..., description="Number of messages")
    ttl: int | None = Field(None, description="Time to live in seconds (None if expired)")


class ClearHistoryResponse(BaseModel):
    """Response schema for clearing chat history."""

    session_id: str = Field(..., description="Session identifier")
    success: bool = Field(..., description="Whether history was cleared")
    message: str = Field(..., description="Status message")


class SessionListResponse(BaseModel):
    """Response schema for session listing."""

    sessions: List[str] = Field(..., description="List of session identifiers")
    total: int = Field(..., description="Total number of sessions returned")


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    tags=["chat"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["chat_history"])
async def list_sessions(
    request: Request,
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=1000,
        description="Maximum number of session IDs to return",
    ),
) -> SessionListResponse:
    """
    List session identifiers stored in chat history.

    Args:
        limit: Optional maximum number of sessions to return.

    Returns:
        SessionListResponse containing session IDs and count.
    """
    try:
        chat_memory = get_chat_memory()
        sessions = chat_memory.list_sessions(limit=limit)

        return SessionListResponse(
            sessions=sessions,
            total=len(sessions),
        )

    except Exception as e:
        msg = f"Failed to list chat sessions: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    tags=["chat"],
    responses={
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["chat_history"])
async def get_chat_history(request: Request, session_id: str) -> ChatHistoryResponse:
    """
    Get chat history for a specific session.

    Args:
        session_id: Session identifier to retrieve history for.

    Returns:
        ChatHistoryResponse with message history and metadata.

    Raises:
        HTTPException: If session not found or retrieval fails.
    """
    try:
        chat_memory = get_chat_memory()

        # Get session info
        info = chat_memory.get_session_info(session_id)

        if not info["exists"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found or expired",
            )

        # Get history
        messages = chat_memory.get_history(session_id)

        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")

        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            message_count=len(messages),
            ttl=info["ttl"] or 0,
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to retrieve chat history: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.get(
    "/session/{session_id}",
    response_model=SessionInfoResponse,
    tags=["chat"],
    responses={
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["chat_history"])
async def get_session_info(request: Request, session_id: str) -> SessionInfoResponse:
    """
    Get information about a chat session.

    Args:
        session_id: Session identifier to get info for.

    Returns:
        SessionInfoResponse with session metadata.

    Raises:
        HTTPException: If retrieval fails.
    """
    try:
        chat_memory = get_chat_memory()
        info = chat_memory.get_session_info(session_id)

        logger.info(f"Retrieved session info for {session_id}: {info}")

        return SessionInfoResponse(
            session_id=session_id,
            exists=info["exists"],
            message_count=info["message_count"],
            ttl=info["ttl"],
        )

    except Exception as e:
        msg = f"Failed to get session info: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.delete(
    "/history/{session_id}",
    response_model=ClearHistoryResponse,
    tags=["chat"],
    responses={
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["chat_history"])
async def clear_chat_history(request: Request, session_id: str) -> ClearHistoryResponse:
    """
    Clear chat history for a specific session.

    Args:
        session_id: Session identifier to clear history for.

    Returns:
        ClearHistoryResponse with status information.

    Raises:
        HTTPException: If clearing fails.
    """
    try:
        chat_memory = get_chat_memory()
        success = chat_memory.clear_history(session_id)

        message = (
            f"Successfully cleared history for session {session_id}"
            if success
            else f"No history found for session {session_id}"
        )

        logger.info(message)

        return ClearHistoryResponse(
            session_id=session_id,
            success=success,
            message=message,
        )

    except Exception as e:
        msg = f"Failed to clear chat history: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
