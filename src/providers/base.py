"""Abstract base interfaces and dataclasses for audio generation and stem separation."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class GenerationResult:
    """Output from an AI music generation provider."""
    audio_bytes: bytes
    format: str  # "wav" or "mp3"
    sample_rate: int
    duration_s: float
    provider: str
    model_version: str
    cost_usd: float
    latency_s: float
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StemSeparationResult:
    """Output from a stem separation engine."""
    stems: Dict[str, bytes]  # {'drums': bytes, 'bass': bytes, ...}
    format: str  # "wav" or "mp3"
    sample_rate: int
    provider: str
    model_version: str
    cost_usd: float
    latency_s: float
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class MusicGeneratorInterface(ABC):
    """Interface for text-to-music generation."""

    @abstractmethod
    def generate_music(
        self,
        prompt: str,
        duration_s: float,
        tempo_bpm: Optional[int] = None,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate an instrumental audio track matching prompt and duration."""
        pass


class StemSeparatorInterface(ABC):
    """Interface for multi-stem audio separation."""

    @abstractmethod
    def separate_stems(
        self,
        audio_bytes: bytes,
        sample_rate: int = 48000,
        stem_format: str = "wav",
        **kwargs: Any,
    ) -> StemSeparationResult:
        """Separate mixed audio into at least three genuine instrument tracks."""
        pass


class AudioProviderInterface(MusicGeneratorInterface, StemSeparatorInterface, ABC):
    """Combined provider capable of both generation and stem separation."""
    pass
