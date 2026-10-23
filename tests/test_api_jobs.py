"""Integration tests for job creation and status endpoints."""
import time
from fastapi.testclient import TestClient


def test_create_job_success(client: TestClient, clean_db):
    """Verify POST /api/v1/music/jobs accepts valid payload and returns HTTP 202."""
    payload = {
        "prompt": "calm corporate acoustic folk",
        "duration_s": 8.0,
        "tempo_bpm": 110,
        "key": "C major",
        "seed": 42,
    }
    response = client.post("/api/v1/music/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["progress"] == 0
    assert "created_at" in data
    assert "X-Correlation-Id" in response.headers


def test_create_job_validation_failures(client: TestClient):
    """Verify HTTP 400 with standardized error schema on invalid payload."""
    # Too short duration (< 5.0s)
    res1 = client.post("/api/v1/music/jobs", json={"prompt": "test", "duration_s": 2.0})
    assert res1.status_code == 400
    err1 = res1.json()
    assert "error" in err1
    assert err1["error"]["code"] == "INVALID_REQUEST"

    # Missing prompt
    res2 = client.post("/api/v1/music/jobs", json={"duration_s": 15.0})
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "INVALID_REQUEST"

    # Too long duration (> 300.0s)
    res3 = client.post("/api/v1/music/jobs", json={"prompt": "long", "duration_s": 500.0})
    assert res3.status_code == 400
    assert res3.json()["error"]["code"] == "INVALID_REQUEST"


def test_get_nonexistent_job_returns_404(client: TestClient):
    """Verify GET /api/v1/jobs/{job_id} returns HTTP 404 for unknown job."""
    response = client.get("/api/v1/jobs/job_unknown_999999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "JOB_NOT_FOUND"


def test_create_and_poll_job_to_completion(client: TestClient, clean_db):
    """Verify end-to-end background execution reaches status 'succeeded' with results."""
    payload = {
        "prompt": "uplifting cinematic strings",
        "duration_s": 6.0,
        "seed": 123,
    }
    create_resp = client.post("/api/v1/music/jobs", json=payload)
    assert create_resp.status_code == 202
    job_id = create_resp.json()["job_id"]

    # Poll status for up to 10 seconds
    max_wait = 10.0
    start = time.time()
    final_status = None
    final_data = None

    while time.time() - start < max_wait:
        poll_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_resp.status_code == 200
        final_data = poll_resp.json()
        final_status = final_data["status"]
        if final_status in ("succeeded", "failed"):
            break
        time.sleep(0.5)

    assert final_status == "succeeded", f"Job failed or timed out: {final_data}"
    assert final_data["progress"] == 100
    assert final_data["result"] is not None
    assert "mix_wav" in final_data["result"]
    assert "manifest" in final_data["result"]
    assert len(final_data["result"]["stems"]) >= 3
    assert final_data["manifest"] is not None
    assert final_data["manifest"]["actual_duration_s"] == 6.0
