"""Tests for Idempotency-Key enforcement per Integration Standard Point 4."""
from fastapi.testclient import TestClient


def test_idempotency_identical_payload_returns_same_job(client: TestClient, clean_db):
    """Verify sending identical payload with same key returns the existing job."""
    headers = {"Idempotency-Key": "test-key-identical-001"}
    payload = {
        "prompt": "peaceful acoustic guitar",
        "duration_s": 8.0,
        "seed": 42,
    }

    # First request
    res1 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    # Second request with identical payload and key
    res2 = client.post("/api/v1/music/jobs", json=payload, headers=headers)
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]

    # Must return identical job_id
    assert job_id_1 == job_id_2
    assert "Existing job returned" in res2.json()["message"]


def test_idempotency_differing_payload_returns_409_conflict(client: TestClient, clean_db):
    """Verify reusing an idempotency key with a differing payload returns HTTP 409 Conflict."""
    headers = {"Idempotency-Key": "test-key-conflict-002"}
    payload_a = {
        "prompt": "calm piano ambient",
        "duration_s": 10.0,
    }
    payload_b = {
        "prompt": "aggressive EDM techno drop",
        "duration_s": 30.0,
    }

    # First request
    res1 = client.post("/api/v1/music/jobs", json=payload_a, headers=headers)
    assert res1.status_code == 202

    # Second request with same key but differing payload
    res2 = client.post("/api/v1/music/jobs", json=payload_b, headers=headers)
    assert res2.status_code == 409

    err = res2.json()
    assert "error" in err
    assert err["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert "previously used" in err["error"]["message"]
