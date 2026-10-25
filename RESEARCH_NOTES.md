# IncuBrix AI Background Music Engine — Research Notes

## Project objective

Build a Python-based, containerized API service with a React web dashboard that generates original instrumental background music for videos. The system must deliver an exactly timed final mix and at least three genuine, separate instrument stems.

The IncuBrix AI Audio Engine engineering specification is the source of truth for all requirements.

## Preferred technology stack

- Python 3.11 or a compatible version supported by all selected dependencies
- FastAPI and Pydantic
- PostgreSQL
- Redis and Celery for background jobs
- FFmpeg and Python audio-processing libraries
- MinIO for S3-compatible object storage
- React and TypeScript for the dashboard
- Docker Compose for local development and testing
- OpenAPI 3.1 for API documentation
- Pytest for automated testing

Confirm version compatibility before pinning dependencies.

## AI provider candidates

### Candidate A: Eleven Music API
Official product page: https://elevenlabs.io/eleven-music-api

Investigate:
- Music-generation API access and pricing
- Instrumental generation
- Duration and section controls
- Supported output formats and sample rates
- Commercial rights for the intended use
- Whether a separate stem provider is required

### Candidate B: Soundverse
Official documentation:
- https://platform.soundverse.ai/docs/music-generation
- https://platform.soundverse.ai/docs/stem-separation

Investigate:
- Music generation and six-stem separation
- Exact API request and response schemas
- Actual duration and output formats
- Published pricing and applicable commercial-use rights
- Reconstruction quality and instrument separation quality

### Candidate C: Stable Audio
Investigate only as an alternative if the first candidates do not satisfy the requirements.

### Local fallback
Investigate Demucs and compatible alternatives, including the exact licences of model weights and dependencies. Do not assume that an open-source code licence automatically grants commercial rights to every pretrained model.

These candidates are not yet approved for production. Verify current official documentation and terms. Never fabricate API endpoints, parameters, prices, licence permissions, or test results.

## Mandatory output requirements

- mix.wav and mix.mp3 where requested
- At least three genuine, distinct instrument stems
- All stems aligned to the mix in duration and sample rate
- Mix reconstructable from stems using documented gains
- Instrumental-only output
- 48 kHz WAV output
- Default integrated loudness target: -16 LUFS, within 1 LU
- True peak at or below -1 dBTP
- Requested duration accuracy within 0.05 seconds
- Intentional musical ending rather than an abrupt cut
- music_manifest.json with actual model/provider versions, settings, seed, timings, gains, costs, warnings, and licensing information
- mix_ducked.wav when narration is provided and ducking succeeds

## API requirements

POST /api/v1/music/jobs  
GET /api/v1/jobs/{job_id}  
GET /health  
GET /ready

Use HTTP 202 for accepted asynchronous jobs. Job statuses: queued, running, succeeded, failed. Support Idempotency-Key on every POST. Return structured JSON errors with code, message, retryable, and details. Use X-Correlation-Id in structured logs.

Support prompt, duration_s, sections, tempo_bpm, key, loopable, narration_url, seed, and output settings.

## Engineering constraints

- Provider adapters must be replaceable through configuration.
- Include a mock provider so tests run without API keys.
- Never hard-code secrets, paths, provider credentials, or environment-specific URLs.
- Validate remote URLs and restrict access to private/internal network addresses to mitigate SSRF.
- Avoid retrying non-idempotent provider operations blindly.
- Do not claim a capability works until an automated test or recorded manual measurement proves it.
- Record failed and weak results in the test pack.
- Verify licences before selecting the production default.

## Initial priorities

1. Research and verify provider capabilities.
2. Prove music generation and genuine stem separation with actual audio.
3. Measure reconstruction, duration, sample rate, loudness, and true peak.
4. Implement the backend and automated tests.
5. Build the dashboard.
6. Deploy, test hard cases, and finalize production verification.

The engineering specification takes precedence over these notes if any conflict exists.