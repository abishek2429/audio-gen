"""Celery application configuration for IncuBrix background workers."""
from celery import Celery
from src.config import settings

celery_app = Celery(
    "incubrix_audio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks.job_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5-minute hard limit
    worker_prefetch_multiplier=1,
)
