"""Configuration management for IncuBrix AI Background Music Engine."""
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # DSP & Audio Engineering Standards
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
