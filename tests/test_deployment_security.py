"""Tests for deployment security: rate limiting, request size limits, and demo access protection."""
import json
import pytest
from starlette.testclient import TestClient

from src.main import create_app
from src.config import settings
from src.security import global_rate_limiter


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_public_health_and_ready_endpoints_always_accessible(client, monkeypatch):
    """Verify that operational endpoints bypass demo auth and rate limiting."""
    monkeypatch.setattr(settings, "demo_api_key", "super_secret_demo_key_999")
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)

    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    r2 = client.get("/ready")
    assert r2.status_code in (200, 503)


def test_payload_size_limit_rejection(client, monkeypatch):
    """Verify that payloads exceeding max_upload_size_bytes return HTTP 413."""
    monkeypatch.setattr(settings, "max_upload_size_bytes", 1024)  # 1 KB

    headers = {
        "Content-Length": "2048",
        "Content-Type": "application/json",
        "Idempotency-Key": "test_payload_large_001",
    }
    payload = {"prompt": "x" * 2000, "duration_s": 10.0}

    resp = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds maximum allowed size" in body["error"]["message"]


def test_demo_api_key_protection_unauthorized(client, monkeypatch):
    """Verify that protected API endpoints return HTTP 401 when demo API key is required."""
    monkeypatch.setattr(settings, "demo_api_key", "incubrix_demo_secret_key_42")

    payload = {"prompt": "ambient cinematic", "duration_s": 10.0}
    headers = {"Idempotency-Key": "test_auth_missing_001"}

    # 1. Missing authentication
    resp = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid authentication
    headers["X-API-Key"] = "wrong_key"
    resp2 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert resp2.status_code == 401
    assert resp2.json()["error"]["code"] == "UNAUTHORIZED"


def test_demo_api_key_protection_authorized(client, monkeypatch):
    """Verify that valid demo API key allows requests via X-API-Key or Bearer token."""
    demo_key = "incubrix_demo_secret_key_42"
    monkeypatch.setattr(settings, "demo_api_key", demo_key)

    payload = {"prompt": "ambient cinematic", "duration_s": 10.0}

    # 1. Valid X-API-Key header
    headers1 = {
        "Idempotency-Key": "test_auth_valid_x_api_key",
        "X-API-Key": demo_key,
    }
    resp1 = client.post("/api/v1/music/jobs", json=payload, headers=headers1)
    assert resp1.status_code == 202
    assert "job_id" in resp1.json()

    # 2. Valid Authorization: Bearer token
    headers2 = {
        "Idempotency-Key": "test_auth_valid_bearer",
        "Authorization": f"Bearer {demo_key}",
    }
    resp2 = client.post("/api/v1/music/jobs", json=payload, headers=headers2)
    assert resp2.status_code == 202
    assert "job_id" in resp2.json()


def test_rate_limiting_exceeded(client, monkeypatch):
    """Verify that exceeding rate_limit_per_minute returns HTTP 429 with Retry-After header."""
    global_rate_limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)

    # First 3 requests should pass
    for i in range(3):
        r = client.get("/api/v1/jobs?limit=5")
        assert r.status_code == 200

    # 4th request must be throttled
    r4 = client.get("/api/v1/jobs?limit=5")
    assert r4.status_code == 429
    assert r4.headers.get("Retry-After") == "60"
    body = r4.json()
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert body["error"]["retryable"] is True

    # Reset limiter for subsequent tests
    global_rate_limiter.reset()
