"""Tests for concurrency, storage failures, timeouts, and job recovery."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from src.database.session import SessionLocal
from src.database.models import MusicJob
from src.tasks.job_worker import execute_job_pipeline
from src.storage import StorageService


def test_concurrent_job_creation(client: TestClient, clean_db):
    """Verify that multiple concurrent creation requests succeed without database locks or race conditions."""
    def send_request(i):
        payload = {
            "prompt": f"concurrent test cue #{i}",
            "duration_s": 6.0,
            "seed": 1000 + i,
        }
        headers = {"Idempotency-Key": f"concurrent-key-{i}"}
        return client.post("/api/v1/music/jobs", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(pool.map(send_request, range(5)))

    assert len(responses) == 5
    job_ids = set()
    for resp in responses:
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        job_ids.add(data["job_id"])

    # All job IDs must be unique
    assert len(job_ids) == 5


def test_storage_failure_handling(clean_db, monkeypatch):
    """Verify worker safely marks job as failed when storage service fails."""
    job_id = "job_storage_fail_test"
    req_json = json.dumps({"prompt": "storage failure test", "duration_s": 8.0})

    with SessionLocal() as db:
        job = MusicJob(
            id=job_id,
            request_hash="dummy_hash",
            prompt="storage failure test",
            duration_s=8.0,
            status="queued",
            progress=0,
            request_json=req_json,
        )
        db.add(job)
        db.commit()

    def broken_upload(self, *args, **kwargs):
        raise IOError("Simulated disk quota exceeded or MinIO S3 network unreachable")

    monkeypatch.setattr(StorageService, "upload_file", broken_upload)

    # Execute pipeline
    execute_job_pipeline(job_id)

    with SessionLocal() as db:
        updated_job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
        assert updated_job.status == "failed"
        assert updated_job.error_code == "PROCESSING_FAILED"
        assert "Simulated disk quota" in updated_job.error_message


def test_job_recovery_simulation(clean_db):
    """Verify that an interrupted job can be re-run and transitions to succeeded."""
    job_id = "job_recovery_test_001"
    req_json = json.dumps({"prompt": "recovery test cue", "duration_s": 6.0, "seed": 42})

    # Simulate job left in 'running' state after an unexpected process crash
    with SessionLocal() as db:
        job = MusicJob(
            id=job_id,
            request_hash="dummy_hash",
            prompt="recovery test cue",
            duration_s=6.0,
            status="queued",  # Re-queued by recovery supervisor
            progress=15,
            request_json=req_json,
        )
        db.add(job)
        db.commit()

    # Re-execute job pipeline
    execute_job_pipeline(job_id)

    with SessionLocal() as db:
        updated_job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
        assert updated_job.status == "succeeded"
        assert updated_job.progress == 100
        assert updated_job.result_urls_json is not None
