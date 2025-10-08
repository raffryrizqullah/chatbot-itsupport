"""
Dependency injection for FastAPI routes.

This module provides reusable dependencies for API endpoints including
authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import User, UserRole
from app.core.security import decode_access_token
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def get_settings():
    """
    Get application settings.

    Returns:
        Settings instance with all configuration values.
    """
    return settings


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token.
        db: Database session.

    Returns:
        User object if authenticated, None if no token provided.

    Raises:
        HTTPException: If token is invalid or user not found.

    Usage:
        ```python
        @router.get("/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            return {"username": user.username}
        ```
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    logger.info(f"Authenticated user: {user.username} (role: {user.role})")
    return user


async def get_current_active_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Get current active user, requiring authentication.

    Args:
        user: Current user from get_current_user dependency.

    Returns:
        User object.

    Raises:
        HTTPException: If user is not authenticated.

    Usage:
        ```python
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            return {"message": f"Hello {user.username}"}
        ```
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for requiring specific user roles.

    Args:
        allowed_roles: One or more UserRole values that are allowed.

    Returns:
        Dependency function that checks user role.

    Usage:
        ```python
        @router.post("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_route():
            return {"message": "Admin access"}

        @router.get("/lecturer-student", dependencies=[Depends(require_role(UserRole.LECTURER, UserRole.STUDENT))])
        async def multi_role_route():
            return {"message": "Lecturer or student access"}
        ```
    """

    async def role_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in allowed_roles)}",
            )
        logger.info(f"Role check passed for user {user.username}: {user.role}")
        return user

    return role_checker
