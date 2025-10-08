"""
Health check and welcome endpoints.

Provides health check endpoint and root welcome message.
"""

from fastapi import APIRouter, Request
from app.models.schemas import HealthResponse, WelcomeResponse
from app.core.config import settings
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=WelcomeResponse, tags=["root"])
async def welcome(request: Request) -> WelcomeResponse:
    """
    Root endpoint with welcome message.

    Returns:
        WelcomeResponse with API information and documentation URL.
    """
    # Build documentation URL from request
    docs_url = str(request.base_url).rstrip("/") + "/docs"

    return WelcomeResponse(
        message=f"Welcome to the {settings.app_name}! Documentation is available at {docs_url}",
        version=settings.app_version,
        status="running",
        docs_url=docs_url,
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status and version information.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
    )
