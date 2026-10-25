"""Automated tests for Stability AI Stable Audio adapter."""
import io
import pytest
import httpx
import soundfile as sf
import numpy as np

from src.providers.stable_audio import StableAudioAdapter
from src.providers.base import (
    ProviderException,
    ProviderTimeoutException,
    ProviderMalformedResponseException,
)


def _generate_synthetic_wav_bytes(duration_s: float = 3.0, sr: int = 48000) -> bytes:
    """Generate minimal valid stereo WAV bytes for mock responses."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    synth = np.sin(2 * np.pi * 440.0 * t)[:, None]
    stereo = np.repeat(synth, 2, axis=1) * 0.3
    buf = io.BytesIO()
    sf.write(buf, stereo, sr, format="WAV")
    return buf.getvalue()


def test_stable_audio_missing_key():
    """Verify that adapter raises ValueError when STABILITY_API_KEY is not configured."""
    adapter = StableAudioAdapter(api_key=None)
    with pytest.raises(ValueError, match="STABILITY_API_KEY"):
        adapter.generate_music("test prompt", 10.0)

    with pytest.raises(ValueError, match="STABILITY_API_KEY"):
        adapter.check_connection_and_balance()


def test_stable_audio_balance_check(monkeypatch):
    """Verify check_connection_and_balance successfully queries Stability AI."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")

    def mock_get(client_self, url, headers=None, **kwargs):
        assert "Authorization" in headers
        assert "Bearer sk-test-mock-key" in headers["Authorization"]
        assert "/v1/user/balance" in str(url)
        return httpx.Response(200, json={"credits": 45.0})

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    info = adapter.check_connection_and_balance()
    assert info["authenticated"] is True
    assert info["credits_balance"] == 45.0
    assert info["generations_remaining"] == 2
    assert info["has_sufficient_quota"] is True


def test_stable_audio_balance_auth_failure(monkeypatch):
    """Verify authentication failure (HTTP 401) raises ProviderException."""
    adapter = StableAudioAdapter(api_key="sk-invalid-key")

    def mock_get(client_self, url, **kwargs):
        return httpx.Response(401, json={"error": "unauthorized"})

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    with pytest.raises(ProviderException) as exc_info:
        adapter.check_connection_and_balance()
    assert exc_info.value.code == "AUTHENTICATION_FAILED"


def test_stable_audio_immediate_200_generation(monkeypatch):
    """Verify immediate 200 audio binary response is parsed correctly."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")
    fake_wav = _generate_synthetic_wav_bytes(duration_s=5.0)

    def mock_post(client_self, url, data=None, headers=None, **kwargs):
        assert "/v2beta/audio/stable-audio/text-to-audio" in str(url)
        assert data["prompt"].startswith("Instrumental background music")
        assert data["duration"] == "5"
        return httpx.Response(200, content=fake_wav, headers={"Content-Type": "audio/wav"})

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    gen_res = adapter.generate_music("Upbeat corporate groove", duration_s=5.0, output_format="wav")
    assert gen_res.provider == "stable_audio"
    assert gen_res.duration_s == 5.0
    assert gen_res.cost_usd == 0.20
    assert gen_res.audio_bytes == fake_wav
    assert gen_res.raw_metadata["credits_charged"] == 20


def test_stable_audio_async_202_polling(monkeypatch):
    """Verify 202 Accepted response polls /v2beta/audio/results/{id} until 200."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")
    fake_wav = _generate_synthetic_wav_bytes(duration_s=8.0)
    poll_count = 0

    def mock_post(client_self, url, **kwargs):
        return httpx.Response(202, json={"id": "task_abc123"})

    def mock_get(client_self, url, **kwargs):
        nonlocal poll_count
        poll_count += 1
        if poll_count < 2:
            return httpx.Response(202, json={"status": "in-progress"})
        return httpx.Response(200, content=fake_wav)

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    monkeypatch.setattr(httpx.Client, "get", mock_get)

    gen_res = adapter.generate_music("Cinematic strings", duration_s=8.0)
    assert gen_res.provider == "stable_audio"
    assert poll_count == 2
    assert gen_res.audio_bytes == fake_wav


def test_stable_audio_quota_exhausted_402(monkeypatch):
    """Verify HTTP 402/403 with insufficient credits raises QUOTA_EXHAUSTED."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")

    def mock_post(client_self, url, **kwargs):
        return httpx.Response(402, text="Your account does not have enough credits to perform this request.")

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderException) as exc_info:
        adapter.generate_music("Test prompt", duration_s=10.0)
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


def test_stable_audio_rate_limit_429(monkeypatch):
    """Verify HTTP 429 raises RATE_LIMIT_EXCEEDED."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")

    def mock_post(client_self, url, **kwargs):
        return httpx.Response(429, text="Rate limit exceeded.")

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderException) as exc_info:
        adapter.generate_music("Test prompt", duration_s=10.0)
    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
    assert exc_info.value.retryable is True


def test_stable_audio_stem_separation_dsp():
    """Verify stem separation decomposes stereo mix into 4 valid stems."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")
    fake_wav = _generate_synthetic_wav_bytes(duration_s=3.0)

    sep_res = adapter.separate_stems(fake_wav)
    assert sep_res.provider == "stable_audio"
    assert len(sep_res.stems) == 4
    for stem_name in ("drums", "bass", "harmony", "melody"):
        assert stem_name in sep_res.stems
        assert len(sep_res.stems[stem_name]) > 0
    assert sep_res.raw_metadata["stems_method"] == "dsp_harmonic_decomposition"


def test_stable_audio_rate_limit_with_retry_after(monkeypatch):
    """Verify HTTP 429 parses Retry-After header."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")

    def mock_post(client_self, url, **kwargs):
        return httpx.Response(429, headers={"Retry-After": "45"}, text="Rate limit exceeded.")

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderException) as exc_info:
        adapter.generate_music("Test", duration_s=5.0)
    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"
    assert "45" in str(exc_info.value)


def test_stable_audio_empty_audio_raises_malformed(monkeypatch):
    """Verify empty or truncated audio bytes raises ProviderMalformedResponseException."""
    adapter = StableAudioAdapter(api_key="sk-test-mock-key")

    def mock_post(client_self, url, **kwargs):
        return httpx.Response(200, content=b"too short")

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(ProviderMalformedResponseException):
        adapter.generate_music("Test", duration_s=5.0)
