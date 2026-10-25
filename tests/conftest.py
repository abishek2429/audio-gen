"""Pytest configuration and test client fixtures."""
import os
import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.database.session import init_db, SessionLocal
from src.database.models import Base, MusicJob
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure environment for automated offline test execution."""
    settings.celery_enabled = False
    settings.storage_backend = "local"
    settings.local_storage_dir = "./storage_data_test"
    settings.music_provider = "mock"
    settings.app_env = "testing"
    init_db()


@pytest.fixture(autouse=True)
def isolate_test_state():
    """Reset rate limiter and wait for background worker threads between tests."""
    from src.security import global_rate_limiter
    from src.tasks.job_worker import ensure_worker_pool_active, wait_for_active_jobs
    ensure_worker_pool_active()
    global_rate_limiter.reset()
    yield
    wait_for_active_jobs(timeout=5.0)
    ensure_worker_pool_active()
    global_rate_limiter.reset()




@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def clean_db():
    """Clean the music_jobs table between tests."""
    with SessionLocal() as db:
        db.query(MusicJob).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(MusicJob).delete()
        db.commit()
