"""ElevenLabs Music API adapter for music generation and multitrack stem separation."""
import time
import io
import zipfile
from typing import Dict, Any, Optional
import httpx

from src.providers.base import (
    AudioProviderInterface,
    GenerationResult,
    StemSeparationResult,
)


class ElevenLabsAdapter(AudioProviderInterface):
    """Adapter for ElevenLabs Music API (api.elevenlabs.io)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.elevenlabs.io",
        timeout_s: float = 180.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.provider_name = "elevenlabs"
        self.model_version = "music_v2"
        self.separation_engine = "six_stems_v1"

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY environment variable is not set. "
                "Set ELEVENLABS_API_KEY or configure MUSIC_PROVIDER=mock for offline testing."
            )
        return {
            "xi-api-key": self.api_key,
            "User-Agent": "IncuBrix-AudioEngine/0.1.0",
        }

    def generate_music(
        self,
        prompt: str,
        duration_s: float,
        tempo_bpm: Optional[int] = None,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Synchronously compose music cue using Eleven Music v2 model."""
        start_time = time.time()
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        # Explicit millisecond length (3000 to 600000 ms)
        length_ms = int(max(3.0, min(600.0, duration_s)) * 1000)

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "music_length_ms": length_ms,
            "model_id": self.model_version,
            "force_instrumental": True,
            "respect_sections_durations": True,
        }
        if seed is not None:
            payload["seed"] = seed

        url = f"{self.base_url}/v1/music?output_format=mp3_48000_320"

        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"ElevenLabs generation failed with HTTP {resp.status_code}: {resp.text}"
                )

            audio_bytes = resp.content
            song_id = resp.headers.get("song_id", "unknown_song_id")

        elapsed = time.time() - start_time
        # Cost estimate: 900 credits per minute ≈ $0.15 / min
        cost_usd = round((duration_s / 60.0) * 0.15, 4)

        return GenerationResult(
            audio_bytes=audio_bytes,
            format="mp3",
            sample_rate=48000,
            duration_s=duration_s,
            provider=self.provider_name,
            model_version=self.model_version,
            cost_usd=cost_usd,
            latency_s=elapsed,
            raw_metadata={
                "song_id": song_id,
                "force_instrumental": True,
                "music_length_ms": length_ms,
            },
        )

    def separate_stems(
        self,
        audio_bytes: bytes,
        sample_rate: int = 48000,
        stem_format: str = "wav",
        **kwargs: Any,
    ) -> StemSeparationResult:
        """Call ElevenLabs stem separation endpoint returning ZIP archive."""
        start_time = time.time()
        headers = self._get_headers()

        url = f"{self.base_url}/v1/music/stem-separation?output_format=mp3_48000_320"
        files = {
            "file": ("mix.wav", audio_bytes, "audio/wav"),
        }
        data = {
            "stem_variation_id": self.separation_engine,
        }

        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, files=files, data=data, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"ElevenLabs stem separation failed with HTTP {resp.status_code}: {resp.text}"
                )

            zip_bytes = resp.content

        # Unpack ZIP archive into stem audio buffers
        stems: Dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for filename in z.namelist():
                if filename.lower().endswith((".wav", ".mp3", ".ogg")):
                    stem_name = filename.rsplit(".", 1)[0].lower()
                    stems[stem_name] = z.read(filename)

        elapsed = time.time() - start_time
        cost_usd = 0.15  # Equivalent to generation credit charge

        return StemSeparationResult(
            stems=stems,
            format="mp3",
            sample_rate=sample_rate,
            provider=self.provider_name,
            model_version=self.separation_engine,
            cost_usd=cost_usd,
            latency_s=elapsed,
            raw_metadata={
                "stems_extracted": list(stems.keys()),
            },
        )
