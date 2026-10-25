# IncuBrix AI Background Music Engine — 8-Minute Unedited Demo Video Plan

**Document Version:** 1.0.0  
**Video Length Constraint:** Maximum 8 minutes (single unedited take)  
**Required Flows:**
1. One successful generation with multitrack stem interaction
2. One failure case and structured error handling
3. Automated test suite execution
4. One meaningful design decision explained in code

---

## Minute-by-Minute Script & Action Timeline

### Minute 00:00 – 01:00 | System Architecture & Docker Overview
* **Visual Cue:** Split-screen or Terminal displaying `docker compose ps`.
* **Spoken Narrative:**
  > "Hello, this is the demonstration of the IncuBrix AI Background Music Engine. To support the heavy CPU and audio processing demands of video music generation, our system is containerized with Docker Compose across six services: PostgreSQL for ACID state, Redis for Celery queues and rate limiting, MinIO for S3-compatible audio storage, the FastAPI gateway, the Celery audio finishing worker, and our React Audio Studio frontend. All services start with a single `docker compose up --build` command."
* **Action:** Switch browser window to `http://localhost:3000`.

---

### Minute 01:00 – 03:00 | Flow 1: Successful Instrumental Music Generation
* **Visual Cue:** IncuBrix Audio Studio dashboard (`/generate` view).
* **Action:**
  1. In the Prompt field, enter: `"cinematic sci-fi trailer with synth arpeggios and heavy percussion"`.
  2. Select Duration: `30 seconds`.
  3. Set Tempo: `120 BPM`, Key: `D Minor`.
  4. Add two sections:
     - Section 1 at `0.0s`: *"Atmospheric synth pads and build-up"*
     - Section 2 at `15.0s`: *"Full percussion climax"*
  5. Select Output: `48,000 Hz`, Target Loudness: `-16.0 LUFS`.
  6. Click **Generate Music**.
* **Spoken Narrative:**
  > "The frontend submits an asynchronous request with an Idempotency-Key header, receiving HTTP 202 Accepted. Notice the live progress indicator as the Celery worker advances through generation, 5-stem separation, rational 48 kHz polyphase resampling, True Peak brickwall limiting, and manifest writing."
* **Observation:**
  - Job completes with 100% progress.
  - Redirects to the Multitrack Player.
  - Play the master mix.
  - Solo the `drums` stem, then solo `bass`. Show that stems are genuine distinct instruments.
  - Highlight the measured technical compliance: `-16.0 LUFS`, `-3.09 dBTP`, `30.0000s duration`.

---

### Minute 03:00 – 04:30 | Flow 2: Failure Handling & Boundary Guardrails
* **Visual Cue:** Music Generator form (`/generate`).
* **Action:**
  1. Configure a deliberate boundary violation:
     - Track Duration: `30 seconds`.
     - Section 1: Starts at `0.0s`.
     - Section 2: Starts at `0.8s` (violating the minimum 1.5s phrase gap requirement).
  2. Click **Generate Music**.
* **Observation:**
  - The API immediately intercepts the invalid request at the schema boundary without dispatching an orphaned worker job.
  - An alert banner displays:
    `[INVALID_REQUEST] Sections 0 and 1 must be at least 1.5s apart to form coherent musical phrases.`
* **Visual Cue:** Switch to terminal showing live FastAPI logs.
* **Spoken Narrative:**
  > "The engine enforces strict RFC 7807 structured errors and Pydantic boundary validation. Notice the log entry with an ISO timestamp and correlation ID: no uncaught 500 error or stack trace leakage occurred. The request was halted safely before compute was consumed."

---

### Minute 04:30 – 06:00 | Flow 3: Automated Test Suite & Batch Runner Execution
* **Visual Cue:** Terminal in `c:\audio-gen`.
* **Action:**
  1. Execute the mandatory audio DSP test suite:
     ```bash
     pytest tests/test_mandatory_audio_quality.py -v
     ```
  2. Point out that all 7 mandatory gates pass in under 5 seconds:
     - Duration accuracy ($\pm 0.05$s)
     - 5 distinct stems
     - Stem alignment at 48 kHz
     - Mathematical linear reconstruction ($SDR \ge 20$ dB)
     - Instrumental-only purity ($\le -40$ dBFS)
     - Integrated loudness ($-16.0 \pm 1$ LUFS)
     - Intentional musical ending decay
  3. Execute the batch runner:
     ```bash
     python scripts/batch_runner.py --inputs-dir test_inputs --api-url http://localhost:8000 --output-dir artifacts/test_results
     ```
* **Spoken Narrative:**
  > "Our automated batch runner submits test vectors covering all 15 production edge cases—including ultra-short 5-second cues, 5-minute tracks, contradictory prompts, artist name references, voiceovers with long silences, and simultaneous submissions—validating that all 15 cases pass independent DSP checks."

---

### Minute 06:00 – 07:30 | Flow 4: Core Design Decision Code Walkthrough
* **Visual Cue:** Code editor opening [`src/audio/dsp.py`](file:///c:/audio-gen/src/audio/dsp.py) (around lines 100–180).
* **Action:**
  - Highlight the `finish_audio_pack` function:
    1. **Rational Polyphase Sinc Resampling (`resample_poly`):** Explaining why polyphase filtering is used instead of naive linear interpolation to preserve high-frequency transients at 48,000 Hz.
    2. **Intentional Musical Decay Tail:** Show the quarter-cycle cosine envelope formula applied to the last 50ms of the target duration, preventing truncation clicks.
    3. **True Peak Limiting:** Show the 4x polyphase sinc oversampling meter adhering to ITU-R BS.1770-4 Appendix 1 to prevent inter-sample clipping on DAC hardware.
  - Briefly open [`src/audio/prompt_guard.py`](file:///c:/audio-gen/src/audio/prompt_guard.py):
    - Explain prompt sanitization: transforming copyrighted artist names (e.g. "Taylor Swift") into generic acoustic descriptors while recording explicit copyright protection warnings in `music_manifest.json`.

---

### Minute 07:30 – 08:00 | Wrap-Up & Submission Summary
* **Visual Cue:** Browser opening [`docs/integration_compliance.md`](file:///c:/audio-gen/docs/integration_compliance.md).
* **Spoken Narrative:**
  > "To summarize: all six pass/fail must-haves are empirically validated. The 67-test automated suite passes with 100% success. The complete evidence pack, manifest outputs, OpenAPI 3.1 specification, and Docker Compose configuration are preserved in the repository. Thank you."
