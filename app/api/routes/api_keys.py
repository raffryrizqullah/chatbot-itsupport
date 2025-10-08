"""
API Key management endpoints (Admin only).

Provides endpoints for creating, listing, and revoking API keys.
All endpoints require admin authentication.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyListResponse,
    ErrorResponse,
)
from app.services import api_key as api_key_service
from app.db.database import get_db
from app.db.models import User, UserRole
from app.core.dependencies import require_role
from app.core.rate_limit import limiter, RATE_LIMITS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["admin", "api-keys"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["api_key_create"])
async def create_api_key(
    request: Request,
    create_request: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> APIKeyCreateResponse:
    """
    Create a new API key for a user (Admin only).

    The API key is only shown once in the response. Make sure to save it!

    Args:
        create_request: API key creation request with user_id and name.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        APIKeyCreateResponse with the full API key (shown only once).

    Raises:
        HTTPException: If user not found or creation fails.
    """
    try:
        api_key, plain_key = await api_key_service.create_api_key(
            db=db,
            user_id=create_request.user_id,
            name=create_request.name,
            admin_id=str(current_user.id),
        )

        logger.info(
            f"Admin {current_user.username} created API key '{create_request.name}' for user {create_request.user_id}"
        )

        return APIKeyCreateResponse(
            id=str(api_key.id),
            key_prefix=api_key.key_prefix,
            name=api_key.name,
            user_id=str(api_key.user_id),
            username=api_key.user.username,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            api_key=plain_key,
        )

    except Exception as e:
        msg = f"Failed to create API key: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.get(
    "/api-keys",
    response_model=APIKeyListResponse,
    tags=["admin", "api-keys"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["api_key_list"])
async def list_api_keys(
    request: Request,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> APIKeyListResponse:
    """
    List all API keys (Admin only).

    Args:
        user_id: Optional user ID to filter API keys.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        APIKeyListResponse with list of API keys.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        api_keys = await api_key_service.list_api_keys(db=db, user_id=user_id)

        api_key_responses = [
            APIKeyResponse(
                id=str(key.id),
                key_prefix=key.key_prefix,
                name=key.name,
                user_id=str(key.user_id),
                username=key.user.username,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
            )
            for key in api_keys
        ]

        logger.info(f"Admin {current_user.username} listed {len(api_keys)} API keys")

        return APIKeyListResponse(
            total=len(api_key_responses),
            api_keys=api_key_responses,
        )

    except Exception as e:
        msg = f"Failed to list API keys: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.get(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
    tags=["admin", "api-keys"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["api_key_list"])
async def get_api_key(
    request: Request,
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> APIKeyResponse:
    """
    Get API key details (Admin only).

    Args:
        key_id: API key ID.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        APIKeyResponse with key details.

    Raises:
        HTTPException: If key not found or retrieval fails.
    """
    try:
        api_key = await api_key_service.get_api_key_by_id(db=db, key_id=key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )

        logger.info(f"Admin {current_user.username} retrieved API key {key_id}")

        return APIKeyResponse(
            id=str(api_key.id),
            key_prefix=api_key.key_prefix,
            name=api_key.name,
            user_id=str(api_key.user_id),
            username=api_key.user.username,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to get API key: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_200_OK,
    tags=["admin", "api-keys"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["api_key_delete"])
async def revoke_api_key(
    request: Request,
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    Revoke (deactivate) an API key (Admin only).

    Args:
        key_id: API key ID to revoke.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        Success message.

    Raises:
        HTTPException: If key not found or revocation fails.
    """
    try:
        success = await api_key_service.revoke_api_key(
            db=db,
            key_id=key_id,
            admin_id=str(current_user.id),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )

        logger.info(f"Admin {current_user.username} revoked API key {key_id}")

        return {
            "message": f"API key {key_id} revoked successfully",
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to revoke API key: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )


@router.get(
    "/users/{user_id}/api-keys",
    response_model=APIKeyListResponse,
    tags=["admin", "api-keys"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["api_key_list"])
async def list_user_api_keys(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> APIKeyListResponse:
    """
    List API keys for a specific user (Admin only).

    Args:
        user_id: User ID to get API keys for.
        db: Database session.
        current_user: Current authenticated admin user.

    Returns:
        APIKeyListResponse with user's API keys.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        api_keys = await api_key_service.list_api_keys(db=db, user_id=user_id)

        api_key_responses = [
            APIKeyResponse(
                id=str(key.id),
                key_prefix=key.key_prefix,
                name=key.name,
                user_id=str(key.user_id),
                username=key.user.username,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
            )
            for key in api_keys
        ]

        logger.info(
            f"Admin {current_user.username} listed {len(api_keys)} API keys for user {user_id}"
        )

        return APIKeyListResponse(
            total=len(api_key_responses),
            api_keys=api_key_responses,
        )

    except Exception as e:
        msg = f"Failed to list user API keys: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
