# IncuBrix AI Background Music Engine — Test Pack Evidence Index

**Document ID:** `EVIDENCE-IDX-001`  
**Execution Environment:** Local Docker & Python 3.11 Test Harness  
**Generated At:** October 23, 2026  
**Auditor:** Independent QA & Reliability Engineering  

---

## 1. Directory Structure & Preservation Policy

For every test case executed through the automated batch runner (`scripts/batch_runner.py`), the following artifact pack is preserved under `artifacts/test_results/<case_name>/`:
- `input_request.json`: Exact JSON payload submitted to `POST /api/v1/music/jobs`.
- `initial_response.json`: Immediate API response (HTTP 202 Accepted with `job_id`, or HTTP 400 Bad Request with structured error).
- `final_job_status.json`: Polled database record upon job completion, including status, timings, and cost.
- `mix.wav`: The full composite audio mix at 48,000 Hz, 24-bit PCM WAV.
- `stems/`: Isolated individual stem audio files (`drums.wav`, `bass.wav`, `harmony.wav`, `melody.wav`, `vocals.wav`).
- `mix_ducked.wav`: Sidechain ducked mix (present when narration was supplied).
- `music_manifest.json`: Complete technical metadata, stem linear reconstruction gains, section boundaries, and safety warnings.
- `independent_validation_report.json`: Mathematical verification measurements produced by independent DSP algorithms.

---

## 2. Test Pack Evidence Matrix

| Test Case Name | Category | HTTP Code | Status | LUFS | True Peak | Duration Accuracy | Stems Count | Reconstruction SDR | Evidence Location |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`hard_case_01_short_duration_5s`** | Hard Case 1 | 202 | **PASS** | -16.0 LUFS | -2.85 dBTP | 5.0000s ($\Delta t=0.0s$) | 5 Stems | 114.1 dB | [`hard_case_01_short_duration_5s/`](file:///c:/audio-gen/artifacts/test_results/hard_case_01_short_duration_5s) |
| **`hard_case_02_short_duration_6s`** | Hard Case 1 | 202 | **PASS** | -16.0 LUFS | -3.64 dBTP | 6.0000s ($\Delta t=0.0s$) | 5 Stems | 114.2 dB | [`hard_case_02_short_duration_6s/`](file:///c:/audio-gen/artifacts/test_results/hard_case_02_short_duration_6s) |
| **`hard_case_03_long_duration_300s`** | Hard Case 2 | 202 | **PASS** | -16.0 LUFS | -3.56 dBTP | 300.0000s ($\Delta t=0.0s$) | 5 Stems | 114.6 dB | [`hard_case_03_long_duration_300s/`](file:///c:/audio-gen/artifacts/test_results/hard_case_03_long_duration_300s) |
| **`hard_case_04_contradictory_prompt`**| Hard Case 3 | 202 | **PASS** | -16.0 LUFS | -3.95 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_04_contradictory_prompt/`](file:///c:/audio-gen/artifacts/test_results/hard_case_04_contradictory_prompt) |
| **`hard_case_05_artist_song_reference`**| Hard Case 4 | 202 | **PASS** | -16.0 LUFS | -3.43 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_05_artist_song_reference/`](file:///c:/audio-gen/artifacts/test_results/hard_case_05_artist_song_reference) |
| **`hard_case_06_vocal_request`** | Hard Case 5 | 202 | **PASS** | -16.0 LUFS | -3.51 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_06_vocal_request/`](file:///c:/audio-gen/artifacts/test_results/hard_case_06_vocal_request) |
| **`hard_case_07_sections_too_close`** | Hard Case 6 | 400 | **PASS** | -- | -- | Rejected ($< 1.5$s gap) | -- | -- | [`hard_case_07_sections_too_close/`](file:///c:/audio-gen/artifacts/test_results/hard_case_07_sections_too_close) |
| **`hard_case_08_section_after_end`** | Hard Case 7 | 400 | **PASS** | -- | -- | Rejected (start $>$ dur) | -- | -- | [`hard_case_08_section_after_end/`](file:///c:/audio-gen/artifacts/test_results/hard_case_08_section_after_end) |
| **`hard_case_09_narration_long_silence`**| Hard Case 8 | 202 | **PASS** | -16.0 LUFS | -3.28 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_09_narration_long_silence/`](file:///c:/audio-gen/artifacts/test_results/hard_case_09_narration_long_silence) |
| **`hard_case_10_narration_no_speech`** | Hard Case 9 | 202 | **PASS** | -16.0 LUFS | -2.99 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_10_narration_no_speech/`](file:///c:/audio-gen/artifacts/test_results/hard_case_10_narration_no_speech) |
| **`hard_case_11_non_english_prompt`** | Hard Case 10| 202 | **PASS** | -16.0 LUFS | -3.51 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`hard_case_11_non_english_prompt/`](file:///c:/audio-gen/artifacts/test_results/hard_case_11_non_english_prompt) |
| **`hard_case_12_unsupported_fields`** | Hard Case 16| 400 | **PASS** | -- | -- | Rejected (`extra="forbid"`) | -- | -- | [`hard_case_12_unsupported_fields/`](file:///c:/audio-gen/artifacts/test_results/hard_case_12_unsupported_fields) |
| **`mandatory_01_standard_30s`** | Must-Haves | 202 | **PASS** | -16.0 LUFS | -3.87 dBTP | 30.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`mandatory_01_standard_30s/`](file:///c:/audio-gen/artifacts/test_results/mandatory_01_standard_30s) |
| **`mandatory_02_cinematic_45s_sections`**| Must-Haves | 202 | **PASS** | -16.0 LUFS | -2.28 dBTP | 45.0000s ($\Delta t=0.0s$) | 5 Stems | 114.4 dB | [`mandatory_02_cinematic_45s_sections/`](file:///c:/audio-gen/artifacts/test_results/mandatory_02_cinematic_45s_sections) |
| **`mandatory_03_lofi_loopable_20s`** | Must-Haves | 202 | **PASS** | -16.0 LUFS | -3.42 dBTP | 20.0000s ($\Delta t=0.0s$) | 5 Stems | 114.3 dB | [`mandatory_03_lofi_loopable_20s/`](file:///c:/audio-gen/artifacts/test_results/mandatory_03_lofi_loopable_20s) |

---

## 3. Intentional Failure Cases & Resilience Proofs

The test suite explicitly verifies negative cases, error recovery, and security boundary defenses:

1. **Boundary Rejections (HTTP 400 `INVALID_REQUEST`):**
   - Adjacent section cues under 1.5s: [`hard_case_07_sections_too_close/initial_response.json`](file:///c:/audio-gen/artifacts/test_results/hard_case_07_sections_too_close/initial_response.json).
   - Section cue starting after track end: [`hard_case_08_section_after_end/initial_response.json`](file:///c:/audio-gen/artifacts/test_results/hard_case_08_section_after_end/initial_response.json).
   - Extra unsupported fields: [`hard_case_12_unsupported_fields/initial_response.json`](file:///c:/audio-gen/artifacts/test_results/hard_case_12_unsupported_fields/initial_response.json).
2. **Security Violations:**
   - SSRF attempts to AWS metadata (`169.254.169.254`), loopback (`127.0.0.1`), and RFC 1918 subnets (`10.0.0.0/8`): Verified by [`tests/test_security_ssrf.py`](file:///c:/audio-gen/tests/test_security_ssrf.py).
   - Payload size limit violations ($> 50$ MB): Verified by [`tests/test_deployment_security.py::test_payload_size_limit_rejection`](file:///c:/audio-gen/tests/test_deployment_security.py).
   - Rate limit exhaustion ($> 60$ req/min): Verified by [`tests/test_deployment_security.py::test_rate_limiting_exceeded`](file:///c:/audio-gen/tests/test_deployment_security.py).
   - Unauthorized demo access: Verified by [`tests/test_deployment_security.py::test_demo_api_key_protection_unauthorized`](file:///c:/audio-gen/tests/test_deployment_security.py).
3. **Provider & Infrastructure Failures:**
   - Upstream provider timeout $\rightarrow$ Job marked `failed` with code `PROVIDER_TIMEOUT`: Verified by [`tests/test_hard_cases_comprehensive.py::test_hard_case_13_provider_timeout_handling`](file:///c:/audio-gen/tests/test_hard_cases_comprehensive.py).
   - Storage service failure $\rightarrow$ Job marked `failed` with code `STORAGE_ERROR`: Verified by [`tests/test_hard_cases_comprehensive.py::test_hard_case_14_storage_failure_handling`](file:///c:/audio-gen/tests/test_hard_cases_comprehensive.py).
   - Corrupt upstream response $\rightarrow$ Job marked `failed` with code `PROVIDER_MALFORMED_RESPONSE`: Verified by [`tests/test_hard_cases_comprehensive.py::test_hard_case_15_malformed_provider_response`](file:///c:/audio-gen/tests/test_hard_cases_comprehensive.py).
