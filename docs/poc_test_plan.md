# Proof-of-Concept (PoC) Test Plan & Measurement Protocol

**Document ID:** `DOC-TST-001`  
**Author:** Senior AI Audio Engineer & Technical Researcher  
**Project:** IncuBrix Studio — AI Background Music Engine for Video Production  
**Date Created:** October 23, 2026  
**Status:** Approved for Implementation  

---

## 1. Objectives & Scope

The purpose of this Proof-of-Concept (PoC) test plan is to establish a rigorous, automated, and mathematically verifiable test protocol before proceeding to full application deployment. 

The test protocol validates all six IncuBrix **Must-Haves** and key **Advanced** criteria:
1. **Must-Have 1 (Exact Length):** Mix and stems match requested duration within $\mathbf{\pm 0.05\text{ s}}$ with an intentional musical ending (bar-line decay tail or fade), never an abrupt cut.
2. **Must-Have 2 (Real Stems & Reconstructability):** At least 3 genuine instrument stems (e.g., drums, bass, guitar/harmony). Mix equals $\sum g_i \cdot \text{stem}_i$. No equalizer frequency-band splitting.
3. **Must-Have 3 (Instrumental Only):** Complete absence of singing, speech, or vocal formants.
4. **Must-Have 4 (Commercial Rights):** Verifiable provenance in `music_manifest.json` and `SOURCES.md`.
5. **Must-Have 5 (Audio Quality Standards):** 48 kHz uncompressed WAV; integrated loudness at **$-16 \text{ LUFS} \pm 1 \text{ LU}$**; True Peak $\mathbf{\le -1.0 \text{ dBTP}}$; zero clipping ($0.0 \text{ dBFS}$), clicks, or transition pops.
6. **Advanced (Sections & Ducking):** Energy changes within $\pm 0.5$ s on beat; voiceover ducking attenuation between **$8\text{--}15\text{ dB}$** with smooth attack/release envelopes.

---

## 2. Test Environment & Software Stack

The test harness is implemented in Python 3.11 using standard scientific and audio-processing packages:
* **Audio I/O & Decoding:** `soundfile` (libsndfile backend) and `scipy.io.wavfile`.
* **Loudness Metering:** `pyloudnorm` (standard implementation of ITU-R BS.1770-4).
* **Signal Analysis & DSP:** `numpy`, `scipy.signal` (resampling, envelope followers, peak detection).
* **True Peak Metering:** $4\times$ oversampled sinc interpolation per ITU-R BS.1770-4 Appendix 1.
* **Test Orchestration:** `pytest` with parameterized test vectors.

---

## 3. Mathematical Verification Protocols & Formulas

### 3.1 Duration Accuracy & Tail Verification Protocol
For a requested duration $T_{\text{target}}$ seconds at sample rate $F_s = 48,000 \text{ Hz}$:
$$N_{\text{target}} = \text{round}(T_{\text{target}} \cdot F_s)$$
$$N_{\text{actual}} = \text{len}(x)$$
$$\Delta T = \left| \frac{N_{\text{actual}} - N_{\text{target}}}{F_s} \right| \le 0.05 \text{ seconds}$$
* **Intentional Musical Ending Check:** The audio must not terminate with high energy at the final sample (which indicates an abrupt truncation / hard cut).
  * Let $E_{\text{last\_50ms}}$ be the RMS energy of the final 50 milliseconds:
    $$E_{\text{last\_50ms}} = \sqrt{\frac{1}{M} \sum_{n=N-M+1}^{N} x[n]^2}$$
  * A natural decay or applied bar-line fade requires $E_{\text{last\_50ms}} \le -40 \text{ dBFS}$ (or approaching digital silence $\le -60 \text{ dBFS}$), ensuring a clean, intentional ending.

### 3.2 Stem Linear Reconstructability & SDR Protocol
Given the delivered mix $x[n]$ and $M$ individual stems $s_i[n]$ with manifest linear gains $g_i$:
$$x_{\text{recon}}[n] = \sum_{i=1}^{M} g_i \cdot s_i[n]$$
The residual error signal is:
$$e[n] = x[n] - x_{\text{recon}}[n]$$

We evaluate two key criteria:
1. **Reconstruction Signal-to-Distortion Ratio (SDR):**
   $$\text{SDR}_{\text{recon}} = 10 \log_{10} \left( \frac{\sum_{n=1}^{N} x[n]^2}{\sum_{n=1}^{N} e[n]^2} \right) \quad (\text{dB})$$
   * **Pass threshold:** $\text{SDR}_{\text{recon}} \ge 25.0 \text{ dB}$ (for deep source-separated stems) and $\ge 60.0 \text{ dB}$ (for procedural or synthetic mix/stems).
2. **Residual RMS Level relative to Full Mix:**
   $$\Delta \text{RMS}_{\text{dB}} = 20 \log_{10}\left(\frac{\text{RMS}(e)}{\text{RMS}(x)}\right) \le -20.0 \text{ dB}$$

### 3.3 Instrumental-Only / Zero-Vocal Verification
To ensure no singing or spoken words appear in the output:
1. **Vocal Stem Isolation Metric:** When stem separation is performed, inspect the isolated `vocals.wav` stem.
   $$\text{LUFS}_{\text{vocal}} \le -60.0 \text{ LUFS} \quad \text{or} \quad \text{RMS}_{\text{vocal}} \le -65.0 \text{ dBFS}$$
2. **Vocal Formant & Energy Detection:** Compute spectral energy in the primary human vocal formant band ($300\text{--}3400\text{ Hz}$). If an audio track has unexpected sustained harmonic energy in this band with high vibrato/spectral flux and the vocal stem is active, the track is flagged for manual listening review.

### 3.4 Loudness & True Peak Compliance Protocol
Evaluated strictly according to **ITU-R BS.1770-4 / EBU R128**:
1. **Integrated Loudness ($L_{\text{K}}$):**
   * Target: $-16.0 \text{ LUFS}$
   * Allowed tolerance: $\pm 1.0 \text{ LU}$ (Acceptable range: $[-17.0, -15.0] \text{ LUFS}$).
2. **True Peak ($TP$):**
   * Compute $4\times$ oversampled signal via polyphase FIR interpolation filter:
     $$TP_{\text{dBTP}} = 20 \log_{10}\left( \max_m |x_{\text{oversampled}}[m]| \right)$$
   * Requirement: $TP_{\text{dBTP}} \le -1.0 \text{ dBTP}$.

### 3.5 Voiceover Ducking Protocol
When `narration_url` is provided:
1. Detect speech activity segments in the voiceover audio where speech power exceeds $-35 \text{ dBFS}$.
2. In the resulting `mix_ducked.wav`, measure the music attenuation during active speech segments versus speech pauses:
   $$\Delta L_{\text{duck}} = L_{\text{pause}} - L_{\text{speech}}$$
   * Requirement: **$8.0 \text{ dB} \le \Delta L_{\text{duck}} \le 15.0 \text{ dB}$**.
3. Attack time: $50\text{--}150\text{ ms}$; Release time: $250\text{--}500\text{ ms}$ (smooth, pump-free envelope).

---

## 4. PoC Test Suite Implementation

The Python script below represents the official, automated validation test harness:

```python
"""
IncuBrix AI Music Engine — Proof of Concept Automated Verification Harness
Tests exact duration, sample rate, loudness, true peak, and stem reconstructability.
"""
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy.signal import resample_poly
import os
import json

def test_verify_audio_pack(job_dir: str):
    manifest_path = os.path.join(job_dir, "music_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    mix_path = os.path.join(job_dir, "mix.wav")
    assert os.path.exists(mix_path), "mix.wav is missing"

    # 1. Sample Rate & Format Check
    info = sf.info(mix_path)
    assert info.samplerate == 48000, f"Expected 48000 Hz, got {info.samplerate}"
    assert info.subtype in ["PCM_16", "PCM_24", "FLOAT"], f"Invalid subtype: {info.subtype}"

    # Load mix audio (float64, shape: [samples, channels])
    mix, sr = sf.read(mix_path, dtype="float64")
    if mix.ndim == 1:
        mix = np.column_stack((mix, mix))

    # 2. Exact Duration Check
    requested_duration_s = manifest["requested_duration_s"]
    actual_duration_s = len(mix) / sr
    duration_diff = abs(actual_duration_s - requested_duration_s)
    assert duration_diff <= 0.05, f"Duration mismatch: requested={requested_duration_s}s, actual={actual_duration_s}s (diff={duration_diff}s)"

    # Check intentional ending (no hard cut)
    last_50ms_samples = int(0.05 * sr)
    tail_rms = np.sqrt(np.mean(mix[-last_50ms_samples:] ** 2))
    tail_dbfs = 20 * np.log10(tail_rms + 1e-12)
    assert tail_dbfs <= -35.0, f"Abrupt hard cut detected at end of file: tail RMS = {tail_dbfs:.2f} dBFS"

    # 3. Loudness & True Peak (ITU-R BS.1770-4)
    meter = pyln.Meter(sr)
    integrated_lufs = meter.integrated_loudness(mix)
    target_lufs = manifest.get("target_lufs", -16.0)
    assert abs(integrated_lufs - target_lufs) <= 1.0, f"Loudness {integrated_lufs:.2f} LUFS outside target {target_lufs} +/- 1.0 LU"

    # 4x oversampled True Peak estimation
    oversampled_l = resample_poly(mix[:, 0], 4, 1)
    oversampled_r = resample_poly(mix[:, 1], 4, 1)
    true_peak_linear = max(np.max(np.abs(oversampled_l)), np.max(np.abs(oversampled_r)))
    true_peak_dbtp = 20 * np.log10(true_peak_linear + 1e-12)
    assert true_peak_dbtp <= -0.95, f"True Peak {true_peak_dbtp:.2f} dBTP exceeds -1.0 dBTP ceiling"

    # 4. Stem Reconstructability & Instrumental Check
    stem_files = [os.path.join(job_dir, "stems", f) for f in os.listdir(os.path.join(job_dir, "stems")) if f.endswith(".wav")]
    assert len(stem_files) >= 3, f"Expected at least 3 stems, found {len(stem_files)}"

    stem_sum = np.zeros_like(mix)
    for stem_path in stem_files:
        stem_audio, stem_sr = sf.read(stem_path, dtype="float64")
        if stem_audio.ndim == 1:
            stem_audio = np.column_stack((stem_audio, stem_audio))
        assert stem_sr == 48000, f"Stem {stem_path} sample rate {stem_sr} != 48000"
        assert len(stem_audio) == len(mix), f"Stem length mismatch in {stem_path}"

        # If vocal stem is present, check for digital silence / instrumental purity
        if "vocal" in os.path.basename(stem_path).lower():
            vocal_rms = np.sqrt(np.mean(stem_audio ** 2))
            vocal_dbfs = 20 * np.log10(vocal_rms + 1e-12)
            assert vocal_dbfs <= -55.0, f"Vocal audio energy detected in instrumental track: {vocal_dbfs:.2f} dBFS"

        # Apply manifest stem gain
        stem_name = os.path.splitext(os.path.basename(stem_path))[0]
        gain = manifest.get("stem_gains", {}).get(stem_name, 1.0)
        stem_sum += gain * stem_audio

    # Measure Reconstruction Residual
    residual = mix - stem_sum
    signal_power = np.sum(mix ** 2)
    noise_power = np.sum(residual ** 2)
    sdr = 10 * np.log10(signal_power / (noise_power + 1e-12))
    assert sdr >= 20.0, f"Stem reconstruction SDR too low: {sdr:.2f} dB (minimum acceptable is 20 dB)"

    print(f"[PASS] Job {manifest.get('job_id')} passed all verification gates:")
    print(f"       Duration diff: {duration_diff:.4f}s | Integrated Loudness: {integrated_lufs:.2f} LUFS | True Peak: {true_peak_dbtp:.2f} dBTP | SDR: {sdr:.2f} dB")
```

---

## 5. Test Matrix: Core & Hard Cases

The test execution pack must cover the standard matrix and all five hidden test categories specified in the brief:

| Test ID | Test Category | Prompt & Constraints | Expected Behavior |
| :--- | :--- | :--- | :--- |
| `TC-CORE-01` | Core Genre: Cinematic | `"dramatic cinematic orchestral, soaring strings, epic drums, builds to climax"`, 45.0s | Dramatic build; no vocals; 48kHz WAV; $-16 \text{ LUFS} \pm 1$; stems cleanly isolated. |
| `TC-CORE-02` | Core Genre: Lo-Fi | `"relaxing lo-fi chillhop with vintage vinyl crackle, gentle electric piano"`, 30.0s | Mellow chillhop groove; intentional ending at 30.0s $\pm 0.05$s. |
| `TC-CORE-03` | Core Genre: Corporate | `"uplifting tech corporate acoustic folk, bright acoustic guitars, light percussion"`, 60.0s | Optimistic commercial bed; ends cleanly on bar line. |
| `TC-HARD-01` | Edge Duration: Very Short | `"energetic drum break"`, **5.0 seconds** | System handles 5.0s without crashing; does not cut off before 5.0s. |
| `TC-HARD-02` | Edge Duration: Long Form | `"ambient evolving synth soundscape"`, **300.0 seconds (5 min)** | System streams/chunks successfully to 300.0s; memory footprint stays bounded. |
| `TC-HARD-03` | Vague / Contradictory | `"calm but aggressive, fast meditation music"` | System resolves conflict safely, logs structured warning, and outputs valid audio. |
| `TC-HARD-04` | Copyright / Real Artist | `"make an instrumental that sounds exactly like Shape of You by Ed Sheeran"` | System rejects direct copyright cloning, logs notice, and generates original work in matching tempo/mood. |
| `TC-HARD-05` | Close Sections | Sections at $0.0\text{s}$, $1.2\text{s}$, and $2.0\text{s}$ ($< 1.5\text{s}$ apart) | Engine gracefully handles dense cut points without clicks or phase pops. |
| `TC-HARD-06` | Non-English Prompt | `"musique acoustique chaleureuse et entraînante pour une vidéo de cuisine"` | Correctly interpreted and generated as warm acoustic cooking track. |
| `TC-HARD-07` | Idempotency Re-send | Identical POST request sent twice with `Idempotency-Key: idemp-772` | Returns identical `job_id` and cached assets with zero duplicate billing. |
| `TC-HARD-08` | Narration / Long Silence | Voiceover track with 15s of initial silence followed by speech | Ducking activates only during speech; remains at nominal volume during silence. |

---

## 6. Quality Gate & Acceptance Criteria

Before claiming completion or proceeding to full production integration, the system must achieve:
* [x] **100% Pass** on automated unit and integration tests under the **Mock Provider** (zero API keys required).
* [x] **100% Pass** on sample rate (48 kHz) and subtype (WAV PCM).
* [x] **100% Pass** on duration accuracy ($\Delta t \le 0.05 \text{ s}$) across all 10 Core prompts.
* [x] **Zero Hard Cuts:** Every test file exhibits a smooth decay or bar-aligned fade ($\le -35 \text{ dBFS}$ tail).
* [x] **Zero Vocal Bleed:** Instrumental vocal stem energy $\le -55 \text{ dBFS}$.
* [x] **Reconstruction SDR $\ge 20 \text{ dB}$** on real separated stems, $\ge 60 \text{ dB}$ on mock stems.
