"""Automated tests for provider verification and test-connection API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_get_provider_comparison():
    """Verify GET /api/v1/providers/comparison returns catalog with all providers."""
    resp = client.get("/api/v1/providers/comparison")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended_provider"] == "stable_audio"
    assert "stable_audio" in data["providers"]
    assert "replicate" in data["providers"]
    assert "soundverse" in data["providers"]
    assert "elevenlabs" in data["providers"]
    assert "mock" in data["providers"]

    stable_spec = data["providers"]["stable_audio"]
    assert stable_spec["commercial_use_allowed"] is True
    assert stable_spec["cost_per_run_usd"] == 0.20
    assert stable_spec["free_trial_available"] is True

    replicate_spec = data["providers"]["replicate"]
    assert replicate_spec["commercial_use_allowed"] is False
    assert "CC-BY-NC 4.0" in replicate_spec["license_type"]


def test_get_providers_status():
    """Verify GET /api/v1/providers/status reports configuration."""
    resp = client.get("/api/v1/providers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_provider" in data
    assert "configured_keys" in data
    assert data["configured_keys"]["mock"] is True


def test_provider_test_connection_mock_with_sample():
    """Verify POST /api/v1/providers/test-connection with mock provider runs short generation."""
    resp = client.post(
        "/api/v1/providers/test-connection",
        json={
            "provider": "mock",
            "perform_sample_generation": True,
            "prompt": "Test acoustic guitar",
            "duration_s": 5.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["authenticated"] is True
    assert data["status"] == "ok"
    assert data["sample_generation"] is not None
    assert data["sample_generation"]["duration_s"] == 5.0
    assert data["sample_generation"]["cost_usd"] == 0.0
    assert data["sample_generation"]["sample_audio_size_bytes"] > 0
    assert data["commercial_use_allowed"] is True


def test_provider_test_connection_unconfigured_external_key():
    """Verify POST /api/v1/providers/test-connection for external provider without key handles gracefully."""
    resp = client.post(
        "/api/v1/providers/test-connection",
        json={
            "provider": "stable_audio",
            "perform_sample_generation": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "stable_audio"
    # In clean test environment without STABILITY_API_KEY, authentication is False
    assert data["authenticated"] is False
    assert data["status"] == "unauthenticated"
    assert "STABILITY_API_KEY" in data["message"]
    assert data["cost_per_run_usd"] == 0.20
    assert data["free_trial_available"] is True


def test_provider_test_connection_unsupported_provider():
    """Verify testing an invalid/unsupported provider returns configuration_error."""
    resp = client.post(
        "/api/v1/providers/test-connection",
        json={"provider": "nonexistent_synth_999"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "configuration_error"
    assert data["authenticated"] is False
    assert "Unsupported provider" in data["message"]


def test_provider_test_connection_scrubs_secrets(monkeypatch):
    """Verify that credentials or tokens are never leaked in diagnostic messages."""
    from src.providers.stable_audio import StableAudioAdapter
    from src.providers.base import ProviderException

    def mock_check(self):
        raise ProviderException("Failed with sk-1234567890abcdef and Bearer secret_tok_xyz")

    monkeypatch.setattr(StableAudioAdapter, "check_connection_and_balance", mock_check)
    monkeypatch.setattr("src.config.settings.stability_api_key", "sk-1234567890abcdef")

    resp = client.post(
        "/api/v1/providers/test-connection",
        json={"provider": "stable_audio"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sk-1234567890abcdef" not in data["message"]
    assert "secret_tok_xyz" not in data["message"]
    assert "sk-1234..." in data["message"] or "[REDACTED]" in data["message"]


def test_provider_test_connection_error_status_mapping(monkeypatch):
    """Verify specific ProviderException codes map to precise status strings."""
    from src.providers.stable_audio import StableAudioAdapter
    from src.providers.base import ProviderException, ProviderTimeoutException

    # 1. Quota Exhausted
    monkeypatch.setattr("src.config.settings.stability_api_key", "sk-valid-key")
    monkeypatch.setattr(
        StableAudioAdapter,
        "check_connection_and_balance",
        lambda self: (_ for _ in ()).throw(ProviderException("Credits empty", code="QUOTA_EXHAUSTED")),
    )
    r_quota = client.post("/api/v1/providers/test-connection", json={"provider": "stable_audio"})
    assert r_quota.json()["status"] == "quota_exhausted"

    # 2. Rate Limited
    monkeypatch.setattr(
        StableAudioAdapter,
        "check_connection_and_balance",
        lambda self: (_ for _ in ()).throw(ProviderException("Too many calls", code="RATE_LIMIT_EXCEEDED")),
    )
    r_rate = client.post("/api/v1/providers/test-connection", json={"provider": "stable_audio"})
    assert r_rate.json()["status"] == "rate_limited"

    # 3. Provider Outage / Timeout
    monkeypatch.setattr(
        StableAudioAdapter,
        "check_connection_and_balance",
        lambda self: (_ for _ in ()).throw(ProviderTimeoutException("Gateway timed out")),
    )
    r_outage = client.post("/api/v1/providers/test-connection", json={"provider": "stable_audio"})
    assert r_outage.json()["status"] == "provider_outage"

