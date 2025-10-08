"""
Rate limiting configuration for API endpoints.

This module provides rate limiting functionality using SlowAPI to prevent
abuse and ensure fair resource usage across all users.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Initialize limiter with remote address as key
limiter = Limiter(key_func=get_remote_address)


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
