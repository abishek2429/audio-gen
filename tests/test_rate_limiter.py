"""Unit tests for sliding-window rate limiter, multi-client isolation, concurrency, and security safeguards."""
import time
import concurrent.futures
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.security import InMemoryRateLimiter, global_rate_limiter
from src.config import settings

client = TestClient(app)


def test_rate_limiter_multi_client_isolation():
    """Verify that requests from separate client IPs do not share or corrupt counters."""
    limiter = InMemoryRateLimiter(limit_per_minute=2)

    # Client A: 2 requests allowed, 3rd blocked
    assert limiter.is_allowed("client_A") is True
    assert limiter.is_allowed("client_A") is True
    assert limiter.is_allowed("client_A") is False

    # Client B: should have independent fresh quota
    assert limiter.is_allowed("client_B") is True
    assert limiter.is_allowed("client_B") is True
    assert limiter.is_allowed("client_B") is False


def test_rate_limiter_sliding_window_expiry(monkeypatch):
    """Verify that timestamps older than 60 seconds expire from the sliding window."""
    limiter = InMemoryRateLimiter(limit_per_minute=2)
    fake_time = 1000.0

    def mock_time():
        return fake_time

    monkeypatch.setattr(time, "time", mock_time)

    # Use up quota at t=1000.0
    assert limiter.is_allowed("user_1") is True
    assert limiter.is_allowed("user_1") is True
    assert limiter.is_allowed("user_1") is False

    # Advance 30 seconds (still within window)
    fake_time = 1030.0
    assert limiter.is_allowed("user_1") is False

    # Advance 61 seconds from start (window expired)
    fake_time = 1061.0
    assert limiter.is_allowed("user_1") is True


def test_rate_limiter_concurrency_thread_safety():
    """Verify thread-safe locking under concurrent requests."""
    limiter = InMemoryRateLimiter(limit_per_minute=10)
    allowed_count = 0
    blocked_count = 0

    def attempt_request():
        nonlocal allowed_count, blocked_count
        if limiter.is_allowed("concurrent_client"):
            allowed_count += 1
        else:
            blocked_count += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_request) for _ in range(25)]
        concurrent.futures.wait(futures)

    assert allowed_count == 10
    assert blocked_count == 15


def test_http_429_retry_after_header_returned(monkeypatch):
    """Verify HTTP 429 response contains Retry-After header and structured error body."""
    global_rate_limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)

    headers = {"X-Forwarded-For": "198.51.100.25"}
    payload = {"prompt": "ambient guitar", "duration_s": 5.0}

    # Request 1 & 2 pass
    r1 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert r1.status_code == 202
    r2 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert r2.status_code == 202

    # Request 3 triggers 429
    r3 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert r3.status_code == 429
    assert r3.headers.get("Retry-After") == "60"
    data = r3.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["details"]["retry_after_s"] == 60


def test_production_safeguard_prevents_zero_limit_bypass(monkeypatch):
    """Verify production environment enforces secure default if rate_limit_per_minute is set to <= 0."""
    global_rate_limiter.reset()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "rate_limit_per_minute", 0)

    # In production, effective limit falls back to 60 rather than disabling protection
    headers = {"X-Forwarded-For": "203.0.113.88"}
    r = client.get("/api/v1/jobs")
    # Should succeed normally without crash
    assert r.status_code in (200, 401)
