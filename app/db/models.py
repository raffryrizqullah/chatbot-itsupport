"""
SQLAlchemy ORM models for database tables.

Defines User and APIKey models with authentication and role-based access control.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration for access control."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    LECTURER = "LECTURER"
    STUDENT = "STUDENT"


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


class APIKey(Base):
    """
    API Key model for programmatic access to the API.

    API keys are created by admins and assigned to users for authentication
    in API requests. Keys are hashed before storage for security.

    Attributes:
        id: Unique API key identifier (UUID).
        key_hash: Bcrypt hash of the API key.
        key_prefix: First 12 characters of key for display (``'sk-proj-abc...'``).
        name: Descriptive name for the API key (e.g., ``'Chatbot Website'``).
        user_id: Foreign key to the user who owns this key.
        is_active: Whether the API key is active and can be used.
        created_at: Timestamp when API key was created.
        last_used_at: Timestamp when API key was last used (nullable).
        created_by: Foreign key to the admin user who created this key.
    """

    __tablename__ = "api_keys"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="api_keys")
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        """String representation of APIKey."""
        return f"<APIKey(prefix={self.key_prefix}, user={self.user_id}, active={self.is_active})>"
