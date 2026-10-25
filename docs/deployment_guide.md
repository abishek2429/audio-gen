# IncuBrix AI Background Music Engine — Deployment & Production Guide

**Document Version:** 1.0.0  
**Target Environment:** Local Docker Compose / Managed Cloud (Render / AWS ECS)  
**Security Standard:** Demo API Protection, Rate Limiting, Request Size Caps, Safe Error Responses  

---

## 1. Architecture Overview & Deployment Justification

The **IncuBrix AI Background Music Engine** is a heavy digital signal processing (DSP) and multitrack audio generation system. 

> [!IMPORTANT]
> **Why a static frontend host is insufficient:**  
> Generating video background music requires asynchronous task dispatch, multi-minute audio synthesis, FFmpeg stem alignment, ITU-R BS.1770-4 loudness compliance filtering, sidechain sideband ducking, and ACID job state tracking. A static frontend host (e.g. Vercel, Netlify) can only host static JavaScript assets; the backend requires persistent compute, PostgreSQL, Redis, and S3-compatible object storage.

```
+-------------------------------------------------------------------------------+
|                             CLIENT / BROWSER                                  |
|     React + TypeScript Dashboard (Port 3000) or Video Production Pipeline     |
+-------------------------------------------------------------------------------+
                                      |
                         (REST API / Reverse Proxy)
                                      v
+-------------------------------------------------------------------------------+
|                       API GATEWAY (FastAPI / Port 8000)                       |
|   * Rate Limiting (60 req/min)             * Request Size Limits (50 MB)      |
|   * Demo Access Protection (DEMO_API_KEY)  * Structured Errors (RFC 7807)     |
|   * Idempotency Enforcement                * Health & Readiness Probes        |
+-------------------------------------------------------------------------------+
         |                                           |                   |
         v (State & Metadata)                        v (Task Dispatch)   v (Storage)
+-----------------------+              +-----------------------+   +-------------------+
|  PostgreSQL 16 Engine |              |     Redis 7 Broker    |   |  MinIO / AWS S3   |
|   (ACID Job State)    |              |  (Celery Queue/Cache) |   |  (Mix & Stems)    |
+-----------------------+              +-----------------------+   +-------------------+
                                                     |
                                                     v (Consume Tasks)
                                       +-----------------------------------------------+
                                       |       BACKGROUND WORKER (Celery / FFmpeg)     |
                                       |   * Music Synthesis (Soundverse/ElevenLabs)   |
                                       |   * Multitrack Stem Separation                |
                                       |   * 48 kHz / 24-bit PCM WAV Alignment         |
                                       |   * Dual-pass Loudness & Brickwall Limiting   |
                                       |   * Voiceover Sidechain Ducking               |
                                       +-----------------------------------------------+
```

---

## 2. Local Containerized Startup (One-Command Launch)

The entire multi-container environment starts with a single command:

```bash
docker compose up --build
```

### Services Started & Port Mappings

| Service Name | Container Name | Host Port | Internal Port | Healthcheck Mechanism |
| :--- | :--- | :---: | :---: | :--- |
| **`frontend`** | `incubrix_frontend` | `3000` | `80` | `wget -q -O /dev/null http://localhost/` |
| **`api`** | `incubrix_api` | `8000` | `8000` | `curl -f http://localhost:8000/health` |
| **`worker`** | `incubrix_worker` | -- | -- | Celery ping via Redis broker |
| **`db`** | `incubrix_postgres` | `5433` | `5432` | `pg_isready -U postgres` |
| **`redis`** | `incubrix_redis` | `6379` | `6379` | `redis-cli ping` |
| **`minio`** | `incubrix_minio` | `9000` / `9001` | `9000` / `9001` | `curl -f http://localhost:9000/minio/health/live` |

### Service Dependency Ordering
Containers use Docker Compose `service_healthy` conditions:
1. `db`, `redis`, and `minio` start and pass their health checks.
2. `api` starts database schema migration (`alembic upgrade head`) and launches FastAPI once dependencies are healthy.
3. `worker` launches Celery worker processes once `api` and brokers are healthy.
4. `frontend` starts Nginx once `api` is healthy.

---

## 3. Configuration Management & Environment Variables

All settings are read from environment variables or `.env` via Pydantic Settings ([`src/config.py`](file:///c:/audio-gen/src/config.py)).

A template is provided in [`.env.example`](file:///c:/audio-gen/.env.example):

```bash
cp .env.example .env
```

### Key Configuration Groups

| Setting Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MUSIC_PROVIDER` | `mock` | Active provider: `mock`, `soundverse`, or `elevenlabs` |
| `SOUNDVERSE_API_KEY` | *(None)* | API key for primary provider Soundverse Enterprise |
| `ELEVENLABS_API_KEY` | *(None)* | API key for fallback provider ElevenLabs Music |
| `DATABASE_URL` | `sqlite:///./incubrix.db` | PostgreSQL in Docker; SQLite for local unit tests |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis task broker and sliding-window rate limit store |
| `CELERY_ENABLED` | `false` | When `true`, delegates jobs to Celery; when `false`, runs local worker |
| `STORAGE_BACKEND` | `local` | `minio` for S3 bucket storage; `local` for filesystem |
| `DEMO_API_KEY` | *(Empty)* | Optional demo protection key; if set, requires `X-API-Key` on `/api/` |
| `RATE_LIMIT_PER_MINUTE`| `60` | Max requests per minute per IP address (0 disables limit) |
| `MAX_UPLOAD_SIZE_BYTES`| `52428800` (50MB) | Enforced request body cap; returns HTTP 413 if exceeded |
| `DEFAULT_SAMPLE_RATE` | `48000` | Mandatory sample rate standard for video production |
| `TARGET_LUFS` | `-16.0` | Default ITU-R BS.1770-4 loudness target |
| `TARGET_TRUE_PEAK_DBTP`| `-1.0` | Mandatory True Peak ceiling |

---

## 4. Production Security & Access Protection

The engine implements four layers of defense-in-depth:

### 1. Demo Access Protection (`DEMO_API_KEY`)
- When `DEMO_API_KEY` is configured in production, unauthenticated requests to `/api/` are rejected with HTTP 401 Unauthorized:
  ```json
  {
    "error": {
      "code": "UNAUTHORIZED",
      "message": "Demo authentication required. Provide valid API key in 'X-API-Key' or 'Authorization: Bearer <key>'.",
      "retryable": false,
      "details": {}
    }
  }
  ```
- Public operational endpoints (`/health`, `/ready`, `/docs`, `/openapi.json`) remain accessible for load balancers.

### 2. Sliding-Window Rate Limiting
- Configurable via `RATE_LIMIT_PER_MINUTE`.
- Tracks client IP in a 60-second sliding window.
- Excess requests receive HTTP 429 Too Many Requests with `Retry-After: 60` header and structured JSON error code `RATE_LIMIT_EXCEEDED`.

### 3. Request Size Enforcement
- Enforces `MAX_UPLOAD_SIZE_BYTES` (50 MB).
- Requests declaring `Content-Length` greater than 50 MB are halted before socket ingestion with HTTP 413 `PAYLOAD_TOO_LARGE`.

### 4. Server-Side Request Forgery (SSRF) Blocklist
- Validates all remote narration and webhook URLs via DNS resolution prior to connection.
- Explicitly blocks RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local metadata endpoints (`169.254.169.254`), and non-HTTP protocols (`file://`, `ftp://`).

---

## 5. Status of Publicly Reachable Demo URL

In compliance with the project rule:
> *"Never invent a deployed URL. If deployment credentials and infrastructure are not available, prepare deployment configuration and document exactly what remains to be done."*

### Current Deployment Status
- **Live Cloud Credentials:** Not configured in the review environment (no AWS, Render, Railway, or Fly.io API tokens were provided).
- **Public URL Status:** **Not provisioned.**
- **Deployment Infrastructure-as-Code:** Fully prepared in [`render.yaml`](file:///c:/audio-gen/render.yaml) and [`docker-compose.yml`](file:///c:/audio-gen/docker-compose.yml).

### Exact Remaining Steps to Deploy Publicly (3 Steps)

1. **Option A — One-Click Render Deployment (Recommended):**
   - Connect the repository to [Render](https://render.com).
   - Select **New + -> Blueprint** and point to `render.yaml`.
   - Set secrets in Render Dashboard:
     - `SOUNDVERSE_API_KEY`
     - `DEMO_API_KEY`
   - Render automatically provisions the PostgreSQL database, Redis broker, FastAPI service, and Celery worker with automated SSL certificates (`https://<app>.onrender.com`).

2. **Option B — AWS ECS / Fargate Deployment:**
   - Push backend image to AWS ECR: `docker build -t <account>.dkr.ecr.<region>.amazonaws.com/incubrix-engine:latest .`
   - Create ECS Task Definition mapping API container (port 8000) and Worker container to AWS RDS PostgreSQL and AWS ElastiCache Redis.
   - Attach Application Load Balancer (ALB) with ACM HTTPS certificate.

3. **Option C — Vercel Fullstack Deployment (Vite Studio + Serverless Functions):**
   - Connect the repository to [Vercel](https://vercel.com).
   - Vercel automatically detects `vercel.json` and root `package.json`.
   - The React audio workstation builds via `npm run build` into `frontend/dist`.
   - The FastAPI backend runs via `api/index.py` serverless functions with `excludeFiles` to ensure the Lambda bundle remains ~226 MB (well within the 500 MB limit).
   - Configure environment variables in Vercel Dashboard (e.g. `DATABASE_URL`, `STORAGE_BACKEND`, `SOUNDVERSE_API_KEY`).
