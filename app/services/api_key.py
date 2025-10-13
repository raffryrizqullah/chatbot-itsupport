"""
API Key service for CRUD operations.

Handles API key generation, verification, and management operations.
"""

from typing import Optional, List
import secrets
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import APIKey, User
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import APIKeyError
import logging

logger = logging.getLogger(__name__)


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key with OpenAI/Claude-style format.

    Returns:
        Tuple of (plain_key, key_hash, key_prefix).
        - plain_key: Full API key to show to user (``'sk-proj-xxxxx...'``).
        - key_hash: Bcrypt hash of the key for database storage.
        - key_prefix: First 12 characters for display (``'sk-proj-abc...'``).

    Example:
        ```python
        plain_key, key_hash, key_prefix = generate_api_key()
        # plain_key: "sk-proj-abc123def456..."
        # key_prefix: "sk-proj-abc..."
        ```
    """
    # Generate random token (32 bytes = 43 chars base64)
    random_token = secrets.token_urlsafe(32)

    # Format: sk-proj-{random_token}
    plain_key = f"sk-proj-{random_token}"

    # Hash the key for storage
    key_hash = get_password_hash(plain_key)

    # Create prefix for display (first 12 chars + ...)
    key_prefix = plain_key[:12] + "..."

    logger.info(f"Generated new API key with prefix: {key_prefix}")
    return plain_key, key_hash, key_prefix


async def create_api_key(
    db: AsyncSession,
    user_id: str,
    name: str,
    admin_id: str,
) -> tuple[APIKey, str]:
    """
    Create a new API key for a user.

    Args:
        db: Database session.
        user_id: UUID of the user who will own this key.
        name: Descriptive name for the API key.
        admin_id: UUID of the admin creating this key.

    Returns:
        Tuple of (APIKey object, plain_key string).
        The plain_key is only returned once and must be saved by the user.

    Raises:
        APIKeyError: If user not found or key creation fails.
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        msg = f"User {user_id} not found"
        logger.error(msg)
        raise APIKeyError(msg)

    # Generate API key
    plain_key, key_hash, key_prefix = generate_api_key()

    # Create API key record
    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        user_id=user_id,
        created_by=admin_id,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()

    # Refresh with eager loading of user relationship
    await db.refresh(api_key)
    result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user))
        .where(APIKey.id == api_key.id)
    )
    api_key = result.scalar_one()

    logger.info(
        f"Created API key '{name}' for user {user.username} by admin {admin_id}"
    )
    return api_key, plain_key


async def verify_api_key(db: AsyncSession, api_key: str) -> Optional[User]:
    """
    Verify an API key and return the associated user.

    Args:
        db: Database session.
        api_key: Plain API key string to verify.

    Returns:
        User object if key is valid and active, None otherwise.
    """
    if not api_key or not api_key.startswith("sk-proj-"):
        return None

    # Get all active API keys
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()

    # Verify key against each hash
    for key_record in api_keys:
        if verify_password(api_key, key_record.key_hash):
            # Update last_used_at
            key_record.last_used_at = datetime.utcnow()
            await db.commit()

            # Get and return user
            result = await db.execute(
                select(User).where(User.id == key_record.user_id)
            )
            user = result.scalar_one_or_none()

            if user and user.is_active:
                logger.info(
                    f"API key {key_record.key_prefix} verified for user {user.username}"
                )
                return user

    msg = "Invalid or inactive API key attempted"
    logger.warning(msg)
    return None


async def list_api_keys(
    db: AsyncSession, user_id: Optional[str] = None
) -> List[APIKey]:
    """
    List API keys, optionally filtered by user.

    Args:
        db: Database session.
        user_id: Optional user ID to filter by.

    Returns:
        List of APIKey objects with eager-loaded user relationships.
    """
    query = select(APIKey).options(selectinload(APIKey.user))

    if user_id:
        query = query.where(APIKey.user_id == user_id)

    query = query.order_by(APIKey.created_at.desc())

    result = await db.execute(query)
    api_keys = result.scalars().all()

    logger.info(f"Retrieved {len(api_keys)} API keys")
    return api_keys


async def get_api_key_by_id(db: AsyncSession, key_id: str) -> Optional[APIKey]:
    """
    Get API key by ID.

    Args:
        db: Database session.
        key_id: API key ID (UUID string).

    Returns:
        APIKey object with eager-loaded user relationship if found, None otherwise.
    """
    result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user))
        .where(APIKey.id == key_id)
    )
    api_key = result.scalar_one_or_none()
    return api_key


async def revoke_api_key(db: AsyncSession, key_id: str, admin_id: str) -> bool:
    """
    Revoke (deactivate) an API key.

    Args:
        db: Database session.
        key_id: API key ID (UUID string).
        admin_id: UUID of the admin revoking this key.

    Returns:
        True if key was revoked, False if not found.

    Raises:
        APIKeyError: If key revocation fails.
    """
    api_key = await get_api_key_by_id(db, key_id)

    if not api_key:
        return False

    api_key.is_active = False
    await db.commit()

    logger.info(
        f"API key {api_key.key_prefix} ({api_key.name}) revoked by admin {admin_id}"
    )
    return True
