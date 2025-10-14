"""
Health check and welcome endpoints.

Provides health check endpoint and root welcome message.
"""

from fastapi import APIRouter, Request, Query
from app.models.schemas import HealthResponse, WelcomeResponse, ServiceHealthResponse, HealthSummaryResponse
from app.core.config import settings
from datetime import datetime
from typing import Dict, Any
import time
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
STARTED_AT = datetime.utcnow()


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


@router.get("/api/v1/health/openai", response_model=ServiceHealthResponse, tags=["health"])
async def health_openai(deep: bool = Query(False, description="Run a live connectivity check")) -> ServiceHealthResponse:
    """
    OpenAI health check.

    - When ``deep=false`` (default): Only validates configuration presence.
    - When ``deep=true``: Attempts a lightweight API call to verify connectivity.
    """
    details: Dict[str, Any] = {
        "model": settings.openai_model,
        "configured": bool(settings.openai_api_key),
    }

    if not settings.openai_api_key:
        return ServiceHealthResponse(
            provider="openai",
            status="configuration_error",
            version=settings.app_version,
            details={**details, "error": "Missing OPENAI_API_KEY"},
        )

    if not deep:
        return ServiceHealthResponse(
            provider="openai",
            status="healthy",
            version=settings.app_version,
            details=details,
        )

    # Deep check: try listing models using the OpenAI client
    start = time.monotonic()
    try:
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=settings.openai_api_key)
            _ = client.models.list()
            latency_ms = int((time.monotonic() - start) * 1000)
            return ServiceHealthResponse(
                provider="openai",
                status="healthy",
                version=settings.app_version,
                details={**details, "latency_ms": latency_ms},
            )
        except ImportError:
            # Fallback: the openai package might not be installed directly
            # Return configured status and a note; avoid forcing a model call.
            msg = "openai package not installed; skipping live OpenAI check"
            logger.warning(msg)
            return ServiceHealthResponse(
                provider="openai",
                status="healthy",
                version=settings.app_version,
                details={**details, "note": "Package 'openai' not installed; skipped live check"},
            )
    except Exception as e:
        msg = f"OpenAI health check failed: {e}"
        logger.error(msg)
        return ServiceHealthResponse(
            provider="openai",
            status="unhealthy",
            version=settings.app_version,
            details={**details, "error": str(e)},
        )


@router.get("/api/v1/health/pinecone", response_model=ServiceHealthResponse, tags=["health"])
async def health_pinecone(deep: bool = Query(False, description="Run a live connectivity check")) -> ServiceHealthResponse:
    """
    Pinecone health check.

    - When ``deep=false`` (default): Only validates configuration presence.
    - When ``deep=true``: Lists indexes and verifies configured index existence.
    """
    details: Dict[str, Any] = {
        "environment": settings.pinecone_environment,
        "index_name": settings.pinecone_index_name,
        "configured": bool(settings.pinecone_api_key),
    }

    if not settings.pinecone_api_key:
        return ServiceHealthResponse(
            provider="pinecone",
            status="configuration_error",
            version=settings.app_version,
            details={**details, "error": "Missing PINECONE_API_KEY"},
        )

    if not deep:
        return ServiceHealthResponse(
            provider="pinecone",
            status="healthy",
            version=settings.app_version,
            details=details,
        )

    # Deep check: verify API access and index existence
    from pinecone import Pinecone  # import locally to avoid overhead at import time

    start = time.monotonic()
    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        indexes = pc.list_indexes()
        index_names = [idx.name for idx in indexes]
        index_exists = settings.pinecone_index_name in index_names
        latency_ms = int((time.monotonic() - start) * 1000)
        return ServiceHealthResponse(
            provider="pinecone",
            status="healthy" if index_exists else "unhealthy",
            version=settings.app_version,
            details={
                **details,
                "latency_ms": latency_ms,
                "available_indexes": index_names,
                "index_exists": index_exists,
            },
        )
    except Exception as e:
        msg = f"Pinecone health check failed: {e}"
        logger.error(msg)
        return ServiceHealthResponse(
            provider="pinecone",
            status="unhealthy",
            version=settings.app_version,
            details={**details, "error": str(e)},
        )


@router.get("/api/v1/health/redis", response_model=ServiceHealthResponse, tags=["health"])
async def health_redis(deep: bool = Query(False, description="Run a live connectivity check")) -> ServiceHealthResponse:
    """
    Redis health check.

    - When ``deep=false`` (default): Returns target configuration info.
    - When ``deep=true``: Performs a `PING` against Redis.
    """
    details: Dict[str, Any] = {
        "host": settings.redis_host,
        "port": settings.redis_port,
        "db": settings.redis_db,
        "configured": True,
    }

    if not deep:
        return ServiceHealthResponse(
            provider="redis",
            status="healthy",
            version=settings.app_version,
            details=details,
        )

    try:
        import redis  # type: ignore

        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        start = time.monotonic()
        pong = client.ping()
        latency_ms = int((time.monotonic() - start) * 1000)
        return ServiceHealthResponse(
            provider="redis",
            status="healthy" if pong else "unhealthy",
            version=settings.app_version,
            details={**details, "latency_ms": latency_ms, "pong": bool(pong)},
        )
    except Exception as e:
        msg = f"Redis health check failed: {e}"
        logger.error(msg)
        return ServiceHealthResponse(
            provider="redis",
            status="unhealthy",
            version=settings.app_version,
            details={**details, "error": str(e)},
        )


@router.get("/api/v1/health/database", response_model=ServiceHealthResponse, tags=["health"])
async def health_database(deep: bool = Query(False, description="Run a live connectivity check")) -> ServiceHealthResponse:
    """
    Database health check.

    - When ``deep=false`` (default): Shows configured DB URL (redacted).
    - When ``deep=true``: Executes a trivial `SELECT 1` using the async engine.
    """
    from app.db.database import engine
    details: Dict[str, Any] = {
        "url": "(redacted)",
        "pool_pre_ping": True,
        "configured": bool(settings.database_url),
    }

    if not settings.database_url:
        return ServiceHealthResponse(
            provider="database",
            status="configuration_error",
            version=settings.app_version,
            details={**details, "error": "Missing DATABASE_URL"},
        )

    if not deep:
        return ServiceHealthResponse(
            provider="database",
            status="healthy",
            version=settings.app_version,
            details=details,
        )

    try:
        from sqlalchemy import text  # type: ignore

        start = time.monotonic()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = int((time.monotonic() - start) * 1000)
        return ServiceHealthResponse(
            provider="database",
            status="healthy",
            version=settings.app_version,
            details={**details, "latency_ms": latency_ms},
        )
    except Exception as e:
        msg = f"Database health check failed: {e}"
        logger.error(msg)
        return ServiceHealthResponse(
            provider="database",
            status="unhealthy",
            version=settings.app_version,
            details={**details, "error": str(e)},
        )


@router.get("/api/v1/health/storage", response_model=ServiceHealthResponse, tags=["health"])
async def health_storage(deep: bool = Query(False, description="Run a live connectivity check")) -> ServiceHealthResponse:
    """
    Cloudflare R2 storage health check.

    - When ``deep=false`` (default): Returns configured bucket info.
    - When ``deep=true``: Attempts a lightweight list on the bucket.
    """
    details: Dict[str, Any] = {
        "bucket": settings.r2_bucket_name,
        "endpoint": settings.r2_endpoint_url,
        "configured": bool(settings.r2_access_key_id and settings.r2_secret_access_key and settings.r2_account_id and settings.r2_bucket_name),
    }

    # Basic configuration sanity
    if not details["configured"]:
        return ServiceHealthResponse(
            provider="storage",
            status="configuration_error",
            version=settings.app_version,
            details={**details, "error": "Missing R2 credentials or bucket"},
        )

    if not deep:
        return ServiceHealthResponse(
            provider="storage",
            status="healthy",
            version=settings.app_version,
            details=details,
        )

    try:
        # Use the existing service for consistent configuration
        from app.services.r2_storage import R2StorageService  # type: ignore

        svc = R2StorageService()
        start = time.monotonic()
        # Minimal list to validate access; avoid fetching content
        svc.client.list_objects_v2(Bucket=svc.bucket_name, MaxKeys=1)
        latency_ms = int((time.monotonic() - start) * 1000)
        return ServiceHealthResponse(
            provider="storage",
            status="healthy",
            version=settings.app_version,
            details={**details, "latency_ms": latency_ms, "bucket": svc.bucket_name},
        )
    except Exception as e:
        msg = f"Storage health check failed: {e}"
        logger.error(msg)
        return ServiceHealthResponse(
            provider="storage",
            status="unhealthy",
            version=settings.app_version,
            details={**details, "error": str(e)},
        )


@router.get("/api/v1/health/rate-limit", response_model=ServiceHealthResponse, tags=["health"])
async def health_rate_limit() -> ServiceHealthResponse:
    """
    Rate limit configuration snapshot.
    """
    details: Dict[str, Any] = {
        "default": settings.rate_limit_default,
        "login": settings.rate_limit_login,
        "register": settings.rate_limit_register,
        "query": settings.rate_limit_query,
        "upload": settings.rate_limit_upload,
        "api_key_create": settings.rate_limit_api_key_create,
        "api_key_list": settings.rate_limit_api_key_list,
        "api_key_delete": settings.rate_limit_api_key_delete,
        "chat_history": settings.rate_limit_chat_history,
        "exposed_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        "storage_uri": settings.get_rate_limit_storage_display_uri(),
    }
    return ServiceHealthResponse(
        provider="rate-limit",
        status="healthy",
        version=settings.app_version,
        details=details,
    )


@router.get("/api/v1/health/version", response_model=ServiceHealthResponse, tags=["health"])
async def health_version() -> ServiceHealthResponse:
    """
    Version and uptime information.
    """
    now = datetime.utcnow()
    uptime_seconds = (now - STARTED_AT).total_seconds()
    details: Dict[str, Any] = {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "started_at": STARTED_AT.isoformat() + "Z",
        "uptime_seconds": int(uptime_seconds),
    }
    return ServiceHealthResponse(
        provider="version",
        status="healthy",
        version=settings.app_version,
        details=details,
    )


@router.get("/api/v1/health/summary", response_model=HealthSummaryResponse, tags=["health"])
async def health_summary(deep: bool = Query(False, description="Run live checks for providers")) -> HealthSummaryResponse:
    """
    Aggregate health across all services.

    - deep=false: configuration-level checks only.
    - deep=true: perform live connectivity checks where supported.
    """
    # Run checks concurrently
    results = await asyncio.gather(
        health_openai(deep=deep),
        health_pinecone(deep=deep),
        health_redis(deep=deep),
        health_database(deep=deep),
        health_storage(deep=deep),
        health_rate_limit(),
        health_version(),
        return_exceptions=True,
    )

    # Map results to identifiers
    names = [
        "openai",
        "pinecone",
        "redis",
        "database",
        "storage",
        "rate_limit",
        "version",
    ]

    services: Dict[str, ServiceHealthResponse] = {}
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            msg = f"Health check for {name} raised exception: {res}"
            logger.error(msg)
            services[name] = ServiceHealthResponse(
                provider=name.replace("_", "-"),
                status="unhealthy",
                version=settings.app_version,
                details={"error": str(res)},
            )
        else:
            services[name] = res  # type: ignore[assignment]

    # Compute overall status
    statuses = [s.status for s in services.values()]
    if any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    elif any(s == "configuration_error" for s in statuses):
        overall = "configuration_error"
    else:
        overall = "healthy"

    return HealthSummaryResponse(
        status=overall,
        version=settings.app_version,
        services=services,
    )
