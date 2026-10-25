"""FastAPI root entrypoint for Vercel Serverless Functions."""
import os
import sys
import json
import traceback
import logging

for candidate in [
    os.path.abspath(os.path.dirname(__file__)),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "src")),
    os.getcwd(),
    "/var/task",
]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from src.main import app as fastapi_app
except Exception as exc:
    err_tb = traceback.format_exc()
    logging.exception("Fatal startup error importing src.main on Vercel: %s", err_tb)
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
                "message": str(exc),
                "traceback": err_tb.splitlines(),
            },
        )


async def app(scope, receive, send):
    """ASGI entrypoint with lifespan handling, path restoration, and error shielding."""
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
        orig_uri = headers.get(b"x-forwarded-uri") or headers.get(b"x-invoke-path")
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

    try:
        await fastapi_app(scope, receive, send)
    except Exception as e:
        trace = traceback.format_exc()
        logging.error("Unhandled ASGI error on Vercel: %s", trace)
        err_body = json.dumps({
            "error": "ASGI_INVOCATION_ERROR",
            "message": str(e),
            "traceback": trace.splitlines(),
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
