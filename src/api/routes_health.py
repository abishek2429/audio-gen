"""Health and Readiness endpoints per Integration Standard Point 8."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.storage import get_storage_service
from src.config import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Service Liveness Check",
    description="Returns HTTP 200 if the FastAPI application process is alive and responsive.",
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/api/health",
    summary="Service Liveness Check (API Alias)",
    description="Returns HTTP 200 if the FastAPI application process is alive and responsive.",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
@router.get(
    "/api/v1/health",
    summary="Service Liveness Check (API v1 Alias)",
    description="Returns HTTP 200 if the FastAPI application process is alive and responsive.",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_health() -> Dict[str, Any]:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "incubrix-audio-engine",
        "version": "0.1.0",
    }


@router.get(
    "/ready",
    summary="Service Readiness Check",
    description="Verifies operational connectivity to PostgreSQL/SQLite and MinIO storage.",
)
@router.get(
    "/api/ready",
    summary="Service Readiness Check (API Alias)",
    description="Verifies operational connectivity to PostgreSQL/SQLite and MinIO storage.",
    include_in_schema=False,
)
@router.get(
    "/api/v1/ready",
    summary="Service Readiness Check (API v1 Alias)",
    description="Verifies operational connectivity to PostgreSQL/SQLite and MinIO storage.",
    include_in_schema=False,
)
def get_ready(response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Readiness probe checking database, storage, and optional Redis broker."""
    checks: Dict[str, str] = {}
    is_ready = True

    # 1. Database Check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
        is_ready = False

    # 2. Storage Check
    try:
        storage = get_storage_service()
        if storage.is_healthy():
            checks["storage"] = "ok"
        else:
            checks["storage"] = "unhealthy: storage backend not accessible"
            is_ready = False
    except Exception as e:
        checks["storage"] = f"unhealthy: {e}"
        is_ready = False

    # 3. Redis / Celery Check (if enabled)
    if settings.celery_enabled:
        try:
            import redis
            r = redis.from_url(settings.redis_url)
            r.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"unhealthy: {e}"
            is_ready = False
    else:
        checks["redis"] = "skipped (in-process mode)"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "checks": checks,
        }

    return {
        "status": "ready",
        "checks": checks,
    }
