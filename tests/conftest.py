"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures for unit and integration tests,
including database session, mock Redis client, and test data factories.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock
from faker import Faker

from app.db.models import Base, User, UserRole
from app.core.security import get_password_hash

# Initialize Faker for generating test data
fake = Faker()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests.

    Yields:
        Event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """
    Create in-memory SQLite database engine for testing.

    Returns:
        Async database engine configured for testing.
    """
    # Use in-memory SQLite for fast tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for tests.

    Args:
        db_engine: Database engine fixture.

    Yields:
        Async database session.
    """
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis():
    """
    Create mock Redis client for testing.

    Returns:
        Mocked Redis client with common methods.
    """
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    mock.ttl.return_value = -1
    return mock


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """
    Create a sample user for testing.

    Args:
        db_session: Database session fixture.

    Returns:
        Created User object.
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("SecurePassword123!"),
        full_name="Test User",
        role=UserRole.STUDENT,
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """
    Create an admin user for testing.

    Args:
        db_session: Database session fixture.

    Returns:
        Created admin User object.
    """
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def lecturer_user(db_session: AsyncSession) -> User:
    """
    Create a lecturer user for testing.

    Args:
        db_session: Database session fixture.

    Returns:
        Created lecturer User object.
    """
    user = User(
        username="lecturer",
        email="lecturer@example.com",
        hashed_password=get_password_hash("LecturerPass123!"),
        full_name="Lecturer User",
        role=UserRole.LECTURER,
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def fake_password() -> str:
    """
    Generate a secure fake password for testing.

    Returns:
        Random password string.
    """
    return fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)


@pytest.fixture
def fake_email() -> str:
    """
    Generate a fake email address for testing.

    Returns:
        Random email address.
    """
    return fake.email()


@pytest.fixture
def fake_username() -> str:
    """
    Generate a fake username for testing.

    Returns:
        Random username.
    """
    return fake.user_name()


@pytest.fixture
def fake_full_name() -> str:
    """
    Generate a fake full name for testing.

    Returns:
        Random full name.
    """
    return fake.name()
