"""Soundverse Enterprise API adapter for music generation and Demucs 6-stem separation."""
import time
import io
from typing import Dict, Any, Optional
import httpx

from src.providers.base import (
    AudioProviderInterface,
    GenerationResult,
    StemSeparationResult,
)


class SoundverseAdapter(AudioProviderInterface):
    """Adapter for Soundverse Enterprise Gateway (apiv2.soundverse.ai)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://apiv2.soundverse.ai",
        timeout_s: float = 120.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.provider_name = "soundverse"
        self.model_version = "soundverse-v7"
        self.separation_engine = "demucs-htdemucs_6s"

    def _get_headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "SOUNDVERSE_API_KEY environment variable is not set. "
                "Set SOUNDVERSE_API_KEY or configure MUSIC_PROVIDER=mock for offline testing."
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "IncuBrix-AudioEngine/0.1.0",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def generate_music(
        self,
        prompt: str,
        duration_s: float,
        tempo_bpm: Optional[int] = None,
        key: Optional[str] = None,
        seed: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Submit text-to-music task to Soundverse API and poll for completion."""
        start_time = time.time()
        headers = self._get_headers(idempotency_key)

        # Enhance prompt with instrumental and tempo constraints if needed
        enhanced_prompt = f"Instrumental only, no vocals. {prompt}"
        if tempo_bpm:
            enhanced_prompt += f", tempo {tempo_bpm} BPM"
        if key:
            enhanced_prompt += f", key of {key}"

        payload = {
            "prompt": enhanced_prompt,
            "parameters": {
                "versions": 1,
            },
        }

        url = f"{self.base_url}/v7/generate/music"

        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201, 202):
                raise RuntimeError(
                    f"Soundverse generation request failed with HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            job_id = data.get("job_id") or data.get("id")
            if not job_id:
                raise RuntimeError(f"No job_id returned by Soundverse: {data}")

            # Poll for completion
            status_url = f"{self.base_url}/v1/generations/{job_id}"
            audio_url = None
            max_polls = int(self.timeout_s / 2.0)

            for _ in range(max_polls):
                time.sleep(2.0)
                status_resp = client.get(status_url, headers=headers)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    if status == "completed":
                        assets = status_data.get("output", {}).get("assets", [])
                        for asset in assets:
                            if asset.get("role") in ("mix", "primary", "audio"):
                                audio_url = asset.get("url")
                                break
                        if not audio_url and assets:
                            audio_url = assets[0].get("url")
                        break
                    elif status == "failed":
                        error_msg = status_data.get("error", "Unknown Soundverse task failure")
                        raise RuntimeError(f"Soundverse task {job_id} failed: {error_msg}")

            if not audio_url:
                raise TimeoutError(f"Soundverse task {job_id} timed out after {self.timeout_s}s")

            # Download generated audio asset
            download_resp = client.get(audio_url)
            if download_resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to download audio asset from {audio_url}: HTTP {download_resp.status_code}"
                )

            audio_bytes = download_resp.content

        elapsed = time.time() - start_time
        # Standard commercial tier: $0.11 per track
        cost_usd = 0.11

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
                "job_id": job_id,
                "asset_url": audio_url,
                "license_tier": "Standard ($0.11)",
            },
        )

    def separate_stems(
        self,
        audio_bytes: bytes,
        sample_rate: int = 48000,
        stem_format: str = "wav",
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> StemSeparationResult:
        """Call Soundverse 6-stem separation endpoint (Meta Demucs backend)."""
        start_time = time.time()
        headers = self._get_headers(idempotency_key)
        # Remove Content-Type so multipart boundary is generated automatically
        headers_multipart = {k: v for k, v in headers.items() if k.lower() != "content-type"}

        url = f"{self.base_url}/v1/generate/stem-separation/six-stem"
        files = {"audio": ("mix.wav", audio_bytes, "audio/wav")}

        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, files=files, headers=headers_multipart)
            if resp.status_code not in (200, 201, 202):
                raise RuntimeError(
                    f"Soundverse stem separation request failed with HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            job_id = data.get("job_id") or data.get("id")
            if not job_id:
                raise RuntimeError(f"No job_id returned by Soundverse separation: {data}")

            # Poll for completion
            status_url = f"{self.base_url}/v1/generations/{job_id}"
            stems_assets = {}
            max_polls = int(self.timeout_s / 2.0)

            for _ in range(max_polls):
                time.sleep(2.0)
                status_resp = client.get(status_url, headers=headers)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    if status == "completed":
                        assets = status_data.get("output", {}).get("assets", [])
                        for asset in assets:
                            stem_name = asset.get("role") or asset.get("stem_name")
                            stem_url = asset.get("url")
                            if stem_name and stem_url:
                                stems_assets[stem_name] = stem_url
                        break
                    elif status == "failed":
                        error_msg = status_data.get("error", "Soundverse separation failed")
                        raise RuntimeError(f"Soundverse separation task {job_id} failed: {error_msg}")

            if not stems_assets:
                raise TimeoutError(f"Soundverse separation task {job_id} timed out")

            downloaded_stems: Dict[str, bytes] = {}
            for name, download_url in stems_assets.items():
                d_resp = client.get(download_url)
                if d_resp.status_code == 200:
                    downloaded_stems[name] = d_resp.content

        elapsed = time.time() - start_time
        # Flat separation cost: $0.10
        cost_usd = 0.10

        return StemSeparationResult(
            stems=downloaded_stems,
            format=stem_format,
            sample_rate=sample_rate,
            provider=self.provider_name,
            model_version=self.separation_engine,
            cost_usd=cost_usd,
            latency_s=elapsed,
            raw_metadata={
                "job_id": job_id,
                "stems_count": len(downloaded_stems),
            },
        )
