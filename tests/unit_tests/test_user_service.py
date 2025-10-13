"""
Unit tests for user service.

Tests user CRUD operations including creation, retrieval, update, and deactivation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import (
    create_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    update_user_role,
    deactivate_user,
)
from app.db.models import User, UserRole
from app.core.exceptions import AuthenticationError


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateUser:
    """Test suite for user creation."""

    async def test_create_user_success(self, db_session: AsyncSession, fake_username, fake_email, fake_password):
        """Test successful user creation with all required fields."""
        user = await create_user(
            db=db_session,
            username=fake_username,
            email=fake_email,
            password=fake_password,
            full_name="John Doe",
            role=UserRole.STUDENT,
        )

        assert user.username == fake_username
        assert user.email == fake_email
        assert user.full_name == "John Doe"
        assert user.role == UserRole.STUDENT
        assert user.is_active is True
        # Password should be hashed, not plain text
        assert user.hashed_password != fake_password
        assert len(user.hashed_password) > 0

    async def test_create_user_defaults_to_student_role(self, db_session: AsyncSession):
        """Test that user creation defaults to STUDENT role if not specified."""
        user = await create_user(
            db=db_session,
            username="defaultrole",
            email="default@example.com",
            password="Pass123!",
            full_name="Default User",
            # No role specified
        )

        assert user.role == UserRole.STUDENT

    async def test_create_user_with_admin_role(self, db_session: AsyncSession):
        """Test creating user with ADMIN role."""
        user = await create_user(
            db=db_session,
            username="adminuser",
            email="admin@example.com",
            password="AdminPass123!",
            full_name="Admin User",
            role=UserRole.ADMIN,
        )

        assert user.role == UserRole.ADMIN

    async def test_create_user_with_lecturer_role(self, db_session: AsyncSession):
        """Test creating user with LECTURER role."""
        user = await create_user(
            db=db_session,
            username="lectureruser",
            email="lecturer@example.com",
            password="LecPass123!",
            full_name="Lecturer User",
            role=UserRole.LECTURER,
        )

        assert user.role == UserRole.LECTURER

    async def test_create_duplicate_username_raises_error(self, db_session: AsyncSession):
        """Test that creating user with duplicate username raises AuthenticationError."""
        # Create first user
        await create_user(
            db=db_session,
            username="duplicate",
            email="first@example.com",
            password="Pass123!",
            full_name="First User",
        )

        # Try to create second user with same username
        with pytest.raises(AuthenticationError, match="already exists"):
            await create_user(
                db=db_session,
                username="duplicate",  # Same username
                email="second@example.com",  # Different email
                password="Pass123!",
                full_name="Second User",
            )

    async def test_create_duplicate_email_raises_error(self, db_session: AsyncSession):
        """Test that creating user with duplicate email raises AuthenticationError."""
        # Create first user
        await create_user(
            db=db_session,
            username="first",
            email="duplicate@example.com",
            password="Pass123!",
            full_name="First User",
        )

        # Try to create second user with same email
        with pytest.raises(AuthenticationError, match="already exists"):
            await create_user(
                db=db_session,
                username="second",  # Different username
                email="duplicate@example.com",  # Same email
                password="Pass123!",
                full_name="Second User",
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetUser:
    """Test suite for user retrieval operations."""

    async def test_get_user_by_username_success(self, db_session: AsyncSession):
        """Test successful user retrieval by username."""
        # Create user
        created_user = await create_user(
            db=db_session,
            username="findme",
            email="find@example.com",
            password="Pass123!",
            full_name="Find Me",
        )

        # Find user
        found_user = await get_user_by_username(db_session, "findme")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "findme"
        assert found_user.email == "find@example.com"

    async def test_get_user_by_username_not_found(self, db_session: AsyncSession):
        """Test that getting non-existent user by username returns None."""
        result = await get_user_by_username(db_session, "nonexistent")

        assert result is None

    async def test_get_user_by_email_success(self, db_session: AsyncSession):
        """Test successful user retrieval by email."""
        # Create user
        created_user = await create_user(
            db=db_session,
            username="emailtest",
            email="findemail@example.com",
            password="Pass123!",
            full_name="Email Test",
        )

        # Find user by email
        found_user = await get_user_by_email(db_session, "findemail@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "findemail@example.com"

    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test that getting non-existent user by email returns None."""
        result = await get_user_by_email(db_session, "nonexistent@example.com")

        assert result is None

    async def test_get_user_by_id_success(self, db_session: AsyncSession):
        """Test successful user retrieval by ID."""
        # Create user
        created_user = await create_user(
            db=db_session,
            username="idtest",
            email="id@example.com",
            password="Pass123!",
            full_name="ID Test",
        )

        # Find user by ID
        found_user = await get_user_by_id(db_session, str(created_user.id))

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "idtest"

    async def test_get_user_by_id_not_found(self, db_session: AsyncSession):
        """Test that getting non-existent user by ID returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = await get_user_by_id(db_session, fake_id)

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestUpdateUser:
    """Test suite for user update operations."""

    async def test_update_user_role_success(self, db_session: AsyncSession):
        """Test successful user role update."""
        # Create user with STUDENT role
        user = await create_user(
            db=db_session,
            username="roleupdate",
            email="role@example.com",
            password="Pass123!",
            full_name="Role Update",
            role=UserRole.STUDENT,
        )

        assert user.role == UserRole.STUDENT

        # Update to LECTURER
        updated_user = await update_user_role(db_session, str(user.id), UserRole.LECTURER)

        assert updated_user is not None
        assert updated_user.id == user.id
        assert updated_user.role == UserRole.LECTURER

    async def test_update_user_role_to_admin(self, db_session: AsyncSession):
        """Test updating user role to ADMIN."""
        # Create user
        user = await create_user(
            db=db_session,
            username="toadmin",
            email="toadmin@example.com",
            password="Pass123!",
            full_name="To Admin",
            role=UserRole.STUDENT,
        )

        # Update to ADMIN
        updated_user = await update_user_role(db_session, str(user.id), UserRole.ADMIN)

        assert updated_user is not None
        assert updated_user.role == UserRole.ADMIN

    async def test_update_user_role_not_found(self, db_session: AsyncSession):
        """Test that updating non-existent user returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = await update_user_role(db_session, fake_id, UserRole.ADMIN)

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestDeactivateUser:
    """Test suite for user deactivation."""

    async def test_deactivate_user_success(self, db_session: AsyncSession):
        """Test successful user deactivation."""
        # Create active user
        user = await create_user(
            db=db_session,
            username="deactivate",
            email="deactivate@example.com",
            password="Pass123!",
            full_name="Deactivate Me",
        )

        assert user.is_active is True

        # Deactivate user
        deactivated_user = await deactivate_user(db_session, str(user.id))

        assert deactivated_user is not None
        assert deactivated_user.id == user.id
        assert deactivated_user.is_active is False

    async def test_deactivate_user_not_found(self, db_session: AsyncSession):
        """Test that deactivating non-existent user returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = await deactivate_user(db_session, fake_id)

        assert result is None

    async def test_deactivate_already_inactive_user(self, db_session: AsyncSession):
        """Test deactivating already inactive user."""
        # Create and deactivate user
        user = await create_user(
            db=db_session,
            username="alreadyinactive",
            email="inactive@example.com",
            password="Pass123!",
            full_name="Already Inactive",
        )

        # First deactivation
        await deactivate_user(db_session, str(user.id))

        # Second deactivation (should still work)
        deactivated_user = await deactivate_user(db_session, str(user.id))

        assert deactivated_user is not None
        assert deactivated_user.is_active is False
