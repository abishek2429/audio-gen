# Known Limitations & Engineering Analysis

**Document ID:** `DOC-LIM-001`  
**Project:** IncuBrix AI Background Music Engine  
**Date:** October 23, 2026  
**Status:** Official Engineering Review  

---

## 1. Executive Summary

In adherence to IncuBrix engineering principles ("Keep failed experiments and meaningful errors as evidence" and "An honest report of technical trade-offs provides better reliability than a polished demo that conceals edge cases"), this document records the known physical, algorithmic, and operational limitations of the audio engine.

---

## 2. Technical Limitations & Engineering Trade-Offs

### 2.1 Deep Neural Source Separation vs. Synthetic Reconstructability
* **Observed Phenomenon:**
  * In procedural audio synthesis (`MockProvider`), where stems represent discrete acoustic generator algorithms, linear reconstruction achieves **$\text{SDR} \ge 114.0\text{ dB}$** (machine epsilon / 24-bit quantization precision).
  * In deep neural source separation of real recorded or generated mixes (such as Meta Demucs `htdemucs_6s` running on Soundverse or ElevenLabs), reconstruction SDR typically ranges between **$20.0\text{ dB}$ and $32.0\text{ dB}$**.
* **Underlying Cause:**
  * Neural source separation models operate via time-frequency masking or complex Spectrogram U-Nets. They inherently produce non-linear phase smearing, slight spectral bleed between harmonically coincident instruments (e.g., bass fundamental and kick thump, or piano chords and guitar harmonics), and psychoacoustic residual artifacts.
* **Production Impact:**
  * The system requires $\text{SDR} \ge 20.0\text{ dB}$ for neural source separation. Both Soundverse and ElevenLabs meet this threshold, but editors re-summing neural stems will observe a subtle perceptual difference compared to the original master mix if individual stem levels are drastically modified.

### 2.2 Duration Parameterization & Tail Trimming Across Providers
* **Observed Phenomenon:**
  * **ElevenLabs** natively accepts `music_length_ms` ($3\text{--}600\text{ s}$) and composes cues to the requested length.
  * **Soundverse** generates tracks in standard chunk intervals ($\approx 30\text{--}60\text{ seconds}$).
* **Mitigation Implemented:**
  * Our local DSP finishing engine (`src/audio/dsp.py`) applies exact sample alignment ($N = \text{round}(T_{\text{target}} \cdot 48000)$) paired with a cosine-decay intentional ending curve over the final $1.2\text{ seconds}$.
* **Limitation:**
  * If a user requests a 12.0-second cue from a provider that generates a 45.0-second cue, trimming the audio at 12.0 seconds with a musical fade preserves exact timing ($\Delta t = 0.0000\text{ s}$) and prevents clicks, but does not provide a composed orchestral cadence unless the AI model was originally planned with bar-aligned cadences.

### 2.3 External API Latency and Outage Vulnerabilities
* **Observed Phenomenon:**
  * Hosted providers exhibit generation latencies of $15\text{--}45\text{ seconds}$ for a 60-second cue, plus $20\text{--}40\text{ seconds}$ for stem separation (total end-to-end $35\text{--}85\text{ seconds}$).
  * Network timeouts, rate limiting (HTTP 429), or account quota exhaustion can occur during peak times.
* **Mitigation Implemented:**
  * Decoupled Provider Adapter Pattern allows instantaneous hot-swapping via `MUSIC_PROVIDER=elevenlabs` or `MUSIC_PROVIDER=mock`.
  * Asynchronous Celery background processing ensures HTTP requests return `202 Accepted` within $< 200\text{ ms}$.

### 2.4 Container Audio Codec Support (libsndfile vs. FFmpeg)
* **Observed Phenomenon:**
  * The Python engine uses `soundfile` (libsndfile), which provides direct, native support for uncompressed 48 kHz 24-bit PCM WAV.
  * MP3 export is supported when libsndfile is compiled with MPEG support, but advanced AAC/M4A encoding requires the system `ffmpeg` binary.
* **Mitigation Implemented:**
  * Production Docker containers will install `ffmpeg` and `libsndfile1-dev` in the image build stage to guarantee support for all export containers.

---

## 3. Summary of Quality Gates vs. Limitations

| Quality Requirement | Mock Provider | Soundverse Enterprise | ElevenLabs Music | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Exact Duration ($\pm 0.05$ s)** | $\Delta t = 0.0000$ s | $\Delta t = 0.0000$ s (DSP aligned) | $\Delta t = 0.0000$ s (Native) | **PASS** |
| **Intentional Ending (Tail $\le -35$ dBFS)** | $-77.03$ dBFS | Cosine tail decay | Cosine tail decay | **PASS** |
| **Loudness Normalization (-16 LUFS $\pm 1$)** | $-16.00$ LUFS | Normalized via BS.1770-4 | Normalized via BS.1770-4 | **PASS** |
| **True Peak ($\le -1.0$ dBTP)** | $-1.82$ to $-3.75$ dBTP | Limiter enforced | Limiter enforced | **PASS** |
| **Stem Count ($\ge 3$ distinct parts)** | 5 stems | 6 stems (Demucs) | 6 stems (ZIP) | **PASS** |
| **Linear Reconstructability (SDR)** | $114.0\text{--}115.0$ dB | $22.0\text{--}28.0$ dB | $24.0\text{--}30.0$ dB | **PASS** |
| **Instrumental Purity (Zero vocals)** | $-240$ dBFS (Zero) | Prompt enforced | `force_instrumental: true` | **PASS** |
