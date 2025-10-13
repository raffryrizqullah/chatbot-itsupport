"""
Unit tests for authentication service.

Tests user authentication, login, and registration flows.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import authenticate_user, login_user, register_user
from app.services.user import create_user
from app.db.models import User, UserRole
from app.core.exceptions import AuthenticationError


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuthenticateUser:
    """Test suite for user authentication."""

    async def test_authenticate_user_success(self, db_session: AsyncSession):
        """Test successful user authentication with correct credentials."""
        # Create user with known password
        password = "SecurePassword123!"
        await create_user(
            db=db_session,
            username="authuser",
            email="auth@example.com",
            password=password,
            full_name="Auth User",
        )

        # Authenticate with correct password
        user = await authenticate_user(db_session, "authuser", password)

        assert user is not None
        assert user.username == "authuser"
        assert user.email == "auth@example.com"
        assert user.is_active is True

    async def test_authenticate_user_wrong_password(self, db_session: AsyncSession):
        """Test authentication fails with wrong password."""
        # Create user
        await create_user(
            db=db_session,
            username="wrongpass",
            email="wrong@example.com",
            password="CorrectPassword123!",
            full_name="Wrong Pass User",
        )

        # Try to authenticate with wrong password
        user = await authenticate_user(db_session, "wrongpass", "WrongPassword456!")

        assert user is None

    async def test_authenticate_user_not_found(self, db_session: AsyncSession):
        """Test authentication fails for non-existent user."""
        user = await authenticate_user(db_session, "nonexistent", "anypassword")

        assert user is None

    async def test_authenticate_user_empty_password(self, db_session: AsyncSession):
        """Test authentication fails with empty password."""
        # Create user
        await create_user(
            db=db_session,
            username="emptypass",
            email="empty@example.com",
            password="ActualPassword123!",
            full_name="Empty Pass User",
        )

        # Try to authenticate with empty password
        user = await authenticate_user(db_session, "emptypass", "")

        assert user is None

    async def test_authenticate_inactive_user(self, db_session: AsyncSession):
        """Test authentication fails for inactive user."""
        # Create user
        user = await create_user(
            db=db_session,
            username="inactive",
            email="inactive@example.com",
            password="Password123!",
            full_name="Inactive User",
        )

        # Deactivate user
        user.is_active = False
        db_session.add(user)
        await db_session.commit()

        # Try to authenticate
        authenticated_user = await authenticate_user(db_session, "inactive", "Password123!")

        # Should return None for inactive user
        assert authenticated_user is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestLoginUser:
    """Test suite for user login flow."""

    async def test_login_user_success(self, db_session: AsyncSession):
        """Test successful user login returns token and user info."""
        # Create user
        password = "LoginPassword123!"
        await create_user(
            db=db_session,
            username="loginuser",
            email="login@example.com",
            password=password,
            full_name="Login User",
            role=UserRole.STUDENT,
        )

        # Login
        result = await login_user(db_session, "loginuser", password)

        assert result is not None
        assert "access_token" in result
        assert "token_type" in result
        assert "user" in result

        # Check token
        assert isinstance(result["access_token"], str)
        assert len(result["access_token"]) > 0
        assert result["token_type"] == "bearer"

        # Check user info
        user_info = result["user"]
        assert user_info["username"] == "loginuser"
        assert user_info["email"] == "login@example.com"
        assert user_info["role"] == "student"

    async def test_login_user_wrong_password(self, db_session: AsyncSession):
        """Test login fails with wrong password."""
        # Create user
        await create_user(
            db=db_session,
            username="loginwrong",
            email="wrong@example.com",
            password="CorrectPassword123!",
            full_name="Login Wrong",
        )

        # Try to login with wrong password
        result = await login_user(db_session, "loginwrong", "WrongPassword456!")

        assert result is None

    async def test_login_user_not_found(self, db_session: AsyncSession):
        """Test login fails for non-existent user."""
        result = await login_user(db_session, "nonexistent", "anypassword")

        assert result is None

    async def test_login_admin_user(self, db_session: AsyncSession):
        """Test login for admin user includes correct role."""
        # Create admin user
        password = "AdminPassword123!"
        await create_user(
            db=db_session,
            username="adminlogin",
            email="admin@example.com",
            password=password,
            full_name="Admin Login",
            role=UserRole.ADMIN,
        )

        # Login
        result = await login_user(db_session, "adminlogin", password)

        assert result is not None
        assert result["user"]["role"] == "admin"

    async def test_login_lecturer_user(self, db_session: AsyncSession):
        """Test login for lecturer user includes correct role."""
        # Create lecturer user
        password = "LecturerPassword123!"
        await create_user(
            db=db_session,
            username="lecturerlogin",
            email="lecturer@example.com",
            password=password,
            full_name="Lecturer Login",
            role=UserRole.LECTURER,
        )

        # Login
        result = await login_user(db_session, "lecturerlogin", password)

        assert result is not None
        assert result["user"]["role"] == "lecturer"


@pytest.mark.unit
@pytest.mark.asyncio
class TestRegisterUser:
    """Test suite for user registration."""

    async def test_register_user_success(self, db_session: AsyncSession):
        """Test successful user registration."""
        user = await register_user(
            db=db_session,
            username="newuser",
            email="new@example.com",
            password="NewPassword123!",
            full_name="New User",
            role=UserRole.STUDENT,
        )

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.role == UserRole.STUDENT
        assert user.is_active is True

    async def test_register_user_with_admin_role(self, db_session: AsyncSession):
        """Test registering user with ADMIN role."""
        user = await register_user(
            db=db_session,
            username="newadmin",
            email="newadmin@example.com",
            password="AdminPassword123!",
            full_name="New Admin",
            role=UserRole.ADMIN,
        )

        assert user is not None
        assert user.role == UserRole.ADMIN

    async def test_register_user_with_lecturer_role(self, db_session: AsyncSession):
        """Test registering user with LECTURER role."""
        user = await register_user(
            db=db_session,
            username="newlecturer",
            email="newlecturer@example.com",
            password="LecturerPassword123!",
            full_name="New Lecturer",
            role=UserRole.LECTURER,
        )

        assert user is not None
        assert user.role == UserRole.LECTURER

    async def test_register_duplicate_username_raises_error(self, db_session: AsyncSession):
        """Test that registering duplicate username raises error."""
        # Register first user
        await register_user(
            db=db_session,
            username="duplicate",
            email="first@example.com",
            password="Password123!",
            full_name="First User",
            role=UserRole.STUDENT,
        )

        # Try to register with same username
        with pytest.raises(AuthenticationError):
            await register_user(
                db=db_session,
                username="duplicate",  # Same username
                email="second@example.com",
                password="Password123!",
                full_name="Second User",
                role=UserRole.STUDENT,
            )

    async def test_register_duplicate_email_raises_error(self, db_session: AsyncSession):
        """Test that registering duplicate email raises error."""
        # Register first user
        await register_user(
            db=db_session,
            username="first",
            email="duplicate@example.com",
            password="Password123!",
            full_name="First User",
            role=UserRole.STUDENT,
        )

        # Try to register with same email
        with pytest.raises(AuthenticationError):
            await register_user(
                db=db_session,
                username="second",
                email="duplicate@example.com",  # Same email
                password="Password123!",
                full_name="Second User",
                role=UserRole.STUDENT,
            )

    async def test_register_user_password_is_hashed(self, db_session: AsyncSession):
        """Test that registered user's password is hashed."""
        password = "PlainPassword123!"
        user = await register_user(
            db=db_session,
            username="hashtest",
            email="hash@example.com",
            password=password,
            full_name="Hash Test",
            role=UserRole.STUDENT,
        )

        assert user.hashed_password != password
        assert len(user.hashed_password) > 0
        # Bcrypt hashes start with $2
        assert user.hashed_password.startswith("$2")
