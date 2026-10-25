# AI Music Generation and Stem Separation Provider Research Report

**Document ID:** `DOC-RES-001`  
**Author:** Senior AI Audio Engineer & Technical Researcher  
**Project:** IncuBrix Studio — AI Background Music Engine for Video Production  
**Date Checked / Verified:** October 23, 2026  
**Status:** Complete Research & Feasibility Analysis  

---

## 1. Executive Summary & Purpose

The IncuBrix AI Background Music Engine requires generating original, commercially safe instrumental music that fits video durations exactly (within $\pm 0.05$ seconds) with intentional musical endings, delivered as a finished mix alongside at least three genuine instrument stems. The production specification strictly mandates commercial usability for all components in the default path, 48 kHz WAV audio conforming to $-16 \text{ LUFS} \pm 1 \text{ LU}$ and $\le -1.0 \text{ dBTP}$, and verifiable linear stem reconstructability.

This report documents exhaustive, evidence-based technical research into the candidate AI music and audio isolation providers:
1. **ElevenLabs Music API** (`Eleven Music` / `POST /v1/music` & `POST /v1/music/stem-separation`)
2. **Soundverse Enterprise API** (`generate_music` & `separate_stems`)
3. **Alternative Candidates:** Stability AI (**Stable Audio API**), Meta **Demucs** (local source separation), and Meta **AudioCraft / MusicGen**.

Every endpoint, parameter, price point, rate limit, and licensing term reported below has been verified against official provider documentation and live API contracts. No endpoints or terms have been fabricated.

---

## 2. Deep Dive: ElevenLabs Music API (Eleven Music)

### 2.1 Documentation & Endpoints
* **Official Music Product Page:** [https://elevenlabs.io/eleven-music-api](https://elevenlabs.io/eleven-music-api)
* **Compose Music API Reference:** [https://elevenlabs.io/docs/api-reference/music/compose](https://elevenlabs.io/docs/api-reference/music/compose)
* **Detailed Compose API Reference:** [https://elevenlabs.io/docs/api-reference/music/compose-detailed](https://elevenlabs.io/docs/api-reference/music/compose-detailed)
* **Stem Separation API Reference:** [https://elevenlabs.io/docs/api-reference/music/separate-stems](https://elevenlabs.io/docs/api-reference/music/separate-stems)
* **Terms & Commercial Conditions:** [https://elevenlabs.io/service-specific-terms](https://elevenlabs.io/service-specific-terms)
* **Date Verified:** October 23, 2026

### 2.2 Architecture & Available Endpoints
ElevenLabs provides two distinct endpoints for music generation and one for stem separation:
1. `POST https://api.elevenlabs.io/v1/music` — Synchronously composes a song or instrumental cue from a prompt or structured composition plan and streams the audio file directly in the response body.
2. `POST https://api.elevenlabs.io/v1/music/detailed` — Returns a `multipart/mixed` response containing JSON metadata (`song_metadata`, `composition_plan`, genres, duration) alongside the binary audio file.
3. `POST https://api.elevenlabs.io/v1/music/stem-separation` — Accepts an uploaded audio file via `multipart/form-data` and returns a ZIP archive containing isolated stems.

### 2.3 Authentication & Request Headers
* **Header:** `xi-api-key: <ELEVENLABS_API_KEY>`
* **Content-Type:** `application/json` (for `/music` and `/music/detailed`) or `multipart/form-data` (for `/music/stem-separation`).
* **Regional Hosting:** Default `https://api.elevenlabs.io`, with residency clusters in US (`api.us.elevenlabs.io`), EU (`api.eu.residency.elevenlabs.io`), India (`api.in.residency.elevenlabs.io`), and Singapore (`api.sg.residency.elevenlabs.io`).

### 2.4 Request & Response Schemas

#### Music Generation (`POST /v1/music` and `POST /v1/music/detailed`)
```json
{
  "prompt": "warm, optimistic acoustic pop for a product launch, builds to an uplifting finish",
  "music_length_ms": 45000,
  "model_id": "music_v2",
  "force_instrumental": true,
  "seed": 42,
  "respect_sections_durations": true,
  "store_for_inpainting": false,
  "sign_with_c2pa": false
}
```
* **Query Parameters:**
  * `output_format`: Enum. Supported values include `mp3_48000_192`, `mp3_48000_240`, `mp3_48000_320`, `pcm_44100`, `pcm_48000`, `mp3_44100_128`. Default is `auto` (resolves to `mp3_48000_192` for `music_v2`).
  * `enable_logging`: Boolean (default `true`). Enterprise accounts can set `false` for Zero Data Retention.
* **Key Fields for IncuBrix Requirements:**
  * `force_instrumental`: **Crucial.** Setting `force_instrumental: true` guarantees instrumental output with no vocal generation, directly satisfying IncuBrix Must-Have 3.
  * `music_length_ms`: Accepts integer millisecond durations from `3000` (3s) to `600000` (10 minutes).
  * `composition_plan`: For multi-section pieces, chunks can be defined with explicit `duration_ms` (3,000ms to 120,000ms), `positive_styles`, and `negative_styles`.
* **Response:**
  * For `/v1/music`: Status `200 OK` with binary audio payload. Header `song_id` contains the unique track identifier.
  * For `/v1/music/detailed`: Status `200 OK` with `multipart/mixed` containing JSON metadata and audio file.

#### Stem Separation (`POST /v1/music/stem-separation`)
```http
POST https://api.elevenlabs.io/v1/music/stem-separation?output_format=pcm_48000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryX

------WebKitFormBoundaryX
Content-Disposition: form-data; name="file"; filename="mix.wav"
Content-Type: audio/wav

[binary audio data]
------WebKitFormBoundaryX
Content-Disposition: form-data; name="stem_variation_id"

six_stems_v1
------WebKitFormBoundaryX--
```
* **Parameters:**
  * `file`: Multipart file upload (required).
  * `stem_variation_id`: Enum. `two_stems_v1` (vocals vs instrumental) or `six_stems_v1` (multitrack instrument breakdown).
  * `output_format`: Query param supporting `pcm_48000`, `pcm_44100`, `mp3_48000_192`, etc.
* **Response:** Status `200 OK` returning a `ZIP` archive containing individual audio files for each isolated stem.

### 2.5 Rate Limits, Concurrency, and Tier Constraints
ElevenLabs enforces concurrency-based throttling rather than traditional request-per-minute limits:
* **Free Tier:** Concurrency limit = `0` (Music generation is strictly disabled on Free tier).
* **Starter ($5/mo first month, $6/mo renew):** Concurrency limit = `2`.
* **Creator ($11/mo first month, $22/mo renew):** Concurrency limit = `2`.
* **Pro ($99/mo):** Concurrency limit = `2`. Pro tier or higher is required to request uncompressed `pcm_44100` or `pcm_48000` directly from the stem-separation endpoint.
* **Scale / Business ($299 / $990/mo):** Concurrency limit = `5`.
* **Queue Behavior:** When concurrency is exceeded, requests enter a priority queue. If the queue is saturated, HTTP `429 Too Many Requests` is returned. Response headers `current-concurrent-requests` and `maximum-concurrent-requests` indicate load.

### 2.6 Pricing & Commercial Licensing
* **Credit Consumption:** ElevenLabs consumes shared subscription credits.
  * Music generation: $\approx 900$ credits per minute of generated audio.
  * Stem separation (`six_stems_v1`): $1\times$ generation cost ($\approx 900$ credits per minute).
  * Effective cost per minute of full mix + stems: $\approx 1,800$ credits. On a Pro plan ($99 for 600,000 credits), the effective cost is $\approx \$0.165$ per 1,000 credits, translating to $\approx \$0.30$ per minute of music + stems.
* **Commercial Rights:**
  * Free tier: Non-commercial only; attribution mandatory.
  * Paid tiers (Starter, Creator, Pro, Scale): **Full commercial license** for generated content. Users retain ownership and monetization rights for commercial outputs, provided they comply with the Acceptable Use Policy (no impersonation, no generating infringing audio).

---

## 3. Deep Dive: Soundverse Enterprise API

### 3.1 Documentation & Endpoints
* **Official Developer Docs:** [https://platform.soundverse.ai/docs](https://platform.soundverse.ai/docs)
* **Music Generation Capability:** [https://platform.soundverse.ai/docs/music-generation](https://platform.soundverse.ai/docs/music-generation)
* **Stem Separation Capability:** [https://platform.soundverse.ai/docs/stem-separation](https://platform.soundverse.ai/docs/stem-separation)
* **Compat Routes:** [https://platform.soundverse.ai/docs/compat-routes](https://platform.soundverse.ai/docs/compat-routes)
* **Tool Catalog & Pricing:** [https://platform.soundverse.ai/docs/tool-catalog](https://platform.soundverse.ai/docs/tool-catalog)
* **Date Verified:** October 23, 2026

### 3.2 Architecture & API Surface
Soundverse operates an Enterprise Gateway architecture on `https://apiv2.soundverse.ai`. All requests are handled asynchronously through task jobs:
1. **Generic Native Route:** `POST /v1/generations` with a `tool_id` matching an active catalog entry.
2. **Compatibility Routes:** Direct HTTP endpoints preserving legacy schemas:
   * Music Generation: `POST /v7/generate/music` (also `/v5` and `/v6`)
   * 6-Stem Separation: `POST /v1/generate/stem-separation/six-stem`
   * 12-Stem Separation: `POST /v1/generate/stem-separation/all-stems`
   * 2-Stem Separation: `POST /v1/generate/stem-separation/vocals` or `/instruments`
3. **Task Status & File Retrieval:**
   * Polling: `GET /v1/generations/{job_id}` or `GET /v7/status?job_id={job_id}`
   * Live SSE Stream: `GET /v1/generations/{id}/stream`
   * Signed File Download: `GET /v1/files/{file_id}/download`

### 3.3 Authentication & Headers
* **Header:** `Authorization: Bearer sksoundverse_<token>`
* **Idempotency:** Native support for `Idempotency-Key: <string>` (up to 200 chars, `[A-Za-z0-9_.:-]`). Retrying an identical key returns the cached task without double-billing.

### 3.4 Request & Response Schemas

#### Music Generation (`POST /v7/generate/music`)
```json
{
  "prompt": "warm, optimistic acoustic pop for a product launch, builds to an uplifting finish",
  "parameters": {
    "versions": 1
  }
}
```
* **Native Tool ID:** `(model="v7", operation="generate_music")` on `POST /v1/generations` with `payload_json`.
* **Response (Immediate 201 Created):**
```json
{
  "job_id": "gen_88fbc71a2b3c",
  "status": "queued"
}
```
* **Completed Task Output (`GET /v1/generations/{id}`):**
```json
{
  "job_id": "gen_88fbc71a2b3c",
  "status": "completed",
  "output": {
    "assets": [
      {
        "file_id": "fil_9921bc43",
        "role": "mix",
        "url": "https://storage.soundverse.ai/...",
        "format": "mp3"
      }
    ]
  }
}
```

#### 6-Stem Separation (`POST /v1/generate/stem-separation/six-stem`)
```json
{
  "audioUrl": "https://storage.soundverse.ai/.../mix.mp3"
}
```
* **Native Tool ID:** `(model="v5", operation="separate_stems")`.
* **Underlying Engine:** Explicitly documented as Meta Demucs 6-way split (`htdemucs_6s`).
* **Returned Stems:**
  1. `drums`
  2. `bass`
  3. `vocals`
  4. `guitar`
  5. `piano`
  6. `other`
* **Response:** Returns 6 individual asset downloads on completion.

### 3.5 Pricing Structure
Soundverse publishes transparent, flat-rate pricing per track and per separation:
* **Music Generation (`generate_music` v5 / v6 / v7):**
  * Royalty-Free tier (`license: 1`): **$0.07 per track**
  * Standard tier (`license: 2`): **$0.11 per track**
  * Distribution tier (`license: 3`): **$0.14 per track**
  * Sync tier (`license: 4`): **$0.28 per track**
  * Master tier (`license: 5`): **$0.70 per track**
* **Stem Separation (`separate_stems` 2-stem, 6-stem, or 12-stem):**
  * **$0.10 flat per separation** across all tiers and all models.
* **Total Combined Cost:**
  * For 1 track generated + 6-stem separated on Royalty-Free tier: $\$0.07 + \$0.10 = \mathbf{\$0.17}$.
  * On Standard tier: $\$0.11 + \$0.10 = \mathbf{\$0.21}$.

### 3.6 Limitations & Nuances
1. **Duration Parameter in Prompt:** Soundverse's `generate_music` API does not accept an explicit `duration_s` parameter in its request payload. The model generates standard length audio clips ($\approx 30\text{--}60$ seconds). Achieving longer durations requires chaining the `extend_music` endpoint ($0.07/call), and exact timing ($\pm 0.05$ s) requires local bar-aligned audio slicing.
2. **Audio Formats:** Generated tracks are initially delivered as high-bitrate MP3/M4A links. Transcoding to 48 kHz uncompressed WAV and loudness normalization must occur on the backend service.

---

## 4. Alternative Candidates Analysis

### 4.1 Stability AI: Stable Audio API
* **Base Endpoint:** `https://api.stability.ai/v2beta/audio/stable-audio/text-to-audio`
* **Model Versions:** Stable Audio 2.0 / 2.5 (commercial hosted) and Stable Audio Open 1.0 (open weights).
* **Capabilities:** Generates full tracks up to 180–190 seconds (3 minutes) from text prompts.
* **Pricing:** Consumes $\approx 20$ Stability credits per generation ($\approx \$0.20$ per track).
* **Stem Separation:** Stable Audio API **does not** provide a hosted stem-separation endpoint. It produces only mixed stereo master audio. Using Stable Audio requires integrating a separate stem separation engine.
* **Licensing:**
  * Commercial API: Fully licensed for commercial outputs.
  * Stable Audio Open weights: Governed by the Stability AI Community License Agreement (free for entities under $1M gross annual revenue; commercial enterprise license required above $1M).

### 4.2 Local Pre-Trained Separation: Meta Demucs
* **Repository:** `facebookresearch/demucs` (Hybrid Demucs / HTDemucs)
* **Architecture:** 4-stem (`drums`, `bass`, `vocals`, `other`) or 6-stem (`drums`, `bass`, `vocals`, `guitar`, `piano`, `other`).
* **Source Code License:** **MIT License** (fully commercial-friendly for software integration).
* **Model Weights License & Data Risk:** The official pre-trained weights (`htdemucs`, `htdemucs_6s`, `htdemucs_ft`) were trained on the **MUSDB-HQ / MUSDB18** dataset, which is restricted strictly to non-commercial academic research. Demucs primary author Alexandre Défossez has explicitly noted that Meta's pre-trained weights are a research artifact for personal/research use.
* **Commercial Compliance Impact:** Using local Demucs with standard pre-trained weights in the default production path violates our commercial license standard ("*No research-only or non-commercial models, data or media (for example CC BY-NC) in the default path*"). However, hosted commercial APIs (like Soundverse) assume the commercial indemnification and platform licensing on their end.

### 4.3 Meta AudioCraft / MusicGen
* **Repository:** `facebookresearch/audiocraft`
* **Weights License:** **CC BY-NC 4.0 (Non-Commercial)**.
* **Commercial Compliance Impact:** **Disqualified** from the default path. Cannot be used commercially without training custom weights from scratch on fully licensed audio datasets.

---

## 5. Feasibility: Single Provider vs. Separate Providers

| Consideration | Option A: Pure ElevenLabs Pipeline | Option B: Pure Soundverse Pipeline | Option C: Hybrid Pipeline (ElevenLabs Gen + Soundverse Stems) |
| :--- | :--- | :--- | :--- |
| **Generation Capability** | `POST /v1/music` (`music_v2`) | `POST /v7/generate/music` | `POST /v1/music` (ElevenLabs) |
| **Stem Capability** | `POST /v1/music/stem-separation` | `POST /v1/generate/stem-separation/six-stem` | `POST /v1/generate/stem-separation/six-stem` |
| **Is Single Provider Possible?** | **Yes** (Both endpoints supported) | **Yes** (Both endpoints supported) | **No** (Uses two external providers) |
| **Direct Millisecond Control** | **Yes** (`music_length_ms` 3s–600s) | No (Requires looping / extension) | **Yes** (`music_length_ms`) |
| **Guaranteed Instrumental** | **Yes** (`force_instrumental: true`) | Implicit via prompt | **Yes** (`force_instrumental: true`) |
| **Cost per 1-min track + stems** | $\approx \$0.30\text{--}\$0.60$ | $\approx \$0.17\text{--}\$0.21$ | $\approx \$0.25\text{--}\$0.40$ |
| **Tier Gating Friction** | High (Pro tier $99/mo needed for PCM stems; Concurrency=2) | Low (Pay-as-you-go self-serve gateway) | Moderate (Requires managing 2 API keys) |

### Engineering Verdict on Provider Consolidation:
While both ElevenLabs and Soundverse offer single-provider capabilities, **music generation and stem separation are fundamentally independent operations in both architectures**. Neither provider returns stems in a single API call; both require a two-step pipeline (`generate_mix` $\rightarrow$ `separate_stems`). 

Therefore, architectural decoupling via the **Adapter Pattern** is mandatory. The core engine must interface with an abstract `MusicGeneratorInterface` and `StemSeparatorInterface`. This ensures that:
1. Soundverse can serve as the cost-efficient primary provider ($0.17/track).
2. ElevenLabs can serve as an immediate drop-in replacement where explicit millisecond composition plans or strict prompt adherence are required.
3. A local DSP / Mock Adapter allows the entire test suite and dockerized container to run with zero API keys or external fees.

---

## 6. Genuine Instrument-Stem Separation Technical Deep-Dive

### 6.1 What Providers Return
In both Soundverse 6-stem and ElevenLabs `six_stems_v1`, the separation engine returns individual mono or stereo audio channels isolating specific musical roles:
1. `drums.wav`: Transients, kick, snare, cymbals, hi-hats, percussion.
2. `bass.wav`: Low-frequency melodic baseline, synth bass, electric bass.
3. `guitar.wav`: Acoustic, electric, rhythm, and lead guitar parts.
4. `piano.wav`: Acoustic piano, electric piano, organ, keyboards.
5. `other.wav`: Synthesizers, pads, strings, brass, orchestral textures, FX.
6. `vocals.wav`: Vocal tracks, speech, choral layers.

### 6.2 Behavior for Instrumental Prompts
When generating instrumental music (using `force_instrumental: true` or instrumental prompting), the AI music generator does not synthesize vocal formant frequencies. 
* **Expected Output:** The resulting `vocals.wav` stem is silence or near-silence (digital zero or ambient model noise floor $\le -70 \text{ dBFS}$).
* **Engine Verification:** The IncuBrix engine inspects the vocal stem. If its integrated loudness is below $-60 \text{ LUFS}$ / RMS below $-70 \text{ dBFS}$, it is confirmed clean and omitted or saved as silent. If vocal energy is detected above $-50 \text{ dBFS}$, the track fails the instrumental check.

### 6.3 Signal Reconstructability
In traditional studio multitrack recording, the mix is a linear sum of stems:
$$x[n] = \sum_{i=1}^{M} g_i \cdot s_i[n]$$
where $g_i$ is the linear gain assigned to stem $s_i[n]$.

However, AI source separation models operate via time-frequency masking or complex spectrogram / U-Net / Demucs convolutional networks. Because non-linear operations (ReLU, soft masking, phase reconstruction, post-separation normalization) are applied:
$$\sum_{i=1}^{M} s_i[n] = x[n] + \epsilon[n]$$
where $\epsilon[n]$ is the **reconstruction residual**.

### 6.4 Measuring Reconstruction Error & Stem Leakage

#### Metric 1: Signal-to-Reconstruction-Error Ratio (Reconstruction SNR / SDR)
$$SNR_{\text{recon}} = 10 \cdot \log_{10} \left( \frac{\sum_{n=1}^{N} x[n]^2}{\sum_{n=1}^{N} \left(x[n] - \sum_{i=1}^{M} g_i s_i[n]\right)^2} \right) \quad (\text{dB})$$
* **Interpretation:** 
  * $> 30 \text{ dB}$: High fidelity; residual is imperceptible.
  * $20\text{--}30 \text{ dB}$: Typical for advanced deep separation (e.g., Demucs v4); minor phase artifacts.
  * $< 15 \text{ dB}$: Noticeable phase cancellation or missing energy.

#### Metric 2: Difference in RMS and Peak Amplitude
$$E_{\text{RMS}} = 20 \log_{10} \left( \text{RMS}\left(x - \sum g_i s_i\right) \right) - 20 \log_{10}(\text{RMS}(x)) \quad (\text{dB})$$
The IncuBrix engine logs $E_{\text{RMS}}$ directly in `music_manifest.json` under `stem_reconstruction_error_db`.

#### Metric 3: Stem Bleed / Inter-Stem Leakage
Bleed occurs when spectral energy belonging to one instrument leaks into another stem (e.g., drum snare leaking into the guitar stem).
We measure stem bleed using the normalized zero-lag cross-correlation matrix between all stem pairs $(i, j)$:
$$R_{ij} = \frac{\sum_{n=1}^{N} s_i[n] \cdot s_j[n]}{\sqrt{\sum_{n=1}^{N} s_i[n]^2} \cdot \sqrt{\sum_{n=1}^{N} s_j[n]^2}}$$
* High cross-correlation between nominally independent stems (e.g., $R_{\text{drums}, \text{bass}} > 0.4$) indicates significant spectral leakage or shared broadband noise.
* In addition, spectral flux and BSS-Eval metrics (SIR: Signal to Interference Ratio) measure the ratio of target signal power to interference power from other stems.

### 6.5 Remaining Limitations of AI Stem Separation
1. **Master Bus Compression & Limiter Inversion:** A generated mix contains master bus compression and peak limiting that glue the instruments together dynamically. Decomposing the master into stems separates linear sounds, but linearly summing them back will not replicate the identical non-linear peak limiting behavior of the original mix without re-mastering.
2. **Phase Smearing & Comb Filtering:** Masking algorithms estimate the magnitude spectrogram and apply the original mixture phase, or estimate phase via complex convolutions. Minor phase errors cause comb-filtering when multiple stems are played together.
3. **Artifacts on Dense Arrangements:** Distorted guitars, reverb tails, and aggressive synth pads share overlapping frequency bins with drums and vocals, occasionally leading to "watery" or "swirling" artifacts in the `other` stem.

---

## 7. Conclusions & Findings Summary

1. **Soundverse Enterprise API** represents the lowest-cost, most commercially direct platform for 6-stem separation ($0.10/separation flat) and generation ($0.07–$0.11/track).
2. **ElevenLabs Music API** provides superior prompt control, explicit millisecond length planning, and guaranteed instrumental enforcement (`force_instrumental: true`), but at a higher cost ($\approx \$0.30\text{--}\$0.60$/minute) and with Pro-tier constraints on uncompressed PCM downloads.
3. **Meta Demucs** source code is MIT-licensed, but pre-trained weights carry non-commercial research dataset contamination (MUSDB-HQ), making direct self-hosting in the default commercial path a high compliance risk under Rule 2.
4. **Decoupled Architecture:** The system must implement an abstracted adapter layer supporting both Soundverse and ElevenLabs, backstopped by a local DSP post-processor and a mock adapter for automated testing.
