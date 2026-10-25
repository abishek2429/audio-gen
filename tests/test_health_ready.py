"""Tests for /health and /ready endpoints."""
from fastapi.testclient import TestClient


def test_get_health_endpoint(client: TestClient):
    """Verify /health returns HTTP 200 with status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "incubrix-audio-engine"
    assert "version" in data


def test_get_ready_endpoint_healthy(client: TestClient):
    """Verify /ready returns HTTP 200 when database and storage are available."""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["storage"] == "ok"


def test_get_ready_unhealthy_on_db_failure(client: TestClient, monkeypatch):
    """Verify /ready returns HTTP 503 if database check fails."""
    from sqlalchemy.orm import Session

    def broken_execute(self, *args, **kwargs):
        raise RuntimeError("Simulated database connection failure")

    monkeypatch.setattr(Session, "execute", broken_execute)

    resp = client.get("/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"
    assert "unhealthy" in data["checks"]["database"]


def test_get_root_endpoint(client: TestClient):
    """Verify / returns HTTP 200 with service information and documentation links."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "IncuBrix" in data["service"]
    assert data["documentation"] == "/docs"
    assert data["health"] == "/health"


def test_get_health_and_ready_api_aliases(client: TestClient):
    """Verify /api/health and /api/ready aliases work for frontend proxy configurations."""
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "ok"

    resp_ready = client.get("/api/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"

