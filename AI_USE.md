# AI_USE.md — AI Engineering Tools & Implementation Provenance

This document records the AI systems engineering tools, foundation models, and development workflows employed during the architecture, implementation, and verification of the IncuBrix AI Background Music Engine.

---

## 1. Tool & Model Details

* **AI Coding Assistant:** Google DeepMind Antigravity IDE
* **Core Foundation Model:** Gemini 3.8 Flash (Advanced Agentic Coding)
* **Date of Use:** October 23, 2026
* **Developer Role:** System Architect, Audio DSP Engineer, Full-Stack Developer, QA & Reliability Auditor

---

## 2. Tasks Performed with AI Assistance

### Phase 1: Day 1 Audio Proof-of-Concept & DSP Finishing
- **Decoupled Provider Architecture:** Designed provider interfaces (`MusicGeneratorInterface`, `StemSeparatorInterface`, `AudioProviderInterface`) and implemented adapters for Soundverse Enterprise, ElevenLabs Music, and the deterministic in-memory `MockProvider`.
- **Digital Signal Processing:** Implemented 48 kHz polyphase rational resampling (`scipy.signal.resample_poly`), sample-accurate cosine decay tail endings, ITU-R BS.1770-4 integrated loudness normalization (-16.0 LUFS), 4x sinc oversampled True Peak limiting ($\le -1.0$ dBTP), and speech sidechain envelope ducking.
- **Audio Validation:** Created `src/audio/validator.py` computing mathematical linear stem reconstruction SDR, RMS residual levels, and click/gap derivative thresholds.

### Phase 2: FastAPI Backend, Database & Storage Architecture
- **Asynchronous API Gateway:** Built FastAPI service adhering to OpenAPI 3.1.0 specifications with asynchronous job lifecycles (HTTP 202) and polling.
- **Idempotency & Database:** Designed SQLAlchemy models with SHA-256 request hashing, database-level unique constraints, and atomic conflict detection (HTTP 409).
- **Security & SSRF Mitigation:** Implemented DNS resolution checks blocking RFC 1918 private subnets, cloud metadata endpoints, and non-HTTP protocols.
- **Object Storage Service:** Built MinIO S3-compatible asset management service with local disk fallback.

### Phase 3: React + TypeScript Audio Studio Dashboard
- **Modern Dark UI:** Built React 19 + TypeScript audio production interface using Vanilla CSS tokens, glassmorphism, and responsive layouts.
- **Interactive Multitrack Player:** Implemented Web Audio API multi-channel audio player with individual stem volume faders, solo/mute toggles, waveform progression, and dynamic section cue markers.

### Phase 4: QA, Hard Cases & Batch Test Runner
- **Prompt Guard & Guardrails:** Built `prompt_guard.py` detecting contradictory emotional descriptors, intercepting copyrighted artist/song references, and suppressing vocal synthesis.
- **Automated Test Harness:** Authored comprehensive pytest suites (`tests/test_mandatory_audio_quality.py`, `tests/test_hard_cases_comprehensive.py`, `tests/test_deployment_security.py`) achieving 67 passed tests (100% pass rate).
- **Reproducible Batch Runner CLI:** Implemented `scripts/batch_runner.py` automating batch job submissions, asset downloading, and independent DSP verification across 15 test vectors.

### Phase 5: Containerization, Deployment & Compliance
- **Docker Compose:** Multi-container orchestration for FastAPI, Celery worker, PostgreSQL, Redis, MinIO, and React/Nginx frontend.
- **Production Security:** Sliding-window rate limiting, request payload size caps, and demo access token protection.
- **Cloud Infrastructure-as-Code:** Authored `render.yaml` Blueprint and comprehensive deployment guide (`docs/deployment_guide.md`).

---

## 3. Engineering Code Ownership & Verification

All generated code, mathematical algorithms, DSP formulas, database schemas, and test suites have been inspected, tested, and verified by the engineering team. Every component is fully understood, covered by automated unit and integration tests, and ready for production operations and ongoing maintenance.
