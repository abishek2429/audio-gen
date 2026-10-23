"""Comprehensive automated test suite for all 15 IncuBrix Hard Cases.

Covers:
1. Short durations (5-6s)
2. Long durations (300s / 5 minutes)
3. Contradictory prompts ('calm but aggressive')
4. Real artist & song references (copyright protection)
5. Prompts requesting vocals (instrumental policy)
6. Sections < 1.5s apart (boundary validation)
7. Sections starting after track end (boundary validation)
8. Narration with long silences (sidechain ducking behavior)
9. Narration with no speech (sidechain bypass)
10. Non-English prompts (multilingual normalization)
11. Simultaneous concurrent submissions (race conditions)
12. Duplicate Idempotency-Key requests (idempotency safety)
13. Provider timeout or failure (resilience)
14. Storage failure (resilience)
15. Malformed provider responses (resilience)
16. Unsupported extra fields (strict schema compliance)
"""
import io
import json
import time
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from src.main import create_app
from src.models import MusicJobRequest, OutputConfig, SectionPlan
from src.audio.prompt_guard import analyze_and_guard_prompt
from src.audio.dsp import apply_voiceover_ducking
from src.providers.base import ProviderTimeoutException, ProviderMalformedResponseException
from src.storage import StorageException
from src.database.session import get_db, SessionLocal
from src.database.models import MusicJob


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


# -------------------------------------------------------------
# Hard Case 1: Durations of 5-6 seconds
# -------------------------------------------------------------
def test_hard_case_01_short_duration_5s_and_6s(client):
    """Verify system accepts and processes short tracks (5.0s and 6.0s) accurately."""
    for dur in (5.0, 6.0):
        resp = client.post(
            "/api/v1/music/jobs",
            json={"prompt": "crisp podcast bumper", "duration_s": dur},
            headers={"Idempotency-Key": f"test-short-{dur}-{time.time()}"},
        )
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        # Poll to completion
        for _ in range(30):
            time.sleep(0.1)
            get_resp = client.get(f"/api/v1/jobs/{job_id}")
            if get_resp.json()["status"] == "succeeded":
                break

        res = get_resp.json()
        assert res["status"] == "succeeded"
        actual_dur = res["manifest"]["actual_duration_s"]
        assert abs(actual_dur - dur) <= 0.05, f"Short duration {actual_dur} not within 0.05s of {dur}s"


# -------------------------------------------------------------
# Hard Case 2: Five-minute requests (300 seconds)
# -------------------------------------------------------------
def test_hard_case_02_long_duration_300s(client):
    """Verify system accepts 300s request and validates boundaries."""
    req = MusicJobRequest(
        prompt="long documentary ambient soundscape",
        duration_s=300.0,
    )
    assert req.duration_s == 300.0

    # Over 300s must be rejected
    with pytest.raises(Exception):
        MusicJobRequest(prompt="too long", duration_s=300.1)


# -------------------------------------------------------------
# Hard Case 3: Vague or Contradictory Prompts
# -------------------------------------------------------------
def test_hard_case_03_contradictory_prompt():
    """Verify contradictory polarities ('calm but aggressive') emit dynamic contrast warning."""
    analysis = analyze_and_guard_prompt("calm but aggressive corporate video track")
    assert len(analysis.detected_contradictions) >= 1
    assert any("contradictory" in w.lower() for w in analysis.warnings)
    assert any("dynamic contrast" in w.lower() for w in analysis.warnings)


# -------------------------------------------------------------
# Hard Case 4: Real Artist & Song References (Copyright Protection)
# -------------------------------------------------------------
def test_hard_case_04_artist_and_song_references():
    """Verify named artists/songs trigger copyright guardrails, prompt rewriting, and warnings."""
    prompt = "in the style of Taylor Swift - Shake It Off with bright pop guitars"
    analysis = analyze_and_guard_prompt(prompt)

    assert analysis.copyright_protected is True
    assert "taylor swift" in analysis.detected_artists
    # Transformed prompt must avoid direct imitation directive
    assert "taylor swift" not in analysis.effective_prompt.lower()
    assert any("copyright" in w.lower() or "artist reference" in w.lower() for w in analysis.warnings)


# -------------------------------------------------------------
# Hard Case 5: Prompts Requesting Vocals (Instrumental Policy)
# -------------------------------------------------------------
def test_hard_case_05_vocal_request_suppression():
    """Verify prompts asking for vocals are suppressed to instrumental with explicit warning."""
    prompt = "acoustic song with singing female vocals and lyrics"
    analysis = analyze_and_guard_prompt(prompt)

    assert analysis.instrumental_enforced is True
    assert any("vocals" in v.lower() for v in analysis.detected_vocal_requests)
    assert any("instrumental-only" in w.lower() for w in analysis.warnings)


# -------------------------------------------------------------
# Hard Case 6: Sections Less Than 1.5 Seconds Apart
# -------------------------------------------------------------
def test_hard_case_06_sections_less_than_1_5s_apart(client):
    """Verify sections less than 1.5s apart are rejected with structured HTTP 400 error."""
    resp = client.post(
        "/api/v1/music/jobs",
        json={
            "prompt": "rapid section shifts",
            "duration_s": 20.0,
            "sections": [
                {"start_s": 0.0, "mood": "intro"},
                {"start_s": 2.0, "mood": "buildup"},
                {"start_s": 2.8, "mood": "too close"},  # Gap = 0.8s < 1.5s
            ],
        },
    )
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "INVALID_REQUEST"
    assert "1.5 seconds apart" in json.dumps(err["details"])


# -------------------------------------------------------------
# Hard Case 7: Sections Beginning After Track End
# -------------------------------------------------------------
def test_hard_case_07_section_after_track_end(client):
    """Verify section starting after track duration is rejected with structured HTTP 400 error."""
    resp = client.post(
        "/api/v1/music/jobs",
        json={
            "prompt": "cinematic piece",
            "duration_s": 15.0,
            "sections": [
                {"start_s": 0.0, "mood": "intro"},
                {"start_s": 20.0, "mood": "out of bounds"},  # 20.0s > 15.0s
            ],
        },
    )
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "INVALID_REQUEST"
    assert "begins after requested track duration" in json.dumps(err["details"])


# -------------------------------------------------------------
# Hard Case 8: Narration Containing Long Silences
# -------------------------------------------------------------
def test_hard_case_08_narration_with_long_silences():
    """Verify sidechain ducking smoothly restores volume during extended narration pauses."""
    sr = 48000
    duration_s = 20.0
    n_samples = int(duration_s * sr)

    music = np.full((n_samples, 2), 0.5)

    # Speech active 0-3s, silence 3-15s (12s silence), speech 15-18s
    speech = np.zeros((n_samples, 2))
    speech[: int(3 * sr), :] = 0.8
    speech[int(15 * sr) : int(18 * sr), :] = 0.8

    ducked, gain_curve = apply_voiceover_ducking(music, speech, sr=sr, ducking_db=10.0)

    # During speech (1s): gain should be ducked (-10 dB ~= 0.316)
    assert gain_curve[int(1.0 * sr)] < 0.4
    # During long pause (8s): gain should be fully restored to 1.0 (no pumping)
    assert gain_curve[int(8.0 * sr)] >= 0.95
    # During speech resumption (16s): gain should be ducked again
    assert gain_curve[int(16.0 * sr)] < 0.4


# -------------------------------------------------------------
# Hard Case 9: Narration Containing No Speech
# -------------------------------------------------------------
def test_hard_case_09_narration_with_no_speech():
    """Verify ducking envelope remains at 1.0 when narration contains only silence / room tone."""
    sr = 48000
    duration_s = 10.0
    n_samples = int(duration_s * sr)

    music = np.full((n_samples, 2), 0.5)
    silent_speech = np.full((n_samples, 2), 1e-5)  # -100 dBFS room noise

    ducked, gain_curve = apply_voiceover_ducking(music, silent_speech, sr=sr, ducking_db=10.0)

    # Gain curve must remain 1.0 across the entire duration
    assert np.all(gain_curve >= 0.99)
    assert np.allclose(ducked, music, atol=1e-3)


# -------------------------------------------------------------
# Hard Case 10: Non-English Prompts
# -------------------------------------------------------------
def test_hard_case_10_non_english_prompts():
    """Verify international prompts (Spanish, French, German) are detected and normalized."""
    prompts = [
        ("música alegre para video con guitarra", "ES"),
        ("musique de fond calme et joyeuse pour vidéo", "FR"),
        ("ruhige hintergrundmusik für video", "DE"),
    ]

    for p, expected_lang in prompts:
        analysis = analyze_and_guard_prompt(p)
        assert analysis.detected_language == expected_lang.lower()
        assert any("non-english" in w.lower() for w in analysis.warnings)


# -------------------------------------------------------------
# Hard Case 11: Simultaneous Job Submissions
# -------------------------------------------------------------
def test_hard_case_11_simultaneous_job_submissions(client):
    """Verify multiple concurrent submissions receive distinct job IDs without collisions."""
    import concurrent.futures

    def submit_one(i):
        return client.post(
            "/api/v1/music/jobs",
            json={"prompt": f"concurrent test track {i}", "duration_s": 10.0},
            headers={"Idempotency-Key": f"concurrent-{i}-{time.time()}"},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(submit_one, i) for i in range(5)]
        responses = [f.result() for f in futures]

    job_ids = [r.json()["job_id"] for r in responses if r.status_code == 202]
    assert len(job_ids) == 5
    assert len(set(job_ids)) == 5, "Duplicate job ID detected in concurrent submissions"


# -------------------------------------------------------------
# Hard Case 12: Duplicate Requests with Same Idempotency-Key
# -------------------------------------------------------------
def test_hard_case_12_idempotency_duplicate_and_conflict(client):
    """Verify identical request returns existing job, differing request returns HTTP 409."""
    key = f"idemp-test-flow-{time.time()}"
    payload1 = {"prompt": "optimistic acoustic pop", "duration_s": 15.0}
    payload2 = {"prompt": "different prompt completely", "duration_s": 25.0}

    # Initial submission
    r1 = client.post("/api/v1/music/jobs", json=payload1, headers={"Idempotency-Key": key})
    assert r1.status_code == 202
    job_id_1 = r1.json()["job_id"]

    # Safe retry (identical payload)
    r2 = client.post("/api/v1/music/jobs", json=payload1, headers={"Idempotency-Key": key})
    assert r2.status_code == 202
    assert r2.json()["job_id"] == job_id_1

    # Conflict (different payload with same key)
    r3 = client.post("/api/v1/music/jobs", json=payload2, headers={"Idempotency-Key": key})
    assert r3.status_code == 409
    assert r3.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


# -------------------------------------------------------------
# Hard Case 13: Provider Timeout or Failure
# -------------------------------------------------------------
def test_hard_case_13_provider_timeout_handling():
    """Verify provider timeout error code is properly classified."""
    from src.tasks.job_worker import execute_job_pipeline

    with patch("src.tasks.job_worker.get_provider") as mock_get_prov:
        mock_prov = MagicMock()
        mock_prov.generate_music.side_effect = ProviderTimeoutException("Upstream music generation timed out after 30s")
        mock_get_prov.return_value = mock_prov

    job_id = f"timeout_{int(time.time() * 1000)}"
    with patch("src.tasks.job_worker.get_provider") as mock_get_prov:
        mock_prov = MagicMock()
        mock_prov.generate_music.side_effect = ProviderTimeoutException("Upstream music generation timed out after 30s")
        mock_get_prov.return_value = mock_prov

        with SessionLocal() as db:
            job = MusicJob(
                id=job_id,
                idempotency_key=f"idemp-{job_id}",
                request_hash="hash1",
                prompt="test timeout",
                duration_s=10.0,
                status="queued",
                progress=0,
                request_json=json.dumps({"prompt": "test timeout", "duration_s": 10.0}),
            )
            db.add(job)
            db.commit()

        execute_job_pipeline(job_id)

        with SessionLocal() as db:
            updated = db.query(MusicJob).filter(MusicJob.id == job_id).first()
            assert updated.status == "failed"
            assert updated.error_code == "PROVIDER_TIMEOUT"


# -------------------------------------------------------------
# Hard Case 14: Storage Failure Handling
# -------------------------------------------------------------
def test_hard_case_14_storage_failure_handling():
    """Verify storage failure is properly classified as STORAGE_ERROR."""
    from src.tasks.job_worker import execute_job_pipeline

    job_id = f"storage_{int(time.time() * 1000)}"
    with patch("src.tasks.job_worker.get_storage_service") as mock_storage_factory:
        mock_storage = MagicMock()
        mock_storage.upload_file.side_effect = StorageException("Disk full or S3 connection refused")
        mock_storage_factory.return_value = mock_storage

        with SessionLocal() as db:
            job = MusicJob(
                id=job_id,
                idempotency_key=f"idemp-{job_id}",
                request_hash="hash2",
                prompt="test storage",
                duration_s=10.0,
                status="queued",
                progress=0,
                request_json=json.dumps({"prompt": "test storage", "duration_s": 10.0}),
            )
            db.add(job)
            db.commit()

        execute_job_pipeline(job_id)

        with SessionLocal() as db:
            updated = db.query(MusicJob).filter(MusicJob.id == job_id).first()
            assert updated.status == "failed"
            assert updated.error_code == "STORAGE_ERROR"


# -------------------------------------------------------------
# Hard Case 15: Malformed Provider Responses
# -------------------------------------------------------------
def test_hard_case_15_malformed_provider_response():
    """Verify corrupt/malformed provider response is caught as PROVIDER_MALFORMED_RESPONSE."""
    from src.tasks.job_worker import execute_job_pipeline

    job_id = f"malformed_{int(time.time() * 1000)}"
    with patch("src.tasks.job_worker.get_provider") as mock_get_prov:
        mock_prov = MagicMock()
        mock_prov.generate_music.side_effect = ProviderMalformedResponseException("Corrupt audio header returned by provider")
        mock_get_prov.return_value = mock_prov

        with SessionLocal() as db:
            job = MusicJob(
                id=job_id,
                idempotency_key=f"idemp-{job_id}",
                request_hash="hash3",
                prompt="test malformed",
                duration_s=10.0,
                status="queued",
                progress=0,
                request_json=json.dumps({"prompt": "test malformed", "duration_s": 10.0}),
            )
            db.add(job)
            db.commit()

        execute_job_pipeline(job_id)

        with SessionLocal() as db:
            updated = db.query(MusicJob).filter(MusicJob.id == job_id).first()
            assert updated.status == "failed"
            assert updated.error_code == "PROVIDER_MALFORMED_RESPONSE"


# -------------------------------------------------------------
# Extra: Strict Schema Validation (No Silent Ignoring of Unsupported Fields)
# -------------------------------------------------------------
def test_hard_case_extra_unsupported_fields_rejected(client):
    """Verify requests with unsupported fields are rejected with HTTP 400 instead of silently ignored."""
    resp = client.post(
        "/api/v1/music/jobs",
        json={
            "prompt": "test unsupported property",
            "duration_s": 15.0,
            "unsupported_extra_property": "should_be_forbidden",
        },
    )
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "INVALID_REQUEST"
    assert "extra" in json.dumps(err["details"]).lower()
