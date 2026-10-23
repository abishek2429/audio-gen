"""Unit tests for MockProvider procedural synthesis and linear stem reconstructability."""
import io
import numpy as np
import soundfile as sf
import pytest

from src.providers.mock_provider import MockProvider


def test_mock_provider_generation():
    """Verify that MockProvider generates valid 48kHz audio with required stems."""
    provider = MockProvider(sample_rate=48000)
    res = provider.generate_music(
        prompt="corporate acoustic folk",
        duration_s=10.0,
        tempo_bpm=120,
        key="C major",
        seed=42,
    )

    assert res.provider == "mock"
    assert res.sample_rate == 48000
    assert res.format == "wav"
    assert res.duration_s == pytest.approx(10.0, abs=0.01)
    assert len(res.audio_bytes) > 0

    # Read audio back
    audio, sr = sf.read(io.BytesIO(res.audio_bytes))
    assert sr == 48000
    assert audio.ndim == 2
    assert len(audio) == int(10.0 * 48000)


def test_mock_provider_separation_and_reconstructability():
    """Verify that MockProvider stem separation returns at least 3 genuine stems

    whose linear sum exactly reconstructs the generated mix.
    """
    provider = MockProvider(sample_rate=48000)
    gen_res = provider.generate_music(
        prompt="cinematic build-up",
        duration_s=6.0,
        seed=100,
    )

    sep_res = provider.separate_stems(gen_res.audio_bytes, sample_rate=48000)

    # Must contain at least 3 distinct stems
    assert len(sep_res.stems) >= 3
    assert "drums" in sep_res.stems
    assert "bass" in sep_res.stems
    assert "harmony" in sep_res.stems
    assert "melody" in sep_res.stems

    # Load mix and all stems
    mix_audio, _ = sf.read(io.BytesIO(gen_res.audio_bytes), dtype="float64")
    stem_sum = np.zeros_like(mix_audio)

    for stem_name, stem_bytes in sep_res.stems.items():
        s_audio, sr = sf.read(io.BytesIO(stem_bytes), dtype="float64")
        assert sr == 48000
        assert len(s_audio) == len(mix_audio)
        stem_sum += s_audio

    # Measure reconstruction residual
    residual = mix_audio - stem_sum
    signal_power = np.sum(mix_audio ** 2)
    noise_power = np.sum(residual ** 2)
    sdr_db = 10.0 * np.log10(signal_power / (noise_power + 1e-12))

    # Procedural mock must have near-perfect reconstructability (> 80 dB)
    assert sdr_db > 80.0


def test_mock_provider_seed_determinism():
    """Verify that identical seeds produce bit-identical audio."""
    provider1 = MockProvider(sample_rate=48000)
    provider2 = MockProvider(sample_rate=48000)

    res1 = provider1.generate_music("chill lo-fi", duration_s=5.0, seed=777)
    res2 = provider2.generate_music("chill lo-fi", duration_s=5.0, seed=777)

    assert res1.audio_bytes == res2.audio_bytes
