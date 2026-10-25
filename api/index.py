"""Vercel Serverless Function entrypoint for IncuBrix AI Background Music Engine."""
import os
import sys
import json
import traceback

# Ensure repository root is on sys.path for internal module imports
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_startup_error = None
fastapi_app = None

try:
    from src.main import app as fastapi_app
except Exception as e:
    _startup_error = traceback.format_exc()
    print("FATAL SERVERLESS IMPORT ERROR:\n" + _startup_error, flush=True)


async def app(scope, receive, send):
    """ASGI application entry point with diagnostic error boundary."""
    if _startup_error:
        body = json.dumps({
            "error": "Serverless Startup Failed",
            "type": "StartupImportError",
            "traceback": _startup_error,
            "cwd": os.getcwd(),
            "sys_path": sys.path[:5],
        }, indent=2).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": body})
        return

    try:
        await fastapi_app(scope, receive, send)
    except Exception as e:
        err_trace = traceback.format_exc()
        print("FATAL SERVERLESS RUNTIME ERROR:\n" + err_trace, flush=True)
        body = json.dumps({
            "error": "Serverless Request Invocation Failed",
            "type": "RuntimeInvocationError",
            "traceback": err_trace
        }, indent=2).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": body})


__all__ = ["app"]
