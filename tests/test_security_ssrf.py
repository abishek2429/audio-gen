"""Tests for SSRF prevention, URL validation, and HMAC webhook signing."""
import pytest
from fastapi.testclient import TestClient

from src.security import (
    validate_remote_url,
    SSRFBlockedException,
    sign_callback_payload,
)


@pytest.mark.parametrize(
    "forbidden_url",
    [
        "http://127.0.0.1/voiceover.wav",
        "http://localhost:8080/voiceover.wav",
        "http://10.0.0.5/audio.wav",
        "http://192.168.1.1/secret.wav",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/narration.wav",
        "ftp://example.com/audio.wav",
        "file:///etc/passwd",
    ],
)
def test_validate_remote_url_blocks_restricted_destinations(forbidden_url: str):
    """Verify that private, loopback, metadata, and invalid schemes raise SSRFBlockedException."""
    with pytest.raises(SSRFBlockedException):
        validate_remote_url(forbidden_url)


def test_api_blocks_ssrf_in_narration_url(client: TestClient):
    """Verify POST /api/v1/music/jobs rejects restricted narration_url with HTTP 400."""
    payload = {
        "prompt": "corporate acoustic",
        "duration_s": 10.0,
        "narration_url": "http://127.0.0.1:8000/internal-voiceover.wav",
    }
    resp = client.post("/api/v1/music/jobs", json=payload)
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "SSRF_BLOCKED"


def test_api_blocks_ssrf_in_callback_url(client: TestClient):
    """Verify POST /api/v1/music/jobs rejects restricted callback_url with HTTP 400."""
    payload = {
        "prompt": "corporate acoustic",
        "duration_s": 10.0,
        "callback_url": "http://169.254.169.254/webhook",
    }
    resp = client.post("/api/v1/music/jobs", json=payload)
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "SSRF_BLOCKED"


def test_hmac_sha256_signature():
    """Verify HMAC-SHA256 signature calculation matches expected RFC test vector."""
    secret = "secret-key-12345"
    payload = b'{"job_id":"job_abc123","status":"succeeded"}'
    sig = sign_callback_payload(payload, secret)

    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64  # 'sha256=' + 64 hex characters
