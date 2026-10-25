"""Automated tests for Video-to-Beat API endpoints."""
import io
import time
import pytest
from fastapi.testclient import TestClient

from tests.test_video_analyzer import generate_test_video_bytes


def test_video_analyze_endpoint_success(client: TestClient):
    """Verify POST /api/v1/video/analyze extracts metadata and returns a valid plan."""
    video_bytes = generate_test_video_bytes(duration_s=5.0, fps=24.0, scene_cuts_at=[2.0])

    response = client.post(
        "/api/v1/video/analyze",
        files={"file": ("promo.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"style": "cinematic"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "metadata" in data
    assert data["metadata"]["filename"] == "promo.mp4"
    assert abs(data["metadata"]["duration_s"] - 5.0) <= 0.15
    assert data["metadata"]["fps"] == 24.0

    assert "scene_cuts" in data
    assert len(data["scene_cuts"]) >= 1

    assert "activity" in data
    assert data["activity"]["pacing"] in ("slow", "moderate", "fast-paced")

    assert "keyframes" in data
    assert len(data["keyframes"]) >= 1

    assert "recommended_plan" in data
    plan = data["recommended_plan"]
    assert plan["genre"] == "Cinematic Orchestral"
    assert abs(plan["target_duration_s"] - 5.0) <= 0.15
    assert len(plan["sections"]) >= 1
    assert plan["sections"][0]["start_s"] == 0.0


def test_video_analyze_endpoint_validation_failures(client: TestClient):
    """Verify invalid video uploads fail with standard 400 errors."""
    # 1. Empty file
    res_empty = client.post(
        "/api/v1/video/analyze",
        files={"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")},
    )
    assert res_empty.status_code == 400
    assert res_empty.json()["error"]["code"] == "EMPTY_VIDEO_FILE"

    # 2. Corrupt file
    res_corrupt = client.post(
        "/api/v1/video/analyze",
        files={"file": ("corrupt.mp4", io.BytesIO(b"NOT_A_VALID_VIDEO"), "video/mp4")},
    )
    assert res_corrupt.status_code == 400
    assert res_corrupt.json()["error"]["code"] in ("INVALID_VIDEO_FILE", "EMPTY_VIDEO_STREAM")

    # 3. Unsupported extension
    res_ext = client.post(
        "/api/v1/video/analyze",
        files={"file": ("audio.mp3", io.BytesIO(b"ID3dummy"), "audio/mpeg")},
    )
    assert res_ext.status_code == 400
    assert res_ext.json()["error"]["code"] == "UNSUPPORTED_VIDEO_FORMAT"


def test_video_job_creation_and_end_to_end_synthesis(client: TestClient, clean_db):
    """Verify POST /api/v1/video/jobs enqueues a job, generates audio, and completes successfully."""
    video_bytes = generate_test_video_bytes(duration_s=6.0, fps=24.0, scene_cuts_at=[2.5])

    response = client.post(
        "/api/v1/video/jobs",
        files={"file": ("ad_clip.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"style": "electronic"},
        headers={"Idempotency-Key": "test-video-idemp-1"},
    )

    assert response.status_code == 202
    data = response.json()
    job_id = data["job_id"]
    assert job_id.startswith("job_")
    assert data["status"] == "queued"
    assert "plan" in data
    assert data["plan"]["genre"] == "Modern Electronic"

    # Poll job until completion
    max_wait_s = 20
    t0 = time.time()
    succeeded = False

    while time.time() - t0 < max_wait_s:
        status_res = client.get(f"/api/v1/jobs/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()

        if status_data["status"] == "succeeded":
            succeeded = True
            assert status_data["progress"] == 100
            assert status_data["result"] is not None
            assert "mix_wav" in status_data["result"]
            assert "drums" in status_data["result"]["stems"]
            assert "manifest" in status_data["result"]

            manifest = status_data["manifest"]
            assert abs(manifest["actual_duration_s"] - 6.0) <= 0.05
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Job failed unexpectedly: {status_data.get('error')}")

        time.sleep(0.3)

    assert succeeded, "Video-to-beat job did not succeed within timeout"


def test_video_job_idempotency_behavior(client: TestClient, clean_db):
    """Verify identical video submission with same Idempotency-Key returns existing job."""
    video_bytes = generate_test_video_bytes(duration_s=5.0, fps=24.0)

    # First submission
    res1 = client.post(
        "/api/v1/video/jobs",
        files={"file": ("clip.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"style": "cinematic"},
        headers={"Idempotency-Key": "idemp-video-duplicate-check"},
    )
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    # Second identical submission
    res2 = client.post(
        "/api/v1/video/jobs",
        files={"file": ("clip.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"style": "cinematic"},
        headers={"Idempotency-Key": "idemp-video-duplicate-check"},
    )
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]
    assert job_id_1 == job_id_2
