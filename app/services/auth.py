"""
Authentication service.

Handles user authentication, login, and token generation.
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, UserRole
from app.services.user import get_user_by_username, create_user
from app.core.security import verify_password, create_access_token
import logging

logger = logging.getLogger(__name__)


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """
    Authenticate user with username and password.

    Args:
        db: Database session.
        username: Username to authenticate.
        password: Plain text password to verify.

    Returns:
        User object if authentication successful, None otherwise.
    """
    user = await get_user_by_username(db, username)
    if not user:
        logger.warning(f"Authentication failed: User {username} not found")
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Invalid password for {username}")
        return None

    if not user.is_active:
        logger.warning(f"Authentication failed: User {username} is inactive")
        return None

    logger.info(f"User {username} authenticated successfully")
    return user


async def login_user(db: AsyncSession, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Login user and generate access token.

    Args:
        db: Database session.
        username: Username to login.
        password: Plain text password.

    Returns:
        Dictionary with access token and user info if successful, None otherwise.
        Format: ``{'access_token': str, 'token_type': 'bearer', 'user': {...}}``
    """
    user = await authenticate_user(db, username, password)
    if not user:
        return None

    # Create JWT access token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
        },
    }


async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.STUDENT,
) -> User:
    """
    Register a new user.

    Args:
        db: Database session.
        username: Unique username.
        email: Unique email address.
        password: Plain text password (will be hashed).
        full_name: User's full name.
        role: User role (defaults to STUDENT).

    Returns:
        Created User object.

    Raises:
        Exception: If username or email already exists.
    """
    user = await create_user(
        db=db,
        username=username,
        email=email,
        password=password,
        full_name=full_name,
        role=role,
    )

    logger.info(f"New user registered: {username}")
    return user
