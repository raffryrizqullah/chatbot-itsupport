"""
Dependency injection for FastAPI routes.

This module provides reusable dependencies for API endpoints.
"""

from app.core.config import settings


def get_settings():
    """
    Get application settings.

    Returns:
        Settings instance with all configuration values.
    """
    return settings
