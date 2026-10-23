"""Automated audio validation harness measuring duration, loudness, True Peak,
and mathematical stem reconstructability (SDR).
"""
import os
import json
import datetime
from typing import Dict, Any, List
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy.signal import resample_poly

from src.models import ValidationReport, GateResult


def measure_true_peak(audio: np.ndarray) -> float:
    """4x oversampled True Peak (dBTP) per ITU-R BS.1770-4 Appendix 1."""
    if len(audio) == 0:
        return -120.0
    oversampled_l = resample_poly(audio[:, 0], 4, 1)
    oversampled_r = resample_poly(audio[:, 1], 4, 1)
    peak_linear = max(np.max(np.abs(oversampled_l)), np.max(np.abs(oversampled_r)))
    if peak_linear <= 1e-12:
        return -120.0
    return float(20.0 * np.log10(peak_linear))


def validate_audio_pack(
    pack_dir: str,
    requested_duration_s: float,
    target_lufs: float = -16.0,
    ceiling_dbtp: float = -1.0,
) -> ValidationReport:
    """Validate a rendered audio pack against all IncuBrix Must-Have requirements."""
    job_id = os.path.basename(pack_dir)
    manifest_path = os.path.join(pack_dir, "music_manifest.json")
    mix_path = os.path.join(pack_dir, "mix.wav")
    stems_dir = os.path.join(pack_dir, "stems")

    gates: Dict[str, GateResult] = {}
    details: List[str] = []

    # -------------------------------------------------------------
    # Gate 1: Manifest & Files Existence
    # -------------------------------------------------------------
    manifest_data = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            job_id = manifest_data.get("job_id", job_id)

    files_exist = os.path.exists(mix_path) and os.path.exists(stems_dir)
    gates["files_exist"] = GateResult(
        passed=files_exist,
        details={
            "mix_exists": os.path.exists(mix_path),
            "manifest_exists": os.path.exists(manifest_path),
            "stems_dir_exists": os.path.exists(stems_dir),
        },
    )

    if not files_exist:
        return ValidationReport(
            job_id=job_id,
            overall_passed=False,
            evaluated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            gates=gates,
            summary="Essential files (mix.wav or stems directory) are missing.",
        )

    # -------------------------------------------------------------
    # Gate 2: Format & Sample Rate (48 kHz uncompressed WAV)
    # -------------------------------------------------------------
    mix_info = sf.info(mix_path)
    sr_passed = (mix_info.samplerate == 48000) and (mix_info.format == "WAV")
    gates["sample_rate_and_format"] = GateResult(
        passed=sr_passed,
        details={
            "expected_sr": 48000,
            "actual_sr": mix_info.samplerate,
            "format": mix_info.format,
            "subtype": mix_info.subtype,
        },
    )

    # Load mix audio (float64)
    mix_audio, sr = sf.read(mix_path, dtype="float64")
    if mix_audio.ndim == 1:
        mix_audio = np.column_stack((mix_audio, mix_audio))

    # -------------------------------------------------------------
    # Gate 3: Exact Duration Accuracy (|actual - requested| <= 0.05s)
    # -------------------------------------------------------------
    actual_duration_s = len(mix_audio) / sr
    duration_diff = abs(actual_duration_s - requested_duration_s)
    dur_passed = duration_diff <= 0.05
    gates["exact_duration"] = GateResult(
        passed=dur_passed,
        details={
            "requested_duration_s": requested_duration_s,
            "actual_duration_s": round(actual_duration_s, 4),
            "difference_s": round(duration_diff, 4),
            "tolerance_s": 0.05,
        },
    )

    # -------------------------------------------------------------
    # Gate 4: Intentional Musical Ending (Tail RMS <= -35 dBFS, no hard cut)
    # -------------------------------------------------------------
    last_50ms_samples = int(0.05 * sr)
    tail_rms = float(np.sqrt(np.mean(mix_audio[-last_50ms_samples:] ** 2)))
    tail_dbfs = float(20.0 * np.log10(tail_rms + 1e-12))
    tail_passed = tail_dbfs <= -35.0
    gates["intentional_ending"] = GateResult(
        passed=tail_passed,
        details={
            "tail_50ms_rms_dbfs": round(tail_dbfs, 2),
            "threshold_dbfs": -35.0,
            "has_hard_cut": not tail_passed,
        },
    )

    # -------------------------------------------------------------
    # Gate 5: Integrated Loudness (-16 LUFS +/- 1.0 LU)
    # -------------------------------------------------------------
    meter = pyln.Meter(sr)
    try:
        actual_lufs = float(meter.integrated_loudness(mix_audio))
        lufs_diff = abs(actual_lufs - target_lufs)
        lufs_passed = lufs_diff <= 1.0
    except Exception as e:
        actual_lufs = -99.0
        lufs_diff = 99.0
        lufs_passed = False

    gates["integrated_loudness"] = GateResult(
        passed=lufs_passed,
        details={
            "target_lufs": target_lufs,
            "actual_lufs": round(actual_lufs, 2),
            "difference_lu": round(lufs_diff, 2),
            "allowed_tolerance_lu": 1.0,
        },
    )

    # -------------------------------------------------------------
    # Gate 6: True Peak (<= -1.0 dBTP)
    # -------------------------------------------------------------
    actual_dbtp = measure_true_peak(mix_audio)
    tp_passed = actual_dbtp <= (ceiling_dbtp + 0.05)  # 0.05dB numerical slack
    gates["true_peak"] = GateResult(
        passed=tp_passed,
        details={
            "ceiling_dbtp": ceiling_dbtp,
            "actual_dbtp": round(actual_dbtp, 2),
        },
    )

    # -------------------------------------------------------------
    # Gate 7 & 8: Real Stems & Linear Reconstructability (SDR >= 20.0 dB)
    # -------------------------------------------------------------
    stem_files = [
        f for f in os.listdir(stems_dir) if f.lower().endswith((".wav", ".flac", ".mp3"))
    ]
    stem_count_passed = len(stem_files) >= 3

    stem_gains = manifest_data.get("stem_gains", {})
    stem_sum = np.zeros_like(mix_audio)
    vocal_energy_dbfs = -120.0
    vocal_stem_found = False

    for stem_file in stem_files:
        stem_path = os.path.join(stems_dir, stem_file)
        stem_audio, stem_sr = sf.read(stem_path, dtype="float64")
        if stem_audio.ndim == 1:
            stem_audio = np.column_stack((stem_audio, stem_audio))

        stem_name = os.path.splitext(stem_file)[0].lower()
        if "vocal" in stem_name:
            vocal_stem_found = True
            v_rms = float(np.sqrt(np.mean(stem_audio ** 2)))
            vocal_energy_dbfs = float(20.0 * np.log10(v_rms + 1e-12))

        # Align length if minor padding difference
        if len(stem_audio) < len(mix_audio):
            stem_audio = np.pad(stem_audio, ((0, len(mix_audio) - len(stem_audio)), (0, 0)))
        elif len(stem_audio) > len(mix_audio):
            stem_audio = stem_audio[: len(mix_audio)]

        gain = stem_gains.get(stem_name, 1.0)
        stem_sum += gain * stem_audio

    # Reconstruction residual calculation
    residual = mix_audio - stem_sum
    signal_power = float(np.sum(mix_audio ** 2))
    noise_power = float(np.sum(residual ** 2))
    sdr_db = float(10.0 * np.log10(signal_power / (noise_power + 1e-12)))

    mix_rms = float(np.sqrt(np.mean(mix_audio ** 2)))
    res_rms = float(np.sqrt(np.mean(residual ** 2)))
    res_relative_rms_db = float(20.0 * np.log10((res_rms + 1e-12) / (mix_rms + 1e-12)))

    # Pass threshold: >= 20.0 dB for neural separation; >= 50.0 dB for procedural
    sdr_passed = sdr_db >= 20.0

    gates["stem_count"] = GateResult(
        passed=stem_count_passed,
        details={
            "stems_found": len(stem_files),
            "stem_names": stem_files,
            "min_required": 3,
        },
    )

    gates["stem_reconstruction"] = GateResult(
        passed=sdr_passed,
        details={
            "sdr_db": round(sdr_db, 2),
            "min_threshold_sdr_db": 20.0,
            "residual_relative_rms_db": round(res_relative_rms_db, 2),
        },
    )

    # -------------------------------------------------------------
    # Gate 9: Instrumental Purity (Vocals <= -55 dBFS if vocal stem exists)
    # -------------------------------------------------------------
    if vocal_stem_found:
        purity_passed = vocal_energy_dbfs <= -55.0
    else:
        purity_passed = True  # No vocal stem means zero vocal output

    gates["instrumental_purity"] = GateResult(
        passed=purity_passed,
        details={
            "vocal_stem_found": vocal_stem_found,
            "vocal_rms_dbfs": round(vocal_energy_dbfs, 2),
            "threshold_dbfs": -55.0,
        },
    )

    overall_passed = all(g.passed for g in gates.values())

    summary = (
        f"Validation {'PASSED' if overall_passed else 'FAILED'}: "
        f"Duration diff={duration_diff:.4f}s, Loudness={actual_lufs:.2f} LUFS, "
        f"True Peak={actual_dbtp:.2f} dBTP, SDR={sdr_db:.2f} dB, Stems={len(stem_files)}"
    )

    report = ValidationReport(
        job_id=job_id,
        overall_passed=overall_passed,
        evaluated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        gates=gates,
        summary=summary,
    )

    # Save validation_report.json into pack directory
    report_path = os.path.join(pack_dir, "validation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    return report
