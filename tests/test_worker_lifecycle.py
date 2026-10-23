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
        assert updated_job.error_code == "PROCESSING_FAILED"
        assert "Simulated upstream provider" in updated_job.error_message
