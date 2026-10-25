# SOURCES.md — Models, APIs, Libraries, and Data Sources

This document provides full disclosure of every external API service, software library, dataset, and licensing condition used in the IncuBrix AI Background Music Engine, in strict compliance with commercial enterprise integration and licensing standards.

---

## 1. External AI Music & Audio Separation Providers

### 1.1 Stability AI — Stable Audio (Recommended Commercial Provider)
* **Provider:** Stability AI Ltd.
* **Service:** Stable Audio REST API (`api.stability.ai`)
* **Model:** `stable-audio-3` (via `/v2beta/audio/stable-audio/text-to-audio`)
* **Official Documentation:** [https://platform.stability.ai/docs/api-reference#tag/Audio](https://platform.stability.ai/docs/api-reference#tag/Audio)
* **Published Pricing:**
  * Developer credits cost $0.01/credit ($10 minimum top-up = 1,000 credits).
  * Audio generation costs 20 credits per generation ($0.20 flat cost).
* **Free Tier Reality:**
  * Stability AI developer platform grants 25 free credits upon initial developer signup ($0.25 value).
  * Because generation costs 20 credits, this provides **exactly 1 free generation** for testing.
  * *Important distinction:* The consumer web application at `stableaudio.com` offers 50 free credits per month, but those consumer credits **cannot** be used on the developer REST API (`api.stability.ai`).
* **Commercial License:** Generation using developer API credits grants commercial rights for client deliverables, monetization, and synchronization.
* **Max Output Duration:** Up to 190 seconds (3 minutes 10 seconds).
* **Output Format:** MP3 or WAV directly streamed.
* **Integration Adapter:** `src/providers/stable_audio.py` (`StableAudioAdapter`)

### 1.2 Meta MusicGen via Replicate (Research & Non-Commercial Provider)
* **Provider:** Replicate Inc. hosting Meta AI's MusicGen model
* **Service:** Replicate API (`api.replicate.com/v1`)
* **Official Documentation:** [https://replicate.com/meta/musicgen](https://replicate.com/meta/musicgen)
* **Published Pricing:**
  * Hardware compute billing: ~$0.0014 per second on Nvidia A100 GPU (~$0.045 for a 30s audio cue).
* **Free Tier Reality:**
  * Replicate has no sustained free API tier. A valid credit card is required to create API tokens.
* **Licensing Restriction:**
  * **CRITICAL:** Official Meta MusicGen model weights are released under `CC-BY-NC 4.0` (Creative Commons Attribution-NonCommercial 4.0).
  * It is strictly legally prohibited to use Meta MusicGen for commercial client projects or monetized background music without a custom commercial agreement from Meta.
* **Max Output Duration:** 30 seconds default.
* **Integration Adapter:** `src/providers/replicate.py` (`ReplicateMusicGenAdapter`)

### 1.3 Soundverse Enterprise API
* **Provider:** Soundverse AI Inc.
* **Service:** Soundverse Enterprise API Gateway (`apiv2.soundverse.ai`)
* **Endpoints Used:**
  * Music Generation: `POST /v7/generate/music`
  * Stem Separation: `POST /v1/generate/stem-separation/six-stem`
  * Task Status: `GET /v1/generations/{job_id}`
* **Documentation:** [https://platform.soundverse.ai/docs](https://platform.soundverse.ai/docs)
* **Published Pricing:**
  * Music Generation: $0.07/track (Royalty-Free), $0.11/track (Standard Commercial).
  * 6-Stem Separation: $0.10 flat per separation.
* **Free Tier Reality:** 10 initial trial credits granted upon developer registration.
* **Commercial License:** Standard commercial tier explicitly grants video synchronization and commercial monetization rights.
* **Integration Adapter:** `src/providers/soundverse.py` (`SoundverseAdapter`)

### 1.4 ElevenLabs Music API
* **Provider:** ElevenLabs Inc.
* **Service:** Eleven Music API (`api.elevenlabs.io`)
* **Endpoints Used:**
  * Music Generation: `POST /v1/music` (model `music_v2`, `force_instrumental: true`)
  * Stem Separation: `POST /v1/music/stem-separation` (`six_stems_v1`)
* **Documentation:** [https://elevenlabs.io/docs/api-reference/music/compose](https://elevenlabs.io/docs/api-reference/music/compose)
* **Published Pricing:**
  * Consumes character/audio quota from paid subscription plans (~$0.30 - $0.60/min equivalent).
* **Free Tier Reality:**
  * Free tier accounts do not have access to the Music API endpoint. Requires paid Creator or Pro tier.
* **Commercial License:** Commercial monetization rights granted on all paid tiers.
* **Integration Adapter:** `src/providers/elevenlabs.py` (`ElevenLabsAdapter`)

### 1.5 Procedural Audio Generator (Default Offline Testing Provider)
* **Provider:** Local In-Memory Procedural Synthesis Engine
* **Algorithm:** Procedural multi-track acoustic synthesis (transient percussion modeling, harmonic overtone bassline, polyphonic triads, bell/melody motifs).
* **API Cost:** $0.00 (Zero network egress, 100% deterministic, offline).
* **Commercial Rights:** Fully proprietary internal code, MIT License compatible.
* **Integration Adapter:** `src/providers/mock_provider.py` (`MockProvider`)


---

## 2. Open-Source Libraries & Dependencies

| Library | Version | License | Commercial Use | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **NumPy** | `>=1.26.0` | BSD-3-Clause | Allowed | High-performance array calculations and audio sample buffers |
| **SciPy** | `>=1.11.0` | BSD-3-Clause | Allowed | Polyphase sinc resampling and signal envelope filtering |
| **SoundFile** | `>=0.12.0` | BSD-3-Clause (libsndfile LGPL 2.1+) | Allowed | 48 kHz uncompressed WAV and MP3 encoding/decoding |
| **pyloudnorm** | `>=0.1.1` | MIT | Allowed | Standard ITU-R BS.1770-4 loudness measurement |
| **FastAPI** | `>=0.109.0`| MIT | Allowed | ASGI web framework with OpenAPI 3.1 support |
| **Uvicorn** | `>=0.27.0` | BSD-3-Clause | Allowed | High-performance ASGI production server |
| **SQLAlchemy** | `>=2.0.25`| MIT | Allowed | Database ORM and connection pooling |
| **Celery** | `>=5.3.6`  | BSD-3-Clause | Allowed | Distributed asynchronous task queue for audio worker |
| **Redis** | `>=5.0.1`  | MIT | Allowed | Message broker and in-memory rate limiting store |
| **MinIO Client**| `>=7.2.0`| Apache-2.0 | Allowed | S3-compatible object storage SDK |
| **Pydantic** | `>=2.7.0` | MIT | Allowed | Data validation and structured manifest schemas |
| **pydantic-settings** | `>=2.1.0` | MIT | Allowed | Environment variable parsing and `.env` support |
| **HTTPX** | `>=0.25.0` | BSD-3-Clause | Allowed | Async and sync HTTP client for provider REST APIs |
| **structlog** | `>=24.1.0` | Apache-2.0 / MIT | Allowed | Machine-readable structured JSON logging |
| **pytest** | `>=7.4.0` | MIT | Allowed | Automated test execution framework |
| **React** | `^19.3.0`  | MIT | Allowed | Frontend UI library for Audio Studio dashboard |
| **Vite** | `^8.3.0`   | MIT | Allowed | Frontend build tool and development server |
| **Lucide React**| `^1.61.0`| ISC | Allowed | Interface iconography |

---

## 3. Separation Model Weights Disclosure & Licensing Note

* **Meta Demucs (`htdemucs_6s`):**
  * The open-source code for Demucs is licensed under the MIT License.
  * *Important Legal Finding:* Meta's official pre-trained weights for 6-stem Demucs were trained on the MUSDB-HQ research dataset, which contains a non-commercial academic clause (`CC BY-NC-SA 4.0`).
  * *Resolution:* In the IncuBrix architecture, Demucs is consumed exclusively through the commercially indemnified **Soundverse Enterprise API** ($0.10 flat commercial separation) or the **ElevenLabs API**, rather than self-hosting unverified research weights in the production default path.
