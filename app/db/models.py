"""
SQLAlchemy ORM models for database tables.

Defines User model with authentication and role-based access control.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum
from app.db.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration for access control."""

    ADMIN = "admin"
    LECTURER = "lecturer"
    STUDENT = "student"


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Unique user identifier (UUID).
        username: Unique username for login.
        email: Unique email address.
        hashed_password: Bcrypt hashed password.
        full_name: User's full name.
        role: User role (admin, lecturer, student).
        is_active: Whether user account is active.
        created_at: Timestamp when user was created.
        updated_at: Timestamp when user was last updated.
    """

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        SQLEnum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.STUDENT,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(username={self.username}, role={self.role})>"
