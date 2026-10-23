"""Unit tests for DSP audio finishing pipeline (resampling, duration, LUFS, True Peak, ducking)."""
import numpy as np
import pytest
import pyloudnorm as pyln

from src.audio.dsp import (
    resample_audio,
    align_duration_and_finish_tail,
    measure_true_peak_dbtp,
    normalize_loudness_and_peaks,
    apply_voiceover_ducking,
)


def test_resample_audio():
    """Verify polyphase resampling changes sample rate while preserving channel structure."""
    sr_orig = 44100
    sr_target = 48000
    duration_s = 1.0

    t = np.linspace(0, duration_s, int(sr_orig * duration_s), endpoint=False)
    sig_l = np.sin(2 * np.pi * 440.0 * t)
    sig_r = np.sin(2 * np.pi * 880.0 * t)
    stereo = np.column_stack((sig_l, sig_r))

    resampled = resample_audio(stereo, orig_sr=sr_orig, target_sr=sr_target)
    assert resampled.shape[1] == 2
    assert len(resampled) == int(sr_target * duration_s)


def test_align_duration_and_finish_tail():
    """Verify that audio is aligned to target duration within 0.05s and ends with smooth decay."""
    sr = 48000
    target_dur_s = 7.50
    # Create 10-second continuous tone
    t = np.linspace(0, 10.0, int(sr * 10.0), endpoint=False)
    audio = np.column_stack((np.sin(2 * np.pi * 440 * t), np.sin(2 * np.pi * 440 * t)))

    aligned = align_duration_and_finish_tail(audio, target_duration_s=target_dur_s, sr=sr, fade_tail_s=1.0)

    # Check exact length
    actual_dur = len(aligned) / sr
    assert abs(actual_dur - target_dur_s) <= 0.001

    # Check intentional ending: last 50ms must be <= -35 dBFS
    last_50ms = int(0.05 * sr)
    tail_rms = np.sqrt(np.mean(aligned[-last_50ms:] ** 2))
    tail_dbfs = 20 * np.log10(tail_rms + 1e-12)
    assert tail_dbfs <= -35.0
    # Final sample must be near zero
    assert np.allclose(aligned[-1], [0.0, 0.0], atol=1e-4)


def test_normalize_loudness_and_peaks():
    """Verify that normalize_loudness_and_peaks hits -16 LUFS and True Peak <= -1.0 dBTP."""
    sr = 48000
    dur_s = 5.0
    t = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False)

    # Stem 1: Low-frequency chord
    s1 = np.column_stack((0.3 * np.sin(2 * np.pi * 220 * t), 0.3 * np.sin(2 * np.pi * 220 * t)))
    # Stem 2: High-frequency motif
    s2 = np.column_stack((0.3 * np.sin(2 * np.pi * 660 * t), 0.3 * np.sin(2 * np.pi * 660 * t)))
    mix = s1 + s2
    stems = {"stem1": s1, "stem2": s2}

    finished_mix, finished_stems, lufs, dbtp, gain = normalize_loudness_and_peaks(
        mix=mix,
        stems=stems,
        sr=sr,
        target_lufs=-16.0,
        ceiling_dbtp=-1.0,
    )

    meter = pyln.Meter(sr)
    measured_lufs = meter.integrated_loudness(finished_mix)
    measured_dbtp = measure_true_peak_dbtp(finished_mix)

    assert abs(measured_lufs - (-16.0)) <= 1.0
    assert measured_dbtp <= -0.95

    # Check that stem sum still equals finished mix exactly
    recon = finished_stems["stem1"] + finished_stems["stem2"]
    np.testing.assert_allclose(finished_mix, recon, atol=1e-10)


def test_apply_voiceover_ducking():
    """Verify that speech detection ducks music by expected attenuation."""
    sr = 48000
    dur_s = 4.0
    n_samples = int(sr * dur_s)
    music = np.ones((n_samples, 2), dtype=np.float64) * 0.5

    # Speech active only in middle (1.0s to 3.0s)
    speech = np.zeros((n_samples, 2), dtype=np.float64)
    mid_start = int(1.0 * sr)
    mid_end = int(3.0 * sr)
    speech[mid_start:mid_end] = 0.5

    ducked_music, gain_curve = apply_voiceover_ducking(
        music=music,
        speech=speech,
        sr=sr,
        ducking_db=10.0,
    )

    # During speech, gain should drop to ~10dB down (~0.316)
    mid_sample = int(2.0 * sr)
    attenuation_db = -20 * np.log10(gain_curve[mid_sample])
    assert 8.0 <= attenuation_db <= 12.0

    # During silence (0.2s), gain should be ~1.0 (0 dB)
    early_sample = int(0.2 * sr)
    assert gain_curve[early_sample] > 0.95
