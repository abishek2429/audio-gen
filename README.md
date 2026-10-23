# IncuBrix AI Background Music Engine for Video

Original, commercially safe instrumental music that fits a video exactly — with real instrument stems, sample-accurate duration alignment, and ITU-R BS.1770-4 loudness compliance.

---

## 1. System Architecture

```
                             +-------------------------------+
                             |    IncuBrix Video Creator     |
                             |   (Client / Video Editor)     |
                             +-------------------------------+
                                             |
                                             | HTTP POST /api/v1/music/jobs
                                             v
                       +---------------------------------------------+
                       |               FastAPI Gateway               |
                       |  - Validates OpenAPI 3.1 Request Payload    |
                       |  - Enforces Idempotency-Key Header          |
                       |  - Blocks SSRF against Private/Internal IPs |
                       |  - Emits Structured JSON Logs + Correlation |
                       |  - Returns HTTP 202 Accepted + job_id       |
                       +---------------------------------------------+
                                             |
                        +--------------------+--------------------+
                        | (In-process Queue)                      | (Celery Queue)
                        v                                         v
         +-----------------------------+           +-----------------------------+
         |     Async Worker Thread     |           |     Celery Audio Worker     |
         +-----------------------------+           +-----------------------------+
                        \                                         /
                         \                                       /
                          v                                     v
                       +---------------------------------------------+
                       |              Audio Generation               |
                       |  - Soundverse Enterprise (v7 Demucs 6-stem) |
                       |  - ElevenLabs Music API (music_v2)          |
                       |  - Mock Provider (Offline Synthetic Audio)  |
                       +---------------------------------------------+
                                             |
                                             v
                       +---------------------------------------------+
                       |          Local DSP & Audio Engine           |
                       |  - 48 kHz 24-bit PCM WAV Transcoding        |
                       |  - Sample-Accurate Duration (|Δt| <= 0.05s) |
                       |  - Cosine Musical Tail (No Truncation Pops) |
                       |  - ITU-R BS.1770-4 Loudness (-16 LUFS)      |
                       |  - True Peak Limiting (<= -1.0 dBTP)        |
                       |  - Voiceover Sidechain Ducking (-10 dB)     |
                       |  - Mathematical Stem Reconstruction (SDR)   |
                       +---------------------------------------------+
                                             |
                                             v
                       +---------------------------------------------+
                       |        MinIO S3 / Object Storage            |
                       |  - mix.wav, mix.mp3                         |
                       |  - stems/drums.wav, bass.wav, harmony...    |
                       |  - mix_ducked.wav (when voiceover provided) |
                       |  - music_manifest.json                      |
                       |  - validation_report.json                   |
                       +---------------------------------------------+
                                             |
                                             v
                       +---------------------------------------------+
                       |       HMAC-SHA256 Webhook Callback          |
                       |  (Signed with X-IncuBrix-Signature header)  |
                       +---------------------------------------------+
```

---

## 2. Quickstart Setup (Under 10 Commands)

### Option A: Local Development & Automated Test Execution (Zero External Keys Required)

```bash
# 1. Clone repository
git clone <repo-url> && cd audio-gen

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database migrations
python -m alembic upgrade head

# 4. Run full test suite (39 automated tests, offline)
python -m pytest -v

# 5. Start FastAPI development server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Option B: One-Command Docker Compose Deployment

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and launch all services (FastAPI, Celery, PostgreSQL, Redis, MinIO)
docker compose up --build -d

# 3. Verify health
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
```

---

## 3. API Contract & Endpoints

### 3.1 `POST /api/v1/music/jobs`
Creates a background music generation job.

#### Headers:
- `Idempotency-Key` *(recommended)*: Unique string. Re-sending identical request returns existing job without duplicate billing. Re-sending differing request returns HTTP 409 Conflict.
- `X-Correlation-Id` *(optional)*: Tracing identifier propagated across logs.

#### Request Body:
```json
{
  "prompt": "warm, optimistic acoustic pop for a product launch, builds to an uplifting finish",
  "duration_s": 45.0,
  "sections": [
    {"start_s": 0.0, "mood": "calm intro"},
    {"start_s": 12.5, "mood": "build-up"},
    {"start_s": 30.0, "mood": "uplifting peak"}
  ],
  "tempo_bpm": 120,
  "key": "C major",
  "loopable": false,
  "narration_url": "https://example.com/voiceover.wav",
  "callback_url": "https://creator.app/webhooks/music",
  "seed": 42,
  "output": {
    "sample_rate": 48000,
    "target_lufs": -16.0,
    "formats": ["wav", "mp3"]
  }
}
```

#### Response (`HTTP 202 Accepted`):
```json
{
  "job_id": "job_80829c9c7aa6",
  "status": "queued",
  "progress": 0,
  "created_at": "2026-10-23T12:00:00Z",
  "message": "Job accepted and queued for processing"
}
```

---

### 3.2 `GET /api/v1/jobs/{job_id}`
Retrieves job status, progress, download links, and manifest.

#### Response (`HTTP 200 OK`):
```json
{
  "job_id": "job_80829c9c7aa6",
  "status": "succeeded",
  "progress": 100,
  "result": {
    "mix_wav": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/mix.wav?...",
    "mix_mp3": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/mix.mp3?...",
    "mix_ducked_wav": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/mix_ducked.wav?...",
    "stems": {
      "drums": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/stems/drums.wav?...",
      "bass": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/stems/bass.wav?...",
      "harmony": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/stems/harmony.wav?...",
      "melody": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/stems/melody.wav?...",
      "vocals": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/stems/vocals.wav?..."
    },
    "manifest": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/music_manifest.json?...",
    "validation_report": "http://localhost:9000/incubrix-audio/job_80829c9c7aa6/validation_report.json?..."
  },
  "manifest": { ... },
  "error": null,
  "created_at": "2026-10-23T12:00:00Z",
  "updated_at": "2026-10-23T12:00:15Z"
}
```

---

### 3.3 `GET /health` & `GET /ready`
- `/health`: Liveness probe (`{"status": "ok"}`).
- `/ready`: Readiness probe verifying PostgreSQL, Redis, and MinIO storage connectivity (`{"status": "ready", "checks": {"database": "ok", "storage": "ok", "redis": "ok"}}`).

---

## 4. Standardized Error Schema

All error responses adhere strictly to the JSON schema:
```json
{
  "error": {
    "code": "UPPER_SNAKE_CASE",
    "message": "Human-readable explanation of error",
    "retryable": false,
    "details": {}
  }
}
```

### Error Catalog:
| Code | HTTP Status | Description | Retryable |
| :--- | :---: | :--- | :---: |
| `INVALID_REQUEST` | 400 | Payload validation failed (e.g., duration < 5s or > 300s). | No |
| `SSRF_BLOCKED` | 400 | Remote URL resolves to internal, private, loopback, or cloud metadata IP. | No |
| `PAYLOAD_TOO_LARGE`| 400 | Downloaded narration audio exceeds 50 MB limit. | No |
| `IDEMPOTENCY_CONFLICT` | 409 | `Idempotency-Key` was previously used with a different request payload. | No |
| `JOB_NOT_FOUND` | 404 | The requested `job_id` does not exist in the database. | No |
| `PROCESSING_FAILED` | 500 | Background audio generation, separation, or DSP error. | Yes |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled server exception. | Yes |

---

## 5. Security, SSRF Prevention & Webhooks

1. **SSRF Mitigation:**
   - Any remote URL passed to `narration_url` or `callback_url` is validated before network dispatch.
   - Hostnames are resolved to IP addresses and verified against private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.169.254`, `::1`). Attempts to target internal addresses are rejected with `SSRF_BLOCKED`.

2. **Webhook HMAC-SHA256 Signing:**
   - When `callback_url` is provided, completion events are dispatched with:
     ```http
     X-IncuBrix-Signature: sha256=<hex_digest>
     ```
   - Calculated using HMAC-SHA256 over the canonical JSON payload with `CALLBACK_SECRET`.

3. **Public Demo Protection & Rate Limiting:**
   - Optional `DEMO_API_KEY` header verification.
   - IP-based rate limiting configured to 60 requests/minute to prevent resource starvation.

---

## 6. CLI Batch Runner

Run the offline batch runner against sample prompts:
```bash
python -m src.cli \
  --prompt "uplifting acoustic instrumental" \
  --duration 30.0 \
  --tempo 120 \
  --key "G major" \
  --output-dir sample_audio_packs/acoustic_30s
```

---

## 7. React + TypeScript Web Dashboard

A modern, dark-themed audio-production web interface for the IncuBrix AI Background Music Engine.

### 7.1 Features
- **Dashboard Overview:** Real-time job metrics (Total, Successful, Failed, Active/Queued), engine health indicator, recent generations table, and one-click production presets.
- **Music Generation Studio:** Full parameter control (prompt, 5–300s duration slider with ±0.05s precision, tempo BPM, musical key, loopable toggle, dynamic video cut points section editor, SSRF-protected narration URL, random seed, sample rate 48k/44.1k, and target LUFS selection).
- **Live Job Polling:** Non-blocking asynchronous progress tracker with 6-stage pipeline visualization, automatic polling, and detailed error handling.
- **Multitrack Audio Studio:** Master mix audio player with canvas waveform, individual multitrack stem mixers (Drums, Bass, Harmony, Melody, Vocals) with solo/mute buttons, voiceover ducked mix bed (-10 dB), and download links for uncompressed 48 kHz WAV files.
- **Manifest Inspector:** Structured tree view of `music_manifest.json` with copyright clearance provenance and 1-click JSON download.
- **Job History:** Real-time database history table with search filtering and direct links to Audio Studio and Manifest views.

### 7.2 Running the Dashboard Locally

```bash
# 1. Start the FastAPI backend server (Port 8000)
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 2. In a separate terminal, navigate to frontend and install dependencies
cd frontend
npm install

# 3. Start Vite development server (Port 3000)
npm run dev

# 4. Open browser at http://localhost:3000
```

### 7.3 Frontend Configuration & Testing

- **Backend API URL:** Configured via `VITE_API_BASE_URL` in `frontend/.env` (defaults to `http://localhost:8000`, with Vite dev server proxying `/api`, `/health`, and `/ready`).
- **Run Unit & Component Tests:**
  ```bash
  cd frontend
  npm test
  ```
- **Run Production Build:**
  ```bash
  cd frontend
  npm run build
  ```

