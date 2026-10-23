# SOURCES.md — Models, APIs, Libraries, and Data Sources

This document provides full disclosure of every external API service, software library, dataset, and licensing condition used in the IncuBrix AI Background Music Engine, in strict compliance with the IncuBrix Assessment Integration Standard.

---

## 1. External AI Music & Audio Separation Providers

### 1.1 Soundverse Enterprise API (Primary Hosted Provider)
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
* **Commercial License:** Standard commercial tier explicitly grants video synchronization, client deliverables, and commercial monetization rights.
* **Integration Adapter:** `src/providers/soundverse.py` (`SoundverseAdapter`)

### 1.2 ElevenLabs Music API (Fallback Hosted Provider)
* **Provider:** ElevenLabs Inc.
* **Service:** Eleven Music API (`api.elevenlabs.io`)
* **Endpoints Used:**
  * Music Generation: `POST /v1/music` (model `music_v2`, `force_instrumental: true`)
  * Stem Separation: `POST /v1/music/stem-separation` (`six_stems_v1`)
* **Documentation:** [https://elevenlabs.io/docs/api-reference/music/compose](https://elevenlabs.io/docs/api-reference/music/compose)
* **Published Pricing:**
  * ~900 credits/min for generation + ~900 credits/min for stem separation (~$0.30 - $0.60/min based on subscription tier).
* **Commercial License:** Commercial monetization rights granted on all paid tiers (Starter, Creator, Pro, Scale). Free tier is strictly non-commercial.
* **Integration Adapter:** `src/providers/elevenlabs.py` (`ElevenLabsAdapter`)

### 1.3 Procedural Audio Generator (Default Offline Testing Provider)
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
| **Pydantic** | `>=2.7.0` | MIT | Allowed | Data validation and structured manifest schemas |
| **pydantic-settings** | `>=2.1.0` | MIT | Allowed | Environment variable parsing and `.env` support |
| **HTTPX** | `>=0.25.0` | BSD-3-Clause | Allowed | Async and sync HTTP client for provider REST APIs |
| **python-dotenv** | `>=1.0.0` | BSD-3-Clause | Allowed | Local `.env` credential loading |
| **pytest** | `>=7.4.0` | MIT | Allowed | Automated test execution framework |

---

## 3. Separation Model Weights Disclosure & Licensing Note

* **Meta Demucs (`htdemucs_6s`):**
  * The open-source code for Demucs is licensed under the MIT License.
  * *Important Legal Finding:* Meta's official pre-trained weights for 6-stem Demucs were trained on the MUSDB-HQ research dataset, which contains a non-commercial academic clause (`CC BY-NC-SA 4.0`).
  * *Resolution:* In the IncuBrix architecture, Demucs is consumed exclusively through the commercially indemnified **Soundverse Enterprise API** ($0.10 flat commercial separation) or the **ElevenLabs API**, rather than self-hosting unverified research weights in the production default path.
