"""Benchmark measurement script for IncuBrix AI Background Music Engine.
Measures:
1. Cold process start + 60s generation time
2. Warm API 60s generation time
3. Actual cost per minute
4. Maximum duration error
5. Integrated LUFS and True Peak
6. Stem reconstruction SDR and residual RMS
7. Stem leakage / correlation estimates
8. Concurrent job behavior (5 parallel submissions)
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import httpx
import numpy as np
import soundfile as sf
import pyloudnorm as pyln

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

API_BASE = "http://localhost:8000"


def measure_cold_generation():
    """Measure cold start by launching a standalone python CLI process for 60s generation."""
    out_dir = os.path.join(PROJECT_ROOT, "artifacts", "benchmark_cold")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    cmd = [
        sys.executable,
        "-m", "src.cli",
        "--prompt", "cold start benchmark instrumental",
        "--duration", "60.0",
        "--output-dir", out_dir,
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    cold_time = time.time() - t0
    success = proc.returncode == 0
    return cold_time, success, out_dir


def measure_warm_generation():
    """Measure warm generation via running API server."""
    t0 = time.time()
    headers = {"Idempotency-Key": f"bench-warm-60s-{int(time.time()*1000)}"}
    payload = {"prompt": "warm API benchmark instrumental", "duration_s": 60.0}
    r = httpx.post(f"{API_BASE}/api/v1/music/jobs", json=payload, headers=headers, timeout=10.0)
    job_id = r.json()["job_id"]
    while True:
        st = httpx.get(f"{API_BASE}/api/v1/jobs/{job_id}", timeout=10.0).json()
        if st["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.5)
    total_time = time.time() - t0
    worker_elapsed = st.get("elapsed_s", 0.0)
    cost = st.get("cost_usd", 0.0)
    return total_time, worker_elapsed, cost, st


def measure_audio_metrics(mix_wav_path, stems_dir):
    """Measure actual duration, loudness, True Peak, SDR, and stem correlation."""
    data, sr = sf.read(mix_wav_path)
    actual_dur = len(data) / sr

    # Loudness
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data)

    # True Peak (4x oversampled)
    from scipy.signal import resample_poly
    data_oversampled = resample_poly(data, up=4, down=1, axis=0)
    tp_linear = np.max(np.abs(data_oversampled))
    tp_dbtp = 20.0 * np.log10(tp_linear) if tp_linear > 0 else -120.0

    # Stems reconstruction
    stem_files = [f for f in os.listdir(stems_dir) if f.endswith(".wav")]
    stem_signals = []
    for sf_name in stem_files:
        s_data, _ = sf.read(os.path.join(stems_dir, sf_name))
        stem_signals.append(s_data)

    recon = sum(stem_signals)
    residual = data - recon
    sig_pow = np.mean(data ** 2)
    res_pow = np.mean(residual ** 2)
    sdr = 10.0 * np.log10(sig_pow / res_pow) if res_pow > 0 else 120.0

    # Cross-correlation leakage across active stems
    active_stems = [s[:, 0] if s.ndim > 1 else s for s in stem_signals if np.sqrt(np.mean(s ** 2)) > 1e-4]
    max_corr = 0.0
    if len(active_stems) >= 2:
        corr_matrix = np.corrcoef(active_stems)
        # Off-diagonal elements
        for i in range(len(active_stems)):
            for j in range(i + 1, len(active_stems)):
                max_corr = max(max_corr, abs(corr_matrix[i, j]))

    return {
        "actual_duration_s": actual_dur,
        "sample_rate": sr,
        "integrated_lufs": round(float(lufs), 2),
        "true_peak_dbtp": round(float(tp_dbtp), 2),
        "reconstruction_sdr_db": round(float(sdr), 2),
        "max_stem_correlation_leakage": round(float(max_corr), 3),
    }


def measure_concurrent_behavior(count=5):
    """Submit multiple concurrent requests and verify system stability."""
    def submit_and_wait(idx):
        t_sub = time.time()
        headers = {"Idempotency-Key": f"bench-conc-{idx}-{int(time.time()*1000)}"}
        payload = {"prompt": f"concurrent test track {idx}", "duration_s": 15.0}
        r = httpx.post(f"{API_BASE}/api/v1/music/jobs", json=payload, headers=headers, timeout=10.0)
        jid = r.json()["job_id"]
        while True:
            st = httpx.get(f"{API_BASE}/api/v1/jobs/{jid}", timeout=10.0).json()
            if st["status"] in ("succeeded", "failed"):
                break
            time.sleep(0.5)
        return st["status"], time.time() - t_sub

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(submit_and_wait, i) for i in range(count)]
        results = [f.result() for f in futures]

    statuses = [r[0] for r in results]
    times = [r[1] for r in results]
    success_rate = statuses.count("succeeded") / len(statuses)
    avg_time = sum(times) / len(times)
    return success_rate, avg_time, statuses


def main():
    print("=== IncuBrix Audio Engine Benchmark Protocol ===")

    print("\n1. Measuring Cold 60s Generation (standalone process)...")
    cold_time, cold_ok, cold_dir = measure_cold_generation()
    print(f"   Cold Start Total Elapsed: {cold_time:.2f}s (Success: {cold_ok})")

    print("\n2. Measuring Warm 60s Generation (API server)...")
    warm_total, warm_worker, warm_cost, warm_status = measure_warm_generation()
    print(f"   Warm Total Roundtrip: {warm_total:.2f}s (Worker Pipeline: {warm_worker:.2f}s, Cost: ${warm_cost:.4f})")

    print("\n3. Measuring Audio Quality & DSP Metrics on 60s Track...")
    cold_mix = os.path.join(cold_dir, "mix.wav")
    cold_stems = os.path.join(cold_dir, "stems")
    metrics = measure_audio_metrics(cold_mix, cold_stems)
    duration_err = abs(metrics["actual_duration_s"] - 60.0)
    print(f"   Actual Duration: {metrics['actual_duration_s']:.4f}s (Error: {duration_err:.4f}s)")
    print(f"   Integrated Loudness: {metrics['integrated_lufs']} LUFS")
    print(f"   True Peak: {metrics['true_peak_dbtp']} dBTP")
    print(f"   Stem Reconstruction SDR: {metrics['reconstruction_sdr_db']} dB")
    print(f"   Max Stem Inter-Correlation (Leakage): {metrics['max_stem_correlation_leakage']}")

    print("\n4. Measuring Concurrency Behavior (5 parallel jobs)...")
    conc_rate, conc_avg, conc_statuses = measure_concurrent_behavior(5)
    print(f"   Concurrency Success Rate: {conc_rate * 100:.1f}% ({conc_statuses.count('succeeded')}/{len(conc_statuses)})")
    print(f"   Average Turnaround Time: {conc_avg:.2f}s")

    benchmark_summary = {
        "cold_60s_time_s": round(cold_time, 2),
        "warm_60s_time_s": round(warm_total, 2),
        "warm_60s_worker_s": round(warm_worker, 2),
        "actual_cost_per_minute_usd": warm_cost,
        "max_duration_error_s": round(duration_err, 4),
        "integrated_lufs": metrics["integrated_lufs"],
        "true_peak_dbtp": metrics["true_peak_dbtp"],
        "stem_reconstruction_sdr_db": metrics["reconstruction_sdr_db"],
        "max_stem_correlation_leakage": metrics["max_stem_correlation_leakage"],
        "concurrency_5_success_rate": conc_rate,
        "concurrency_5_avg_time_s": round(conc_avg, 2),
    }

    out_json = os.path.join(PROJECT_ROOT, "artifacts", "benchmark_metrics.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)
    print(f"\nSaved benchmark metrics to {out_json}")


if __name__ == "__main__":
    main()
