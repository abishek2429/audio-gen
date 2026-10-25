"""Tests for background worker execution, provider failures, and job recovery."""
import json
import pytest

from src.database.session import SessionLocal
from src.database.models import MusicJob
from src.tasks.job_worker import execute_job_pipeline
from src.providers.mock_provider import MockProvider


def test_worker_handles_provider_failure(clean_db, monkeypatch):
    """Verify that worker marks job as failed with standardized error code if provider fails."""
    # Insert queued job
    job_id = "job_test_failure_001"
    req_json = json.dumps({"prompt": "broken prompt", "duration_s": 10.0})

    with SessionLocal() as db:
        job = MusicJob(
            id=job_id,
            request_hash="dummy_hash",
            prompt="broken prompt",
            duration_s=10.0,
            status="queued",
            progress=0,
            request_json=req_json,
        )
        db.add(job)
        db.commit()

    # Simulate provider failure
    def broken_generate(*args, **kwargs):
        raise RuntimeError("Simulated upstream provider connection timeout")

    monkeypatch.setattr(MockProvider, "generate_music", broken_generate)

    # Execute pipeline
    execute_job_pipeline(job_id)

    # Verify state in database
    with SessionLocal() as db:
        updated_job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
        assert updated_job.status == "failed"
        assert updated_job.error_code in ("PROVIDER_TIMEOUT", "PROCESSING_FAILED")
        assert "Simulated upstream provider" in updated_job.error_message


def test_worker_pool_graceful_shutdown(clean_db):
    """Verify that shutting down the worker pool allows running jobs to drain to terminal state."""
    from src.tasks.job_worker import JobWorkerPool, execute_job_pipeline

    pool = JobWorkerPool(max_workers=2)
    job_id = "job_shutdown_test_001"
    req_json = json.dumps({"prompt": "soothing acoustic guitar", "duration_s": 5.0})

    with SessionLocal() as db:
        job = MusicJob(
            id=job_id,
            request_hash="hash_shutdown_001",
            prompt="soothing acoustic guitar",
            duration_s=5.0,
            status="queued",
            progress=0,
            request_json=req_json,
        )
        db.add(job)
        db.commit()

    # Submit to custom pool
    submitted = pool.submit_job(job_id)
    assert submitted is True

    # Initiate graceful shutdown
    pool.shutdown(wait=True, timeout=10.0)

    with SessionLocal() as db:
        finished_job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
        assert finished_job.status == "succeeded"
        assert finished_job.progress == 100


def test_worker_pool_rejects_jobs_when_shutting_down():
    """Verify that worker pool refuses new submissions when shutdown is active."""
    from src.tasks.job_worker import JobWorkerPool

    pool = JobWorkerPool(max_workers=2)
    pool.shutdown(wait=False)

    submitted = pool.submit_job("job_rejected_after_shutdown")
    assert submitted is False

