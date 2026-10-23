"""Unit tests for external provider adapters (Soundverse, ElevenLabs, and error handling)."""
import io
import zipfile
import pytest
import httpx

from src.providers.soundverse import SoundverseAdapter
from src.providers.elevenlabs import ElevenLabsAdapter
from src.providers.factory import get_provider


def test_provider_missing_key_raises_error():
    """Verify that adapters raise descriptive ValueErrors when API keys are missing."""
    sv_adapter = SoundverseAdapter(api_key=None)
    with pytest.raises(ValueError, match="SOUNDVERSE_API_KEY"):
        sv_adapter.generate_music("corporate pop", 15.0)

    el_adapter = ElevenLabsAdapter(api_key=None)
    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        el_adapter.generate_music("cinematic strings", 15.0)


def test_get_provider_factory():
    """Verify provider factory correctly instantiates providers."""
    mock_p = get_provider("mock")
    assert mock_p.provider_name == "mock"

    sv_p = get_provider("soundverse")
    assert sv_p.provider_name == "soundverse"

    el_p = get_provider("elevenlabs")
    assert el_p.provider_name == "elevenlabs"

    with pytest.raises(ValueError, match="Unsupported provider"):
        get_provider("invalid_provider_name")


def test_elevenlabs_mocked_network(monkeypatch):
    """Test ElevenLabs adapter serialization and ZIP extraction with mocked HTTP calls."""
    adapter = ElevenLabsAdapter(api_key="mock_xi_key")

    # Mock audio bytes
    fake_audio = b"RIFF....WAVEfmt...."

    def mock_post(client_self, url, *args, **kwargs):
        url_str = str(url)
        if "/v1/music" in url_str and "stem-separation" not in url_str:
            return httpx.Response(200, content=fake_audio, headers={"song_id": "song_123"})
        elif "stem-separation" in url_str:
            # Create a mock zip in memory with stems
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("drums.mp3", b"drum_data")
                z.writestr("bass.mp3", b"bass_data")
                z.writestr("other.mp3", b"other_data")
            return httpx.Response(200, content=buf.getvalue())
        return httpx.Response(404)

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    gen_res = adapter.generate_music("test prompt", duration_s=15.0)
    assert gen_res.provider == "elevenlabs"
    assert gen_res.audio_bytes == fake_audio
    assert gen_res.cost_usd > 0

    sep_res = adapter.separate_stems(gen_res.audio_bytes)
    assert len(sep_res.stems) == 3
    assert "drums" in sep_res.stems
    assert "bass" in sep_res.stems
    assert "other" in sep_res.stems
