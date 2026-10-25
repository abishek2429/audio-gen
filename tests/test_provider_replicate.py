"""Automated tests for Replicate Meta MusicGen adapter."""
import io
import pytest
import httpx
import soundfile as sf
import numpy as np

from src.providers.replicate import ReplicateMusicGenAdapter
from src.providers.base import ProviderException, ProviderTimeoutException


def _generate_synthetic_wav_bytes(duration_s: float = 3.0, sr: int = 32000) -> bytes:
    """Generate minimal valid WAV bytes."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    synth = np.sin(2 * np.pi * 440.0 * t)[:, None]
    buf = io.BytesIO()
    sf.write(buf, synth, sr, format="WAV")
    return buf.getvalue()


def test_replicate_missing_token():
    """Verify ValueError when REPLICATE_API_TOKEN is missing."""
    adapter = ReplicateMusicGenAdapter(api_token=None)
    with pytest.raises(ValueError, match="REPLICATE_API_TOKEN"):
        adapter.generate_music("test prompt", 10.0)

    with pytest.raises(ValueError, match="REPLICATE_API_TOKEN"):
        adapter.check_connection_and_balance()


def test_replicate_account_check(monkeypatch):
    """Verify check_connection_and_balance calls /account endpoint."""
    adapter = ReplicateMusicGenAdapter(api_token="r8_mock_token")

    def mock_get(client_self, url, headers=None, **kwargs):
        assert "Bearer r8_mock_token" in headers["Authorization"]
        assert "/account" in str(url)
        return httpx.Response(200, json={"username": "incubrix-dev", "type": "personal"})

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    info = adapter.check_connection_and_balance()
    assert info["authenticated"] is True
    assert info["username"] == "incubrix-dev"
    assert "CC-BY-NC 4.0" in info["notice"]


def test_replicate_generation_lifecycle(monkeypatch):
    """Verify Replicate prediction creation, polling, and audio download."""
    adapter = ReplicateMusicGenAdapter(api_token="r8_mock_token")
    fake_wav = _generate_synthetic_wav_bytes(duration_s=5.0)

    def mock_post(client_self, url, json=None, **kwargs):
        assert "/predictions" in str(url)
        return httpx.Response(201, json={
            "id": "pred_123",
            "status": "starting",
            "urls": {"get": "https://api.replicate.com/v1/predictions/pred_123"}
        })

    poll_count = 0
    def mock_get(client_self, url, **kwargs):
        nonlocal poll_count
        url_str = str(url)
        if "pred_123" in url_str:
            poll_count += 1
            if poll_count < 2:
                return httpx.Response(200, json={"status": "processing"})
            return httpx.Response(200, json={
                "status": "succeeded",
                "output": "https://replicate.delivery/pbxt/fake_audio.wav",
                "metrics": {"predict_time": 4.2}
            })
        elif "fake_audio.wav" in url_str:
            return httpx.Response(200, content=fake_wav)
        return httpx.Response(404)

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    monkeypatch.setattr(httpx.Client, "get", mock_get)

    gen_res = adapter.generate_music("Epic orchestral swell", duration_s=5.0)
    assert gen_res.provider == "replicate"
    assert gen_res.duration_s == 5.0
    assert gen_res.audio_bytes == fake_wav
    assert gen_res.raw_metadata["license_restriction"] == "CC-BY-NC 4.0 (Non-commercial research only)"
