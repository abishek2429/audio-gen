"""FastAPI root entrypoint for Vercel Serverless Functions."""
import os
import sys
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

_startup_error = None
app = None

try:
    from src.main import app as _main_app
    app = _main_app
except Exception as exc:
    _startup_error = traceback.format_exc()
    logging.exception("Fatal startup error importing src.main on Vercel: %s", _startup_error)
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="IncuBrix Diagnostics")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
    async def diag_handler(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "SERVERLESS_STARTUP_FAILED",
                "message": str(exc),
                "traceback": _startup_error.splitlines(),
                "cwd": os.getcwd(),
                "dirname": os.path.dirname(__file__),
                "sys_path": sys.path[:8],
                "files_in_cwd": os.listdir(".") if os.path.exists(".") else [],
            },
        )

__all__ = ["app"]
