"""FastAPI Application Entry Point for IncuBrix AI Background Music Engine."""
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logging_config import setup_structured_logging, correlation_id_ctx
from src.database.session import init_db
from src.api.routes_jobs import router as jobs_router
from src.api.routes_health import router as health_router

logger = logging.getLogger("incubrix.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_structured_logging(settings.log_level)
    logger.info("Initializing IncuBrix AI Background Music Engine (v0.1.0)...")
    init_db()
    logger.info("Database schema initialized successfully.")
    yield
    logger.info("IncuBrix AI Background Music Engine shutting down.")


def create_app() -> FastAPI:
    """FastAPI application factory with OpenAPI 3.1 schema adherence."""
    app = FastAPI(
        title="IncuBrix AI Background Music Engine API",
        description=(
            "AI Background Music Engine for Video: Generates original, commercially safe "
            "instrumental music timed to exact video edit points, with genuine multitrack stems, "
            "ITU-R BS.1770-4 loudness compliance, and voiceover sidechain ducking."
        ),
        version="0.1.0",
        openapi_version="3.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID & Tracing Middleware
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        cid = request.headers.get("X-Correlation-Id") or f"corr_{uuid.uuid4().hex[:12]}"
        correlation_id_ctx.set(cid)

        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response

    # Standardized Exception Handlers (Integration Standard Point 5)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", "HTTP_ERROR")
            message = exc.detail.get("message", str(exc.detail))
            retryable = exc.detail.get("retryable", False)
            details = exc.detail.get("details", {})
        else:
            code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
            message = str(exc.detail)
            retryable = False
            details = {}

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "retryable": retryable,
                    "details": details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_details = []
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            error_details.append({"location": loc, "message": err.get("msg")})

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request payload validation failed.",
                    "retryable": False,
                    "details": {"validation_errors": error_details},
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                    "retryable": True,
                    "details": {"exception": exc.__class__.__name__},
                }
            },
        )

    # Register Routers
    app.include_router(health_router)
    app.include_router(jobs_router)

    return app


app = create_app()
