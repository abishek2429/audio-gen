"""FastAPI root entrypoint for Vercel Serverless Functions."""
import os
import sys
import json
import logging
import traceback

logger = logging.getLogger("incubrix.entrypoint")

# Ensure repository root and /var/task are at the front of sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = (
    _current_dir
    if os.path.exists(os.path.join(_current_dir, "src"))
    else os.path.abspath(os.path.join(_current_dir, ".."))
)

for path_dir in [_repo_root, "/var/task", os.getcwd()]:
    if os.path.exists(path_dir) and path_dir not in sys.path:
        sys.path.insert(0, path_dir)

_startup_error = None
_startup_exc_type = None
_startup_tb = None

try:
    from src.main import app as fastapi_app
except Exception as exc:
    # Explicitly capture exception attributes within the except scope
    _startup_error = str(exc)
    _startup_exc_type = exc.__class__.__name__
    _startup_tb = traceback.format_exc()

    # Log full traceback server-side without leaking secrets to public clients
    logger.exception("Fatal startup error importing src.main on Vercel: %s", _startup_tb)
    sys.stderr.write(f"FATAL STARTUP IMPORT ERROR:\n{_startup_tb}\n")
    sys.stderr.flush()

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    fastapi_app = FastAPI(title="IncuBrix Diagnostics")

    @fastapi_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
    async def diag_handler(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "SERVERLESS_STARTUP_FAILED",
                "message": f"Serverless application startup failed: {_startup_error}",
                "details": {
                    "exception": _startup_exc_type,
                },
            },
        )


async def app(scope, receive, send):
    """ASGI entrypoint with lifespan handling, path restoration, and single-response guarantee."""
    if scope.get("type") == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope.get("type") == "http":
        headers = dict(scope.get("headers", []))
        orig_uri = (
            headers.get(b"x-forwarded-uri")
            or headers.get(b"x-invoke-path")
            or headers.get(b"x-matched-path")
            or headers.get(b"x-forwarded-path")
        )
        if orig_uri:
            try:
                orig_path = orig_uri.decode("utf-8", errors="ignore").split("?")[0]
                if orig_path:
                    scope["path"] = orig_path
            except Exception:
                pass
        elif scope.get("path") == "/api/index.py":
            scope["path"] = "/"
        elif scope.get("path", "").startswith("/api/index.py/"):
            scope["path"] = scope["path"][len("/api/index.py"):]

    response_started = False

    async def send_wrapper(message):
        nonlocal response_started
        if message.get("type") == "http.response.start":
            response_started = True
        await send(message)

    try:
        await fastapi_app(scope, receive, send_wrapper)
    except Exception as e:
        trace = traceback.format_exc()
        logger.error("Unhandled ASGI error on Vercel: %s", trace)
        sys.stderr.write(f"UNHANDLED ASGI ERROR:\n{trace}\n")
        sys.stderr.flush()

        # Enforce single-response guarantee per ASGI specification:
        # only send error response if http.response.start has NOT been sent yet.
        if not response_started:
            err_body = json.dumps({
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                    "details": {"exception": e.__class__.__name__},
                }
            }).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(err_body)).encode("ascii")),
                ],
            })
            await send({"type": "http.response.body", "body": err_body})


__all__ = ["app"]
