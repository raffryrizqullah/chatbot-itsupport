"""
Unit tests for API key service.

Tests API key generation, verification, creation, and revocation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.services.api_key import (
    generate_api_key,
    create_api_key,
    verify_api_key,
    list_api_keys,
    get_api_key_by_id,
    revoke_api_key,
)
from app.services.user import create_user
from app.db.models import APIKey, UserRole


@pytest.mark.unit
class TestGenerateAPIKey:
    """Test suite for API key generation."""

    def test_generate_api_key_returns_tuple(self):
        """Test that generate_api_key returns a tuple of three strings."""
        plain_key, key_hash, key_prefix = generate_api_key()

        assert isinstance(plain_key, str)
        assert isinstance(key_hash, str)
        assert isinstance(key_prefix, str)

    def test_generate_api_key_format(self):
        """Test that generated API key has correct format (sk-proj-xxx)."""
        plain_key, _, _ = generate_api_key()

        assert plain_key.startswith("sk-proj-")
        assert len(plain_key) > len("sk-proj-")

    def test_generate_api_key_prefix_length(self):
        """Test that key prefix has expected length."""
        _, _, key_prefix = generate_api_key()

        # Prefix should be first few characters (e.g., "sk-proj-abc")
        assert key_prefix.startswith("sk-proj-")
        assert len(key_prefix) < 30  # Prefix should be shorter than full key

    def test_generate_api_key_hash_is_different_from_plain(self):
        """Test that hash is different from plain key."""
        plain_key, key_hash, _ = generate_api_key()

        assert plain_key != key_hash
        assert len(key_hash) > 0

    def test_generate_multiple_keys_are_unique(self):
        """Test that generating multiple keys produces unique results."""
        key1, hash1, prefix1 = generate_api_key()
        key2, hash2, prefix2 = generate_api_key()

        assert key1 != key2
        assert hash1 != hash2
        # Prefixes might be same or different depending on random generation

    def test_generate_api_key_hash_is_bcrypt(self):
        """Test that hash uses bcrypt format."""
        _, key_hash, _ = generate_api_key()

        # Bcrypt hashes start with $2
        assert key_hash.startswith("$2")


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateAPIKey:
    """Test suite for API key creation in database."""

    async def test_create_api_key_success(self, db_session: AsyncSession, sample_user, admin_user):
        """Test successful API key creation."""
        api_key, plain_key = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Test API Key",
            admin_id=str(admin_user.id),
        )

        assert api_key is not None
        assert api_key.name == "Test API Key"
        assert api_key.user_id == sample_user.id
        assert api_key.created_by == admin_user.id
        assert api_key.is_active is True
        assert api_key.key_prefix.startswith("sk-proj-")

        # Plain key should be returned
        assert plain_key.startswith("sk-proj-")
        assert len(plain_key) > 20

    async def test_create_api_key_for_different_user(self, db_session: AsyncSession, lecturer_user, admin_user):
        """Test creating API key for lecturer user."""
        api_key, _ = await create_api_key(
            db=db_session,
            user_id=str(lecturer_user.id),
            name="Lecturer API Key",
            admin_id=str(admin_user.id),
        )

        assert api_key is not None
        assert api_key.user_id == lecturer_user.id
        assert api_key.created_by == admin_user.id

    async def test_create_multiple_api_keys_for_same_user(self, db_session: AsyncSession, sample_user, admin_user):
        """Test creating multiple API keys for the same user."""
        # Create first key
        key1, _ = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="First Key",
            admin_id=str(admin_user.id),
        )

        # Create second key
        key2, _ = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Second Key",
            admin_id=str(admin_user.id),
        )

        assert key1.id != key2.id
        assert key1.name != key2.name
        assert key1.user_id == key2.user_id


@pytest.mark.unit
@pytest.mark.asyncio
class TestVerifyAPIKey:
    """Test suite for API key verification."""

    async def test_verify_api_key_valid(self, db_session: AsyncSession, sample_user, admin_user):
        """Test verifying a valid API key returns user."""
        # Create API key
        _, plain_key = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Verification Test",
            admin_id=str(admin_user.id),
        )

        # Verify the key
        user = await verify_api_key(db_session, plain_key)

        assert user is not None
        assert user.id == sample_user.id
        assert user.username == sample_user.username

    async def test_verify_api_key_invalid(self, db_session: AsyncSession):
        """Test verifying invalid API key returns None."""
        invalid_key = "sk-proj-invalidkeyhere"
        user = await verify_api_key(db_session, invalid_key)

        assert user is None

    async def test_verify_api_key_inactive(self, db_session: AsyncSession, sample_user, admin_user):
        """Test verifying inactive API key returns None."""
        # Create API key
        api_key, plain_key = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Inactive Test",
            admin_id=str(admin_user.id),
        )

        # Deactivate the key
        api_key.is_active = False
        db_session.add(api_key)
        await db_session.commit()

        # Try to verify inactive key
        user = await verify_api_key(db_session, plain_key)

        assert user is None

    async def test_verify_api_key_wrong_format(self, db_session: AsyncSession):
        """Test verifying key with wrong format returns None."""
        wrong_key = "not-an-api-key"
        user = await verify_api_key(db_session, wrong_key)

        assert user is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestListAPIKeys:
    """Test suite for listing API keys."""

    async def test_list_all_api_keys(self, db_session: AsyncSession, sample_user, admin_user):
        """Test listing all API keys."""
        # Create multiple keys
        await create_api_key(db_session, str(sample_user.id), "Key 1", str(admin_user.id))
        await create_api_key(db_session, str(sample_user.id), "Key 2", str(admin_user.id))

        # List all keys
        keys = await list_api_keys(db_session)

        assert len(keys) >= 2
        assert all(isinstance(key, APIKey) for key in keys)

    async def test_list_api_keys_for_specific_user(self, db_session: AsyncSession, sample_user, lecturer_user, admin_user):
        """Test listing API keys for specific user."""
        # Create keys for different users
        await create_api_key(db_session, str(sample_user.id), "User Key 1", str(admin_user.id))
        await create_api_key(db_session, str(sample_user.id), "User Key 2", str(admin_user.id))
        await create_api_key(db_session, str(lecturer_user.id), "Lecturer Key", str(admin_user.id))

        # List keys for sample_user only
        user_keys = await list_api_keys(db_session, user_id=str(sample_user.id))

        assert len(user_keys) == 2
        assert all(key.user_id == sample_user.id for key in user_keys)

    async def test_list_api_keys_empty(self, db_session: AsyncSession):
        """Test listing API keys when none exist."""
        keys = await list_api_keys(db_session)

        assert keys == []


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetAPIKeyByID:
    """Test suite for retrieving API key by ID."""

    async def test_get_api_key_by_id_success(self, db_session: AsyncSession, sample_user, admin_user):
        """Test successfully retrieving API key by ID."""
        # Create API key
        created_key, _ = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Get by ID Test",
            admin_id=str(admin_user.id),
        )

        # Retrieve by ID
        retrieved_key = await get_api_key_by_id(db_session, str(created_key.id))

        assert retrieved_key is not None
        assert retrieved_key.id == created_key.id
        assert retrieved_key.name == "Get by ID Test"

    async def test_get_api_key_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving non-existent API key returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        key = await get_api_key_by_id(db_session, fake_id)

        assert key is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestRevokeAPIKey:
    """Test suite for revoking API keys."""

    async def test_revoke_api_key_success(self, db_session: AsyncSession, sample_user, admin_user):
        """Test successfully revoking an API key."""
        # Create API key
        api_key, _ = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Revoke Test",
            admin_id=str(admin_user.id),
        )

        assert api_key.is_active is True

        # Revoke the key
        result = await revoke_api_key(db_session, str(api_key.id), str(admin_user.id))

        assert result is True

        # Verify key is inactive
        revoked_key = await get_api_key_by_id(db_session, str(api_key.id))
        assert revoked_key.is_active is False

    async def test_revoke_api_key_not_found(self, db_session: AsyncSession, admin_user):
        """Test revoking non-existent API key returns False."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = await revoke_api_key(db_session, fake_id, str(admin_user.id))

        assert result is False

    async def test_revoke_already_revoked_key(self, db_session: AsyncSession, sample_user, admin_user):
        """Test revoking already revoked key."""
        # Create and revoke API key
        api_key, _ = await create_api_key(
            db=db_session,
            user_id=str(sample_user.id),
            name="Double Revoke Test",
            admin_id=str(admin_user.id),
        )

        # First revocation
        await revoke_api_key(db_session, str(api_key.id), str(admin_user.id))

        # Second revocation (should still return True)
        result = await revoke_api_key(db_session, str(api_key.id), str(admin_user.id))

        assert result is True

        # Verify still inactive
        revoked_key = await get_api_key_by_id(db_session, str(api_key.id))
        assert revoked_key.is_active is False
