"""
Main FastAPI application entry point.

This module initializes the FastAPI app with all routes, middleware,
and error handlers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.routes import health, document, query, chat, auth, api_keys
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.database import init_db, close_db
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.server_log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.

    Handles database initialization on startup and cleanup on shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        Control to the application during its lifetime.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"API documentation available at /docs")
    await init_db()

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    await close_db()


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-modal RAG API for PDF document processing and question answering",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_redoc else None,
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: The incoming request.
        exc: The raised exception.

    Returns:
        JSON response with error details.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc),
        },
    )


# Include routers
app.include_router(health.router, prefix="")
app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth")
app.include_router(api_keys.router, prefix=f"{settings.api_v1_prefix}/admin")
app.include_router(document.router, prefix=settings.api_v1_prefix)
app.include_router(query.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
        log_level=settings.server_log_level,
    )
