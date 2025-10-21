"""
User service for CRUD operations.

Handles user creation, retrieval, update, and deletion operations.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, UserRole
from app.core.security import get_password_hash
from app.core.exceptions import AuthenticationError
import logging

logger = logging.getLogger(__name__)


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.

    Args:
        db: Database session.
        username: Username to search for.

    Returns:
        User object if found, None otherwise.
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email.

    Args:
        db: Database session.
        email: Email to search for.

    Returns:
        User object if found, None otherwise.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID.

    Args:
        db: Database session.
        user_id: User ID (UUID string).

    Returns:
        User object if found, None otherwise.
    """
    # Convert string to UUID for SQLAlchemy comparison
    try:
        uuid_obj = UUID(user_id)
    except (ValueError, AttributeError):
        return None

    result = await db.execute(select(User).where(User.id == uuid_obj))
    user = result.scalar_one_or_none()
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.STUDENT,
) -> User:
    """
    Create a new user.

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
    # Check if username exists
    existing_user = await get_user_by_username(db, username)
    if existing_user:
        msg = f"Username {username} already exists"
        logger.error(msg)
        raise AuthenticationError(msg)

    # Check if email exists
    existing_email = await get_user_by_email(db, email)
    if existing_email:
        msg = f"Email {email} already exists"
        logger.error(msg)
        raise AuthenticationError(msg)

    # Create new user
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Created new user: {username} with role {role}")
    return user


async def update_user_role(
    db: AsyncSession, user_id: str, new_role: UserRole
) -> Optional[User]:
    """
    Update user's role.

    Args:
        db: Database session.
        user_id: User ID (UUID string).
        new_role: New role to assign.

    Returns:
        Updated User object if found, None otherwise.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    user.role = new_role
    await db.commit()
    await db.refresh(user)

    logger.info(f"Updated user {user.username} role to {new_role}")
    return user


async def deactivate_user(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Deactivate a user account.

    Args:
        db: Database session.
        user_id: User ID (UUID string).

    Returns:
        Updated User object if found, None otherwise.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    logger.info(f"Deactivated user: {user.username}")
    return user


async def delete_user(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Delete a user from the database.

    Args:
        db: Database session.
        user_id: User ID (UUID string).

    Returns:
        Deleted User object if found, None otherwise.

    Raises:
        AuthenticationError: If attempting to delete the last SUPER_ADMIN.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    # Prevent deleting the last SUPER_ADMIN
    if user.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(User).where(User.role == UserRole.SUPER_ADMIN)
        )
        super_admins = result.scalars().all()

        if len(super_admins) <= 1:
            msg = "Cannot delete the last SUPER_ADMIN user"
            logger.error(msg)
            raise AuthenticationError(msg)

    # Store user info before deletion
    username = user.username

    # Delete user (API keys will be cascade deleted due to ondelete="CASCADE")
    await db.delete(user)
    await db.commit()

    logger.info(f"Deleted user: {username} (ID: {user_id})")
    return user
