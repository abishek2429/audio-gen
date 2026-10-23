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

        # 1. Request payload size check
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > settings.max_upload_size_bytes:
                    return JSONResponse(
                        status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body exceeds maximum allowed size of {settings.max_upload_size_bytes} bytes.",
                                "retryable": False,
                                "details": {"max_bytes": settings.max_upload_size_bytes, "received_bytes": int(cl)},
                            }
                        },
                    )
            except ValueError:
                pass

        # 2. Demo access protection (when DEMO_API_KEY is configured)
        public_paths = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}
        path = request.url.path
        if settings.demo_api_key and settings.demo_api_key.strip():
            if path not in public_paths and not path.startswith("/docs"):
                auth_hdr = request.headers.get("Authorization", "")
                bearer_tok = auth_hdr[7:].strip() if auth_hdr.startswith("Bearer ") else None
                provided_key = request.headers.get("X-API-Key") or bearer_tok
                from src.security import validate_demo_api_key
                if not validate_demo_api_key(provided_key, settings.demo_api_key):
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Demo authentication required. Provide valid API key in 'X-API-Key' or 'Authorization: Bearer <key>'.",
                                "retryable": False,
                                "details": {},
                            }
                        },
                    )

        # 3. Rate limiting (sliding window per client IP)
        if settings.rate_limit_per_minute > 0 and path not in public_paths:
            client_ip = (
                request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1")
                .split(",")[0]
                .strip()
            )
            from src.security import global_rate_limiter
            if not global_rate_limiter.is_allowed(client_ip, limit=settings.rate_limit_per_minute):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit of {settings.rate_limit_per_minute} requests per minute exceeded.",
                            "retryable": True,
                            "details": {"retry_after_s": 60},
                        }
                    },
                    headers={"Retry-After": "60"},
                )

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
