# Architecture Decision Record (ADR) & System Blueprint

**Document ID:** `ADR-001`  
**Author:** Senior AI Audio Engineer & Technical Researcher  
**Project:** IncuBrix Engineering Assessment 1 — AI Background Music Engine for Video  
**Date Created:** October 23, 2026  
**Status:** Approved for Implementation  

---

## 1. Context & Business Problem

IncuBrix video creators require high-quality, commercially cleared original instrumental music dynamically aligned to their video edit points and scene lengths ($5\text{--}300$ seconds), delivered with genuine multitrack stems (drums, bass, harmony, lead) so video editors can rebalance audio or duck music under voiceover speech.

To satisfy all IncuBrix assessment criteria without architectural bloat or excessive API fees, we must make definitive engineering decisions regarding:
1. **Primary & Fallback AI Music & Stem Providers.**
2. **Decoupled Provider Architecture (Adapter Pattern with Mock Provider).**
3. **Core Backend Stack & Background Processing Engine.**
4. **DSP & Audio Engineering Pipeline (Sample rate, Duration, Loudness, Ducking).**
5. **Storage, Idempotency, and API Contract (OpenAPI 3.1 & Integration Standard).**

---

## 2. Provider Recommendations

### 2.1 Primary Architecture Recommendation: Soundverse Enterprise API
* **Music Generation Endpoint:** `POST https://apiv2.soundverse.ai/v7/generate/music` (or native `POST /v1/generations` with `generate_music`).
* **Stem Separation Endpoint:** `POST https://apiv2.soundverse.ai/v1/generate/stem-separation/six-stem` (Demucs 6-way split: drums, bass, vocals, guitar, piano, other).
* **Rationale for Primary Selection:**
  1. **Published Flat Pricing:** $\$0.11$ per track (Standard commercial tier) + $\$0.10$ flat per separation = **$\$0.21$ total per track**. This represents less than half the cost of ElevenLabs ($\approx \$0.50$), keeping evaluation costs under $\$15.00$ for the full assessment test pack.
  2. **6 Genuine Instrument Stems:** The 6-stem Demucs split guarantees genuine instrument tracks (drums, bass, guitar, piano, other) rather than frequency-equalized bands.
  3. **Direct Commercial Clearance:** The Standard license tier explicitly covers commercial video synchronization and client deliverables without recurring royalties.
  4. **Native Idempotency:** The gateway natively supports `Idempotency-Key`, aligning directly with Integration Standard Point 4.

### 2.2 Fallback Architecture Recommendation: ElevenLabs Music API
* **Music Generation Endpoint:** `POST https://api.elevenlabs.io/v1/music` (model `music_v2`).
* **Stem Separation Endpoint:** `POST https://api.elevenlabs.io/v1/music/stem-separation` (`six_stems_v1`).
* **Rationale for Fallback Selection:**
  1. **Strict Instrumental Guarantee:** Includes a native boolean parameter `force_instrumental: true` that mathematically forbids vocal synthesis.
  2. **Millisecond Length Parameter:** Accepts `music_length_ms` directly in the prompt payload ($3\text{--}600\text{ seconds}$).
  3. **Instant Hot-Swappability:** Enabled simply by switching an environment variable (`MUSIC_PROVIDER=elevenlabs`) without touching core business logic.

---

## 3. High-Level Architecture Diagram

```
                             +-------------------------------+
                             |    IncuBrix Video Creator     |
                             |   (Dashboard / HTTP Client)   |
                             +-------------------------------+
                                             |
                                             | HTTP POST /api/v1/music/jobs
                                             v
                      +---------------------------------------------+
                      |               FastAPI Gateway               |
                      |  - Validates OpenAPI 3.1 Request Payload    |
                      |  - Enforces Idempotency-Key via Redis cache  |
                      |  - Emits Structured JSON Logs + Correlation |
                      |  - Returns HTTP 202 Accepted + job_id       |
                      +---------------------------------------------+
                                             |
                                             v Celery Task Enqueue
                      +---------------------------------------------+
                      |               Redis Broker                  |
                      +---------------------------------------------+
                                             |
                                             v Async Worker Pick-up
                      +---------------------------------------------+
                      |             Celery Audio Worker             |
                      +---------------------------------------------+
                                     /               \
       Step 1: Music Generation     /                 \  Step 2: Stem Separation
                                   v                   v
             +---------------------------+       +---------------------------+
             |  MusicProvider Interface  |       | StemSeparator Interface   |
             +---------------------------+       +---------------------------+
             |  - MockProvider (Testing) |       |  - MockSeparator (Test)   |
             |  - SoundverseMusicAdapter |       |  - SoundverseStemAdapter  |
             |  - ElevenLabsMusicAdapter |       |  - ElevenLabsStemAdapter  |
             +---------------------------+       +---------------------------+
                                   \                   /
                                    \                 /
                                     v               v
                      +---------------------------------------------+
                      |         Local DSP & Audio Engine            |
                      |  - Beat & Tempo Detection (BPM grid)        |
                      |  - Bar-Aligned Tail Slice / Musical Fade    |
                      |  - 48 kHz 24-bit PCM WAV Transcoding        |
                      |  - ITU-R BS.1770-4 Loudness (-16 LUFS)      |
                      |  - True Peak Limiting (<= -1.0 dBTP)        |
                      |  - Voiceover Sidechain Ducking (-8 to -15dB)|
                      |  - Linear Stem Summation & SDR Verification |
                      +---------------------------------------------+
                                             |
                                             v Uploads Outputs
                      +---------------------------------------------+
                      |            MinIO Object Storage             |
                      |  - mix.wav, mix.mp3                         |
                      |  - stems/drums.wav, bass.wav, guitar.wav... |
                      |  - mix_ducked.wav (when narration given)    |
                      |  - music_manifest.json                      |
                      +---------------------------------------------+
```

---

## 4. Subsystem Design & Technical Specifications

### 4.1 Integration Standard Adherence (Points 1–10)

| Requirement | Implementation Details |
| :--- | :--- |
| **1. One-command start & test** | `docker compose up --build -d` starts the FastAPI gateway, Celery worker, Redis, MinIO, and React dashboard. `docker compose exec api pytest` runs all tests with zero API keys using the Mock Provider. `.env.example` documents every variable. |
| **2. Documented HTTP API** | Auto-generated `openapi.yaml` (OpenAPI 3.1 specification) exported from FastAPI routes under `/api/v1/`. |
| **3. Background jobs** | Any job slower than 2s returns `HTTP 202 Accepted` with `{"job_id": "...", "status": "queued"}`. Status polled at `GET /api/v1/jobs/{job_id}` returning progress (0–100) and download links. Supports optional `callback_url` signed with HMAC-SHA256 in header `X-IncuBrix-Signature`. |
| **4. Safe retries** | Every `POST` endpoint requires or accepts an `Idempotency-Key` header. Requests are stored in Redis; identical repeated requests immediately return the cached job record. |
| **5. Clear errors** | Standardized JSON schema: `{"error": {"code": "UPPER_SNAKE_CASE", "message": "...", "retryable": bool, "details": {}}}`. All codes cataloged in `README.md`. |
| **6. Configuration** | 100% environment-driven via `pydantic-settings`. Zero hardcoded paths, URLs, or API keys. |
| **7. Files in, files out** | Direct audio file uploads or remote URLs (`narration_url`). Audio outputs stored in MinIO S3 bucket and served as time-limited presigned download URLs. |
| **8. Logs and health** | Structured JSON logging using `structlog` containing `timestamp`, `level`, `job_id`, and `X-Correlation-Id`. Health check endpoints at `GET /health` and `GET /ready`. |
| **9. Output manifest** | `music_manifest.json` delivered with every job: seed, model versions, section timestamps, beat grid, stem linear gains, reconstruction SDR, loudness, cost, and commercial licensing metadata. |
| **10. Batch runner** | A standalone CLI script (`python -m cli.batch_runner --input-dir ./test_inputs --output-dir ./test_results`) that executes batch jobs against the API and verifies results. |

---

### 4.2 The Provider Adapter Pattern

To isolate external dependencies and allow offline testing without incurring API fees, the core service interfaces with providers through Python Abstract Base Classes (`ABC`):

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class GenerationResult:
    audio_bytes: bytes
    format: str
    sample_rate: int
    duration_s: float
    provider: str
    model_version: str
    cost_usd: float

@dataclass
class StemSeparationResult:
    stems: Dict[str, bytes]  # {'drums': b'...', 'bass': b'...', 'guitar': b'...'}
    format: str
    sample_rate: int
    reconstruction_sdr_db: float
    cost_usd: float

class MusicGeneratorInterface(ABC):
    @abstractmethod
    def generate_music(self, prompt: str, duration_s: float, seed: int = None, **kwargs) -> GenerationResult:
        pass

class StemSeparatorInterface(ABC):
    @abstractmethod
    def separate_stems(self, audio_bytes: bytes, **kwargs) -> StemSeparationResult:
        pass
```

#### Provider Implementations:
1. `MockProvider`: Generates multi-channel procedural audio in-memory (sine waves with harmonic overtones for guitar/piano, sub-bass sine wave for bass, and filtered transient bursts for drums). Guaranteed mathematical reconstruction ($SDR > 80 \text{ dB}$), zero external dependencies, 100% deterministic test execution.
2. `SoundverseProvider`: Integrates with `apiv2.soundverse.ai` for music generation and 6-stem separation.
3. `ElevenLabsProvider`: Integrates with `api.elevenlabs.io` for millisecond-controlled generation and stem separation.

---

### 4.3 Digital Signal Processing (DSP) & Audio Engine

The local DSP post-processor performs crucial normalization and editing operations that external AI models do not provide:
1. **Sample Rate Standardization:** Transcodes all incoming audio streams to uncompressed **48 kHz 24-bit PCM WAV** using `soundfile` and high-quality polyphase sinc filtering.
2. **Exact Duration Alignment & Bar-Line Snapping:**
   * Detects the musical tempo ($BPM$) using spectral onset strength autocorrelation.
   * Calculates bar lengths: $\text{Bar Duration} = \frac{4 \times 60}{BPM}$.
   * Rather than hard-cutting audio at $T_{\text{target}}$ (which produces an audible click and clashing tail), the engine plans sections to end on musical bar boundaries and applies an intentional musical decay tail or smooth bar fade ($\le -35 \text{ dBFS}$ tail), guaranteeing $\Delta t \le 0.05 \text{ s}$.
3. **ITU-R BS.1770-4 Loudness Normalization:**
   * Measures integrated loudness via `pyloudnorm.Meter`.
   * Applies linear gain adjustment to achieve $-16.0 \text{ LUFS} \pm 0.2 \text{ LU}$.
   * Passes the normalized signal through an oversampled True Peak limiter ensuring $TP \le -1.0 \text{ dBTP}$ with zero dynamic clipping.
4. **Voiceover Sidechain Ducking:**
   * Analyzes the voiceover waveform from `narration_url`.
   * Computes an RMS speech envelope with $50\text{ ms}$ attack and $300\text{ ms}$ release.
   * Calculates an attenuation curve reducing the music bed by $10.0 \text{ dB}$ (within the required $8\text{--}15 \text{ dB}$ window) during active speech.
   * Exports the ducking gain curve into `music_manifest.json` and renders `mix_ducked.wav`.

---

## 5. Risk Assessment & Mitigation Matrix

| Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- |
| **External API Rate Limit or Outage** | High | Automatic fallback switch to secondary provider; retryable task backoff with exponential jitter; mock provider prevents CI blocks. |
| **Vocal Bleed in Instrumental Output** | High | Rigorous automated test checks vocal stem energy ($\le -55 \text{ dBFS}$). Prompts prepend strict instrumental tags; ElevenLabs uses `force_instrumental: true`. |
| **Duration Inaccuracy from Model** | Medium | Local DSP engine trims and aligns tracks on musical bar boundaries to guarantee $\pm 0.05$ s precision. |
| **API Secret Leakage** | Critical | Strict `.env` parsing via Pydantic; pre-commit git hooks; sanitized log formatters strip authorization headers. |

---

## 6. Implementation Readiness & Next Steps

All technical, legal, and architectural questions are now thoroughly investigated and documented. 

### Exact Next Steps:
1. **Obtain User Approval** to commence implementation.
2. **Scaffold Directory Structure & Docker Compose:**
   * Setup FastAPI service, Celery worker, Redis, MinIO, and React dashboard.
   * Create `.env.example`, `openapi.yaml`, and `README.md`.
3. **Implement Core Engine & Mock Provider:**
   * Implement DSP audio normalization (48 kHz WAV, LUFS, True Peak, Bar-aligned fade).
   * Implement Mock Provider and execute the automated PoC test suite to achieve 100% green tests.
4. **Implement Hosted Provider Adapters:**
   * Connect Soundverse and ElevenLabs client adapters behind the configuration switch.
5. **Implement Batch Runner & Hard Case Test Suite:**
   * Generate Core 10 audio pack, record demo video, and complete the submission Excel workbook.
