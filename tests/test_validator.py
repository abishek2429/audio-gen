"""Unit tests for the audio validation harness (SDR, duration, LUFS, True Peak)."""
import os
import json
import numpy as np
import soundfile as sf
import pytest

from src.audio.validator import validate_audio_pack


def test_validator_passes_on_valid_pack(tmp_path):
    """Verify that a compliant audio pack passes all validation gates."""
    pack_dir = str(tmp_path / "valid_job")
    stems_dir = os.path.join(pack_dir, "stems")
    os.makedirs(stems_dir, exist_ok=True)

    sr = 48000
    duration_s = 10.0
    n_samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)

    # Fade tail for intentional ending
    fade_len = int(1.0 * sr)
    fade = np.ones(n_samples)
    fade[-fade_len:] = np.cos(np.linspace(0, np.pi / 2, fade_len)) ** 2

    # 3 distinct stems
    s1 = np.column_stack((0.1 * np.sin(2 * np.pi * 100 * t) * fade, 0.1 * np.sin(2 * np.pi * 100 * t) * fade))
    s2 = np.column_stack((0.1 * np.sin(2 * np.pi * 300 * t) * fade, 0.1 * np.sin(2 * np.pi * 300 * t) * fade))
    s3 = np.column_stack((0.1 * np.sin(2 * np.pi * 800 * t) * fade, 0.1 * np.sin(2 * np.pi * 800 * t) * fade))
    mix = s1 + s2 + s3

    sf.write(os.path.join(pack_dir, "mix.wav"), mix, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "drums.wav"), s1, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "bass.wav"), s2, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "harmony.wav"), s3, sr, format="WAV", subtype="PCM_24")

    manifest = {
        "job_id": "valid_job",
        "requested_duration_s": 10.0,
        "stem_gains": {"drums": 1.0, "bass": 1.0, "harmony": 1.0},
    }
    with open(os.path.join(pack_dir, "music_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    report = validate_audio_pack(pack_dir, requested_duration_s=10.0, target_lufs=-16.0)

    assert report.gates["files_exist"].passed is True
    assert report.gates["sample_rate_and_format"].passed is True
    assert report.gates["exact_duration"].passed is True
    assert report.gates["intentional_ending"].passed is True
    assert report.gates["stem_count"].passed is True
    assert report.gates["stem_reconstruction"].passed is True
    assert report.gates["stem_reconstruction"].details["sdr_db"] > 60.0


def test_validator_fails_on_abrupt_hard_cut(tmp_path):
    """Verify that an audio pack with a hard cut at the final sample fails the intentional ending gate."""
    pack_dir = str(tmp_path / "hardcut_job")
    stems_dir = os.path.join(pack_dir, "stems")
    os.makedirs(stems_dir, exist_ok=True)

    sr = 48000
    duration_s = 5.0
    n_samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)

    # Full volume tone right to the end (no fade/decay)
    mix = np.column_stack((0.8 * np.sin(2 * np.pi * 440 * t), 0.8 * np.sin(2 * np.pi * 440 * t)))

    sf.write(os.path.join(pack_dir, "mix.wav"), mix, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "stem1.wav"), mix * 0.5, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "stem2.wav"), mix * 0.3, sr, format="WAV", subtype="PCM_24")
    sf.write(os.path.join(stems_dir, "stem3.wav"), mix * 0.2, sr, format="WAV", subtype="PCM_24")

    manifest = {"job_id": "hardcut_job", "requested_duration_s": 5.0}
    with open(os.path.join(pack_dir, "music_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    report = validate_audio_pack(pack_dir, requested_duration_s=5.0)
    assert report.gates["intentional_ending"].passed is False
    assert report.gates["intentional_ending"].details["has_hard_cut"] is True
    assert report.overall_passed is False
