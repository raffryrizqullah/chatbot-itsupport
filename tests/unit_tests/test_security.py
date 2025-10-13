"""
Unit tests for security utilities.

Tests password hashing, verification, and JWT token operations.
"""

import pytest
from datetime import timedelta
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test suite for password hashing and verification."""

    def test_password_hashing_creates_different_hashes(self):
        """Test that hashing same password twice produces different hashes due to salt."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to bcrypt salt
        assert hash1 != hash2
        # But both should verify the password
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_fails_with_wrong_password(self):
        """Test password verification fails with incorrect password."""
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(correct_password)

        assert verify_password(wrong_password, hashed) is False

    def test_password_verification_fails_with_empty_password(self):
        """Test password verification fails with empty password."""
        password = "NotEmpty123!"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_hashed_password_is_string(self):
        """Test that hashed password is a string."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hashed_password_starts_with_bcrypt_identifier(self):
        """Test that hashed password uses bcrypt format."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Bcrypt hashes start with $2b$ or $2a$ or $2y$
        assert hashed.startswith("$2")


@pytest.mark.unit
class TestJWTToken:
    """Test suite for JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123", "role": "student"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT has 3 parts separated by dots
        assert token.count(".") == 2

    def test_decode_access_token_success(self):
        """Test successful JWT token decoding."""
        data = {"sub": "user456", "role": "admin", "custom": "value"}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "user456"
        assert decoded["role"] == "admin"
        assert decoded["custom"] == "value"
        assert "exp" in decoded  # Expiration should be added

    def test_decode_access_token_contains_expiration(self):
        """Test that decoded token contains expiration timestamp."""
        data = {"sub": "user789"}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert "exp" in decoded
        assert isinstance(decoded["exp"], int)

    def test_create_token_with_custom_expiration(self):
        """Test creating token with custom expiration time."""
        data = {"sub": "user999"}
        custom_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=custom_delta)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert "exp" in decoded

    def test_decode_invalid_token_returns_none(self):
        """Test decoding invalid token returns None."""
        invalid_token = "invalid.token.here"
        result = decode_access_token(invalid_token)

        assert result is None

    def test_decode_malformed_token_returns_none(self):
        """Test decoding malformed token returns None."""
        malformed_token = "not-a-jwt-token"
        result = decode_access_token(malformed_token)

        assert result is None

    def test_decode_empty_token_returns_none(self):
        """Test decoding empty token returns None."""
        empty_token = ""
        result = decode_access_token(empty_token)

        assert result is None

    def test_token_preserves_data_types(self):
        """Test that token preserves various data types."""
        data = {
            "sub": "user123",
            "role": "lecturer",
            "active": True,
            "count": 42,
        }
        token = create_access_token(data)
        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "lecturer"
        assert decoded["active"] is True
        assert decoded["count"] == 42

    def test_multiple_tokens_with_same_data_are_different(self):
        """Test that creating multiple tokens with same data produces different tokens."""
        data = {"sub": "user123"}
        token1 = create_access_token(data)
        token2 = create_access_token(data)

        # Tokens should be different due to different expiration timestamps
        assert token1 != token2
        # But both should decode to same user data
        decoded1 = decode_access_token(token1)
        decoded2 = decode_access_token(token2)
        assert decoded1["sub"] == decoded2["sub"]
