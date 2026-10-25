"""Configuration management for IncuBrix AI Background Music Engine."""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_serverless_or_readonly() -> bool:
    """Detect if running in Vercel, AWS Lambda, or a read-only filesystem."""
    serverless_keys = (
        "VERCEL",
        "VERCEL_ENV",
        "VERCEL_URL",
        "VERCEL_REGION",
        "AWS_LAMBDA_FUNCTION_NAME",
        "LAMBDA_TASK_ROOT",
        "AWS_EXECUTION_ENV",
    )
    if any(k in os.environ for k in serverless_keys):
        return True
    try:
        test_path = os.path.join(os.getcwd(), ".write_test")
        with open(test_path, "w") as f:
            f.write("1")
        os.remove(test_path)
        return False
    except (OSError, PermissionError):
        return True


class Settings(BaseSettings):
    """Application and Provider settings loaded from environment variables."""

    # Active Provider: 'mock', 'soundverse', or 'elevenlabs'
    music_provider: Literal["mock", "soundverse", "elevenlabs"] = "mock"

    # Soundverse Settings
    soundverse_api_key: Optional[str] = None
    soundverse_base_url: str = "https://apiv2.soundverse.ai"

    # ElevenLabs Settings
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io"

    # Database Settings (PostgreSQL in container, SQLite locally or /tmp in Vercel)
    database_url: str = (
        "sqlite:////tmp/incubrix.db"
        if _is_serverless_or_readonly()
        else "sqlite:///./incubrix.db"
    )

    # Redis and Celery Settings
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_enabled: bool = False

    # MinIO / Object Storage Settings
    storage_backend: Literal["minio", "local"] = "local"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "incubrix-audio"
    minio_secure: bool = False
    local_storage_dir: str = (
        "/tmp/storage_data"
        if _is_serverless_or_readonly()
        else "./storage_data"
    )

    # Security & Webhook Callback Settings
    callback_secret: str = "incubrix-default-hmac-secret-change-in-prod"
    max_upload_size_bytes: int = 52428800  # 50 MB
    demo_api_key: Optional[str] = None  # Optional API token for live demo protection
    rate_limit_per_minute: int = 60

    # DSP & Audio Engineering Standards (ITU-R BS.1770-4)
    default_sample_rate: int = 48000
    target_lufs: float = -16.0
    target_true_peak_dbtp: float = -1.0
    duration_tolerance_s: float = 0.05

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


# Singleton instance
settings = Settings()
