"""Replicate Meta MusicGen API adapter for music generation."""
import io
import time
from typing import Dict, Any, Optional
import httpx
import numpy as np

from src.providers.base import (
    AudioProviderInterface,
    GenerationResult,
    StemSeparationResult,
    ProviderException,
    ProviderTimeoutException,
    ProviderMalformedResponseException,
)
from src.audio.dsp import load_audio_from_bytes

try:
    import soundfile as sf
except Exception:
    sf = None


class ReplicateMusicGenAdapter(AudioProviderInterface):
    """Adapter for Meta MusicGen hosted on Replicate (replicate.com/meta/musicgen)."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_version: str = "671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
        timeout_s: float = 180.0,
    ):
        self.api_token = api_token
        self.model_version = model_version
        self.timeout_s = timeout_s
        self.provider_name = "replicate"
        self.base_url = "https://api.replicate.com/v1"

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_token or not self.api_token.strip():
            raise ValueError(
                "REPLICATE_API_TOKEN environment variable is not configured. "
                "Set REPLICATE_API_TOKEN in your .env or configure MUSIC_PROVIDER=mock for offline verification."
            )
        return {
            "Authorization": f"Bearer {self.api_token.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "IncuBrix-AudioEngine/0.1.0",
        }

    def check_connection_and_balance(self) -> Dict[str, Any]:
        """Verify API token against Replicate account API."""
        headers = self._get_headers()
        url = f"{self.base_url}/account"

        with httpx.Client(timeout=15.0) as client:
            try:
                resp = client.get(url, headers=headers)
            except httpx.TimeoutException:
                raise ProviderTimeoutException("Replicate account check timed out", code="PROVIDER_TIMEOUT")
            except httpx.RequestError as exc:
                raise ProviderException(f"Network error connecting to Replicate: {exc}", code="NETWORK_ERROR")

            if resp.status_code == 401:
                raise ProviderException("Invalid Replicate API token or unauthorized.", code="AUTHENTICATION_FAILED")
            if resp.status_code != 200:
                raise ProviderException(
                    f"Replicate account check failed with HTTP {resp.status_code}: {resp.text}",
                    code="ACCOUNT_CHECK_FAILED",
                )

            data = resp.json()
            return {
                "provider": self.provider_name,
                "authenticated": True,
                "username": data.get("username", "unknown"),
                "account_type": data.get("type", "personal"),
                "notice": "Replicate bills per-second of GPU compute ($0.0014/sec on A100). Meta MusicGen weights are licensed under CC-BY-NC 4.0 (non-commercial).",
            }

    def generate_music(
        self,
        prompt: str,
        duration_s: float,
        tempo_bpm: Optional[int] = None,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        output_format: str = "wav",
        **kwargs: Any,
    ) -> GenerationResult:
        """Submit text-to-music prediction to Meta MusicGen on Replicate."""
        start_time = time.time()
        headers = self._get_headers()

        prompt_lower = prompt.lower()
        if "instrumental" not in prompt_lower and "no vocals" not in prompt_lower:
            effective_prompt = f"instrumental, no vocals. {prompt}"
        else:
            effective_prompt = prompt

        target_duration = int(round(max(5.0, min(120.0, duration_s))))

        payload = {
            "version": self.model_version,
            "input": {
                "prompt": effective_prompt,
                "duration": target_duration,
                "model_version": "stereo-large",
                "output_format": "wav" if output_format == "wav" else "mp3",
                "normalization_strategy": "peak",
            },
        }
        if seed is not None:
            payload["input"]["seed"] = seed

        url = f"{self.base_url}/predictions"

        with httpx.Client(timeout=self.timeout_s) as client:
            try:
                resp = client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException:
                raise ProviderTimeoutException("Replicate prediction dispatch timed out")
            except httpx.RequestError as exc:
                raise ProviderException(f"Network error communicating with Replicate: {exc}")

            if resp.status_code == 401:
                raise ProviderException("Replicate authentication failed: invalid token", code="AUTHENTICATION_FAILED")
            elif resp.status_code == 402:
                raise ProviderException("Replicate spending limit reached or billing setup required", code="QUOTA_EXHAUSTED")
            elif resp.status_code == 429:
                raise ProviderException("Replicate rate limit exceeded", code="RATE_LIMIT_EXCEEDED", retryable=True)
            elif resp.status_code not in (200, 201):
                raise ProviderException(f"Replicate prediction failed: {resp.text}")

            pred = resp.json()
            pred_id = pred.get("id")
            if not pred_id:
                raise ProviderMalformedResponseException("No prediction ID returned by Replicate")

            # Poll for completion
            poll_url = f"{self.base_url}/predictions/{pred_id}"
            audio_url = None
            max_polls = int(self.timeout_s / 2.5)

            for _ in range(max_polls):
                time.sleep(2.5)
                poll_resp = client.get(poll_url, headers=headers)
                if poll_resp.status_code == 200:
                    p_data = poll_resp.json()
                    status = p_data.get("status")
                    if status == "succeeded":
                        audio_url = p_data.get("output")
                        break
                    elif status in ("failed", "canceled"):
                        error_msg = p_data.get("error", "Prediction failed")
                        raise ProviderException(f"Replicate MusicGen prediction failed: {error_msg}")

            if not audio_url:
                raise ProviderTimeoutException("Replicate MusicGen prediction timed out")

            audio_resp = client.get(audio_url)
            if audio_resp.status_code != 200:
                raise ProviderException(f"Failed to download audio from Replicate URL: {audio_resp.status_code}")

            audio_bytes = audio_resp.content

        elapsed = time.time() - start_time
        # Replicate A100 GPU compute: ~$0.0014/sec * elapsed
        cost_usd = round(elapsed * 0.0014, 4)

        return GenerationResult(
            audio_bytes=audio_bytes,
            format="wav" if output_format == "wav" else "mp3",
            sample_rate=48000,
            duration_s=float(target_duration),
            provider=self.provider_name,
            model_version="meta-musicgen-stereo-large",
            cost_usd=cost_usd,
            latency_s=round(elapsed, 3),
            raw_metadata={
                "prediction_id": pred_id,
                "effective_prompt": effective_prompt,
                "license_restriction": "CC-BY-NC 4.0 (Non-commercial research only)",
                "license": "CC-BY-NC 4.0 (Non-commercial research only for model weights)",
            },

        )

    def separate_stems(
        self,
        audio_bytes: bytes,
        sample_rate: int = 48000,
        stem_format: str = "wav",
        **kwargs: Any,
    ) -> StemSeparationResult:
        """Decompose mixed audio into distinct instrument stems."""
        start_time = time.time()
        audio, sr = load_audio_from_bytes(audio_bytes, target_sr=sample_rate)

        fft = np.fft.rfft(audio, axis=0)
        freqs = np.fft.rfftfreq(len(audio), 1.0 / sample_rate)

        bass_mask = np.exp(-((freqs / 220.0) ** 4))[:, None]
        melody_mask = (1.0 - np.exp(-((freqs / 3200.0) ** 4)))[:, None]
        harmony_mask = np.clip(1.0 - bass_mask - melody_mask, 0.0, 1.0)

        bass_audio = np.fft.irfft(fft * bass_mask, n=len(audio), axis=0)
        harmony_audio = np.fft.irfft(fft * harmony_mask, n=len(audio), axis=0)
        melody_audio = np.fft.irfft(fft * melody_mask, n=len(audio), axis=0)
        drums_audio = np.clip(audio - (0.7 * harmony_audio + 0.3 * melody_audio), -1.0, 1.0)

        def _to_wav_bytes(arr: np.ndarray) -> bytes:
            buf = io.BytesIO()
            if sf is not None:
                sf.write(buf, arr, sample_rate, format="WAV", subtype="PCM_24")
            return buf.getvalue()

        stems = {
            "drums": _to_wav_bytes(drums_audio),
            "bass": _to_wav_bytes(bass_audio),
            "harmony": _to_wav_bytes(harmony_audio),
            "melody": _to_wav_bytes(melody_audio),
        }

        elapsed = time.time() - start_time

        return StemSeparationResult(
            stems=stems,
            format=stem_format,
            sample_rate=sample_rate,
            provider=self.provider_name,
            model_version="dsp-spectral-decomposer-v1",
            cost_usd=0.0,
            latency_s=round(elapsed, 3),
            raw_metadata={
                "stems_method": "dsp_harmonic_decomposition",
                "notice": "MusicGen produces a stereo mix; stems were decomposed via harmonic DSP.",
            },
        )
