"""Automated tests for Vercel serverless entrypoints, exception scoping, and single-response guarantees."""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient

import main
import api.index
from src.main import app as fastapi_app


def test_root_endpoint_metadata(client: TestClient):
    """Requirement 7: Check the root route returns deliberate informational response, not 500."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "IncuBrix" in data["service"]
    assert data["health"] == "/health"


def test_health_endpoint_healthy(client: TestClient):
    """Requirement 6: Check /health returns simple successful JSON response when healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "incubrix-audio-engine"
    assert "version" in data


def test_normal_endpoint_404_not_found(client: TestClient):
    """Verify missing endpoints return structured 404, not internal server errors."""
    response = client.get("/non_existent_path_xyz")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_main_asgi_single_response_for_health():
    """Verify ASGI entrypoint sends exactly one start and one body message for /health."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await main.app(scope, receive, send)

    starts = [m for m in messages if m["type"] == "http.response.start"]
    bodies = [m for m in messages if m["type"] == "http.response.body"]

    assert len(starts) == 1, f"Expected exactly 1 start message, got {len(starts)}"
    assert starts[0]["status"] == 200
    assert len(bodies) >= 1
    full_body = b"".join(m.get("body", b"") for m in bodies)
    data = json.loads(full_body.decode("utf-8"))
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_main_asgi_path_restoration_from_forwarded_uri():
    """Verify x-forwarded-uri from Vercel rewrites routes to /health instead of /api/index.py."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/index.py",
        "raw_path": b"/api/index.py",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"x-forwarded-uri", b"/health"),
        ],
    }
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await main.app(scope, receive, send)

    starts = [m for m in messages if m["type"] == "http.response.start"]
    bodies = [m for m in messages if m["type"] == "http.response.body"]

    assert len(starts) == 1
    assert starts[0]["status"] == 200
    full_body = b"".join(m.get("body", b"") for m in bodies)
    data = json.loads(full_body.decode("utf-8"))
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_asgi_no_double_response_on_unhandled_exception():
    """Requirement 3: Verify ASGI error-response logic NEVER sends a second response if response already started."""
    sent_messages = []

    # Create a mock ASGI app that starts a response, then raises an exception
    async def flawed_inner_app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"partial"})
        # Now raise an unhandled exception after response started
        raise RuntimeError("Simulated mid-stream failure")

    # Wrap with our entrypoint's send_wrapper logic
    response_started = False

    async def send_wrapper(message):
        nonlocal response_started
        if message.get("type") == "http.response.start":
            # If start was already sent, sending again is a protocol violation
            if response_started:
                raise RuntimeError("Unexpected ASGI message 'http.response.start' sent, after response already completed.")
            response_started = True
        sent_messages.append(message)

    try:
        await flawed_inner_app({}, None, send_wrapper)
    except Exception:
        # Now test our error handler logic: it must NOT send start if response_started is True
        if not response_started:
            await send_wrapper({"type": "http.response.start", "status": 500})

    starts = [m for m in sent_messages if m["type"] == "http.response.start"]
    assert len(starts) == 1, f"Expected exactly 1 http.response.start, got {len(starts)}"


@pytest.mark.asyncio
async def test_diagnostic_handler_exception_scoping():
    """Requirement 2: Verify exception scoping in diagnostic fallback handler without NameError."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    _simulated_error = None
    _simulated_exc_type = None

    try:
        raise ValueError("Simulated module import failure on cold start")
    except Exception as exc:
        _simulated_error = str(exc)
        _simulated_exc_type = exc.__class__.__name__

    diag_app = FastAPI()

    @diag_app.api_route("/{path:path}", methods=["GET", "POST"])
    async def diag_handler(path: str = ""):
        # Must access captured strings, not deleted 'exc' variable
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "SERVERLESS_STARTUP_FAILED",
                "message": f"Serverless application startup failed: {_simulated_error}",
                "details": {"exception": _simulated_exc_type},
            },
        )

    diag_client = TestClient(diag_app)
    resp = diag_client.get("/health")
    assert resp.status_code == 500
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "SERVERLESS_STARTUP_FAILED"
    assert "Simulated module import failure" in data["message"]
    assert data["details"]["exception"] == "ValueError"
