"""Provider factory for instantiating the active audio provider adapter."""
import logging
from typing import Optional

from src.config import settings
from src.providers.base import AudioProviderInterface
from src.providers.mock_provider import MockProvider
from src.providers.soundverse import SoundverseAdapter
from src.providers.elevenlabs import ElevenLabsAdapter
from src.providers.stable_audio import StableAudioAdapter
from src.providers.replicate import ReplicateMusicGenAdapter

logger = logging.getLogger(__name__)


def get_provider(provider_name: Optional[str] = None) -> AudioProviderInterface:
    """Instantiate and return the configured audio provider adapter."""
    name = (provider_name or settings.music_provider).lower()

    if name == "auto":
        if settings.stability_api_key:
            name = "stable_audio"
        elif settings.soundverse_api_key:
            name = "soundverse"
        elif settings.elevenlabs_api_key:
            name = "elevenlabs"
        elif settings.replicate_api_token:
            name = "replicate"
        else:
            logger.info("No external provider API keys found. Defaulting to 'mock' provider.")
            name = "mock"

    if name in ("stable_audio", "stability", "stableaudio"):
        return StableAudioAdapter(
            api_key=settings.stability_api_key,
            base_url=settings.stability_base_url,
            model_version=settings.stability_model,
        )
    elif name in ("replicate", "musicgen"):
        return ReplicateMusicGenAdapter(
            api_token=settings.replicate_api_token,
        )
    elif name == "soundverse":
        return SoundverseAdapter(
            api_key=settings.soundverse_api_key,
            base_url=settings.soundverse_base_url,
        )
    elif name == "elevenlabs":
        return ElevenLabsAdapter(
            api_key=settings.elevenlabs_api_key,
            base_url=settings.elevenlabs_base_url,
        )
    elif name == "mock":
        return MockProvider(sample_rate=settings.default_sample_rate)
    else:
        raise ValueError(
            f"Unsupported provider: '{name}'. Choose from 'mock', 'stable_audio', 'replicate', 'soundverse', 'elevenlabs', or 'auto'."
        )

