"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache import get_cache_client
from src.config import get_settings
from src.database import get_db
from src.metrics import get_metrics

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str = settings.api_version
    environment: str = settings.environment


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: str
    timestamp: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check - is the service running."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> ReadinessResponse:
    """Readiness check including database connectivity."""
    checks: dict[str, str] = {}

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check cache connection
    try:
        cache_client = get_cache_client()
        if cache_client.is_connected:
            cache_stats = await cache_client.get_stats()
            checks["cache"] = f"ok ({cache_stats.get('backend', 'unknown')})"
        else:
            checks["cache"] = "not_connected"
    except Exception as e:
        checks["cache"] = f"error: {str(e)}"

    # Determine overall status (cache is optional, so don't fail on it)
    critical_checks = {k: v for k, v in checks.items() if k in ["database"]}
    all_ok = all(v == "ok" or v.startswith("ok") for v in critical_checks.values())

    return ReadinessResponse(
        status="ready" if all_ok else "not_ready",
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check - is the process alive."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
