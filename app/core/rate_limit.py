"""
Rate limiting configuration for API endpoints.

This module provides rate limiting functionality using SlowAPI to prevent
abuse and ensure fair resource usage across all users.
"""

<<<<<<< HEAD
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Initialize limiter with remote address as key
limiter = Limiter(key_func=get_remote_address)
=======
from hashlib import sha256
from typing import Optional
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings
from app.core.security import decode_access_token

# Use shared backend so counters persist across workers
_storage_uri = settings.get_rate_limit_storage_uri()


def _hash_value(value: str) -> str:
    """Hash sensitive identifiers so raw secrets are not stored."""
    return sha256(value.encode("utf-8")).hexdigest()


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def rate_limit_key_func(request: Request) -> str:
    """
    Determine rate limit identity for incoming request.

    Priority: API key -> JWT subject -> fallback to remote IP.
    """
    # API key based identity (hashed to avoid storing raw secret)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api-key:{_hash_value(api_key)}"

    # JWT subject when bearer token is provided
    token = _extract_bearer_token(request)
    if token:
        payload = decode_access_token(token)
        subject = (payload or {}).get("sub")
        if subject:
            return f"user:{subject}"
        # Fallback to hashed token so refresh tokens with same user still group together
        return f"bearer:{_hash_value(token)}"

    # Default: per client IP
    return f"ip:{get_remote_address(request)}"


# Initialize limiter with identity-aware key function and shared storage
limiter = Limiter(
    key_func=rate_limit_key_func,
    storage_uri=_storage_uri,
)
>>>>>>> bb677be (feat : update logging error)


def get_rate_limits() -> dict:
    """
    Get rate limit configuration from settings.

    Returns:
        Dictionary of rate limit profiles for different endpoints.
    """
    return {
        "auth_login": settings.rate_limit_login,
        "auth_register": settings.rate_limit_register,
        "query": settings.rate_limit_query,
        "upload": settings.rate_limit_upload,
        "api_key_create": settings.rate_limit_api_key_create,
        "api_key_list": settings.rate_limit_api_key_list,
        "api_key_delete": settings.rate_limit_api_key_delete,
        "chat_history": settings.rate_limit_chat_history,
        "default": settings.rate_limit_default,
    }


# Rate limit profiles loaded from settings
RATE_LIMITS = get_rate_limits()
