"""Provider interfaces and implementations for music generation and stem separation."""
from src.providers.base import (
    GenerationResult,
    StemSeparationResult,
    MusicGeneratorInterface,
    StemSeparatorInterface,
    AudioProviderInterface,
)
from src.providers.mock_provider import MockProvider
from src.providers.soundverse import SoundverseAdapter
from src.providers.elevenlabs import ElevenLabsAdapter
from src.providers.factory import get_provider

__all__ = [
    "GenerationResult",
    "StemSeparationResult",
    "MusicGeneratorInterface",
    "StemSeparatorInterface",
    "AudioProviderInterface",
    "MockProvider",
    "SoundverseAdapter",
    "ElevenLabsAdapter",
    "get_provider",
]
