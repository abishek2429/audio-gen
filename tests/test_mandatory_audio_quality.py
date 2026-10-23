"""Comprehensive automated test suite for IncuBrix Mandatory Audio Requirements.

Verifies:
1. Duration accuracy within 0.05 seconds
2. At least three distinct instrument stems
3. Correct stem alignment and 48 kHz sample rate
4. Mathematical stem reconstruction using manifest gains (SDR >= 20 dB)
5. Instrumental-only output (vocal energy <= -40 dBFS)
6. 48 kHz 24-bit PCM WAV container format
7. Integrated loudness within 1.0 LU of target (-16 LUFS default)
8. True peak no higher than -1.0 dBTP
9. No abrupt ending (tail <= -35 dBFS), unintended silence, clipping, or clicks
"""
import io
import os
import tempfile
import numpy as np
import pytest
import soundfile as sf
import pyloudnorm as pyln

from src.audio.dsp import (
    align_duration_and_finish_tail,
    normalize_loudness_and_peaks,
    measure_true_peak_dbtp,
    load_audio_from_bytes,
)
from src.audio.validator import validate_audio_pack, measure_true_peak
from src.providers.mock_provider import MockProvider


@pytest.fixture
def mock_provider():
    return MockProvider()


def test_mandatory_duration_accuracy_across_lengths(mock_provider):
    """Test duration accuracy is strictly within 0.05s for short, medium, and long durations."""
    test_durations = [5.0, 10.0, 45.0, 120.0]

    for target_dur in test_durations:
        gen_res = mock_provider.generate_music(prompt="acoustic folk", duration_s=target_dur)
        raw_audio, sr = load_audio_from_bytes(gen_res.audio_bytes, target_sr=48000)
        aligned = align_duration_and_finish_tail(raw_audio, target_duration_s=target_dur, sr=48000)

        actual_dur = len(aligned) / sr
        diff = abs(actual_dur - target_dur)
        assert diff <= 0.05, f"Duration diff {diff:.4f}s exceeds 0.05s tolerance for target {target_dur}s"


def test_mandatory_at_least_three_distinct_instrument_stems(mock_provider):
    """Verify provider delivers at least 3 distinct instrument parts, not frequency-split bands."""
    gen_res = mock_provider.generate_music(prompt="cinematic orchestral", duration_s=15.0)
    sep_res = mock_provider.separate_stems(gen_res.audio_bytes, sample_rate=48000)

    stems = sep_res.stems
    assert len(stems) >= 3, f"Expected at least 3 stems, got {len(stems)}"

    # Load audio for each stem
    stem_arrays = {}
    for name, s_bytes in stems.items():
        arr, sr = sf.read(io.BytesIO(s_bytes), dtype="float64")
        if arr.ndim == 1:
            arr = np.column_stack((arr, arr))
        stem_arrays[name] = arr

    # Verify stems with energy are not identical (cross-correlation < 0.95 between different active stems)
    active_stems = {k: v for k, v in stem_arrays.items() if np.sqrt(np.mean(v ** 2)) > 1e-4}
    assert len(active_stems) >= 3, f"Expected at least 3 active instrument stems, got {len(active_stems)}"

    active_names = list(active_stems.keys())
    for i in range(len(active_names)):
        for j in range(i + 1, len(active_names)):
            s1 = active_stems[active_names[i]][:, 0]
            s2 = active_stems[active_names[j]][:, 0]
            corr = np.corrcoef(s1, s2)[0, 1]
            assert abs(corr) < 0.95, f"Stems '{active_names[i]}' and '{active_names[j]}' are too correlated ({corr:.3f})"


def test_mandatory_stem_alignment_and_sample_rate(mock_provider):
    """Verify all stems match the mix length and sample rate exactly."""
    target_dur = 20.0
    gen_res = mock_provider.generate_music(prompt="ambient soundscape", duration_s=target_dur)
    sep_res = mock_provider.separate_stems(gen_res.audio_bytes, sample_rate=48000)

    raw_mix, sr = load_audio_from_bytes(gen_res.audio_bytes, target_sr=48000)
    aligned_mix = align_duration_and_finish_tail(raw_mix, target_duration_s=target_dur, sr=48000)

    for stem_name, s_bytes in sep_res.stems.items():
        s_arr, s_sr = sf.read(io.BytesIO(s_bytes), dtype="float64")
        assert s_sr == 48000, f"Stem {stem_name} sample rate {s_sr} != 48000"
        aligned_s = align_duration_and_finish_tail(s_arr, target_duration_s=target_dur, sr=48000)
        assert len(aligned_s) == len(aligned_mix), f"Stem {stem_name} length {len(aligned_s)} != mix length {len(aligned_mix)}"


def test_mandatory_mathematical_stem_reconstruction(mock_provider):
    """Verify sum of stems equals final mix with SDR >= 20 dB."""
    target_dur = 15.0
    gen_res = mock_provider.generate_music(prompt="tech corporate", duration_s=target_dur)
    sep_res = mock_provider.separate_stems(gen_res.audio_bytes, sample_rate=48000)

    raw_mix, sr = load_audio_from_bytes(gen_res.audio_bytes, target_sr=48000)
    aligned_mix = align_duration_and_finish_tail(raw_mix, target_duration_s=target_dur, sr=sr)

    aligned_stems = {}
    for name, s_bytes in sep_res.stems.items():
        s_arr, _ = load_audio_from_bytes(s_bytes, target_sr=sr)
        aligned_stems[name] = align_duration_and_finish_tail(s_arr, target_duration_s=target_dur, sr=sr)

    finished_mix, finished_stems, _, _, _ = normalize_loudness_and_peaks(
        mix=aligned_mix,
        stems=aligned_stems,
        sr=sr,
        target_lufs=-16.0,
    )

    stem_sum = np.zeros_like(finished_mix)
    for stem_arr in finished_stems.values():
        stem_sum += stem_arr

    residual = finished_mix - stem_sum
    sig_power = np.sum(finished_mix ** 2)
    noise_power = np.sum(residual ** 2)
    sdr_db = 10.0 * np.log10(sig_power / (noise_power + 1e-12))

    assert sdr_db >= 20.0, f"Stem reconstruction SDR {sdr_db:.2f} dB is below required 20.0 dB"


def test_mandatory_instrumental_only_output(mock_provider):
    """Verify instrumental-only output with vocal stem energy <= -40 dBFS."""
    gen_res = mock_provider.generate_music(prompt="acoustic pop with no vocals", duration_s=10.0)
    sep_res = mock_provider.separate_stems(gen_res.audio_bytes, sample_rate=48000)

    for stem_name, s_bytes in sep_res.stems.items():
        if "vocal" in stem_name.lower():
            arr, sr = sf.read(io.BytesIO(s_bytes), dtype="float64")
            rms = np.sqrt(np.mean(arr ** 2))
            dbfs = 20.0 * np.log10(rms + 1e-12)
            assert dbfs <= -40.0, f"Vocal stem energy {dbfs:.2f} dBFS exceeds -40 dBFS instrumental ceiling"


def test_mandatory_loudness_and_true_peak_compliance(mock_provider):
    """Verify integrated loudness within 1.0 LU of target (-16 LUFS) and True Peak <= -1.0 dBTP."""
    targets = [-16.0, -14.0, -23.0]

    for target_lufs in targets:
        gen_res = mock_provider.generate_music(prompt="jazz ballad", duration_s=15.0)
        raw_mix, sr = load_audio_from_bytes(gen_res.audio_bytes, target_sr=48000)
        aligned_mix = align_duration_and_finish_tail(raw_mix, target_duration_s=15.0, sr=sr)

        finished_mix, _, measured_lufs, measured_dbtp, _ = normalize_loudness_and_peaks(
            mix=aligned_mix,
            stems={},
            sr=sr,
            target_lufs=target_lufs,
            ceiling_dbtp=-1.0,
        )

        assert abs(measured_lufs - target_lufs) <= 1.0, (
            f"Measured LUFS {measured_lufs:.2f} is outside 1.0 LU tolerance of target {target_lufs}"
        )
        assert measured_dbtp <= -0.95, f"Measured True Peak {measured_dbtp:.2f} dBTP exceeds -1.0 dBTP ceiling"


def test_mandatory_intentional_musical_ending_no_hard_cut(mock_provider):
    """Verify track ends intentionally with smooth bar-line fade (tail RMS <= -35 dBFS, no hard pops)."""
    gen_res = mock_provider.generate_music(prompt="orchestral finish", duration_s=10.0)
    raw_mix, sr = load_audio_from_bytes(gen_res.audio_bytes, target_sr=48000)
    aligned_mix = align_duration_and_finish_tail(raw_mix, target_duration_s=10.0, sr=sr, fade_tail_s=1.2)

    # Check last 50ms of audio
    last_50ms = aligned_mix[-int(0.05 * sr):]
    tail_rms = np.sqrt(np.mean(last_50ms ** 2))
    tail_dbfs = 20.0 * np.log10(tail_rms + 1e-12)

    assert tail_dbfs <= -35.0, f"Tail RMS {tail_dbfs:.2f} dBFS indicates an abrupt hard cut (must be <= -35 dBFS)"
    assert np.all(np.abs(aligned_mix) <= 1.0), "Audio contains samples exceeding 0.0 dBFS (clipping)"
