"""
Health check endpoint.

Provides a simple health check endpoint to verify the API is running.
"""

from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import settings
from datetime import datetime

router = APIRouter()


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
