"""API endpoints for testing music provider connections, checking balance, and comparing providers."""
import logging
import time
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.config import settings
from src.models import (
    ProviderTestRequest,
    ProviderTestResponse,
    ProviderTestSampleResult,
    StandardErrorResponse,
)
from src.providers import get_provider
from src.providers.base import (
    AudioProviderInterface,
    ProviderException,
    ProviderTimeoutException,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/providers", tags=["Providers"])

# Provider Knowledge & Verification Matrix (derived from verified official documentation)
PROVIDER_SPEC_CATALOG: Dict[str, Dict[str, Any]] = {
    "stable_audio": {
        "provider_display_name": "Stability AI (Stable Audio)",
        "official_docs_url": "https://platform.stability.ai/docs/api-reference#tag/Audio/paths/~1v2beta~1audio~1stable-audio~1text-to-audio/post",
        "pricing_model": "$0.01 per credit (20 credits = $0.20 per generation)",
        "cost_per_run_usd": 0.20,
        "free_trial_available": True,
        "free_trial_details": (
            "Stability AI developer platform grants 25 free credits upon initial developer signup ($0.25 value). "
            "Because each generation costs 20 credits, this allows exactly 1 free test generation before requiring "
            "credit purchase. Consumer web tier (50 credits/mo at stableaudio.com) does NOT grant developer REST API access."
        ),
        "commercial_use_allowed": True,
        "license_type": "Commercial license included with developer API credits",
        "max_duration_s": 190.0,
        "output_formats": ["mp3", "wav"],
        "rate_limits": "150 requests / minute",
        "limitations": [
            "Generates stereo master mix only. Multi-track instrument stems are decomposed downstream via DSP harmonic filterbank.",
            "Free trial quota is strictly limited to 1 generation (25 credits signup / 20 credits per generation).",
            "Single generation max duration is 190 seconds (longer video soundtracks require stitching or loop alignment).",
            "Requires STABILITY_API_KEY environment variable.",
        ],
    },
    "replicate": {
        "provider_display_name": "Meta MusicGen (via Replicate)",
        "official_docs_url": "https://replicate.com/meta/musicgen",
        "pricing_model": "Pay-per-second GPU compute: ~$0.0014/sec on Nvidia A100 (~$0.045 per 30s generation)",
        "cost_per_run_usd": 0.045,
        "free_trial_available": False,
        "free_trial_details": (
            "Replicate requires credit card billing on file. No perpetual free API tier. "
            "Accounts may occasionally receive a promotional $5 one-time initial credit upon first signup."
        ),
        "commercial_use_allowed": False,
        "license_type": "CC-BY-NC 4.0 (Non-Commercial Research Only)",
        "max_duration_s": 30.0,
        "output_formats": ["wav"],
        "rate_limits": "Concurrent hardware rate limits based on account tier",
        "limitations": [
            "CRITICAL: Official Meta MusicGen weights are licensed under CC-BY-NC 4.0; commercial use is prohibited.",
            "Requires payment method on file; no sustained free API tier.",
            "Cold start latency on serverless GPU containers can take 15-40 seconds if instance is idle.",
            "Generates stereo mix only (no separate stems).",
            "Requires REPLICATE_API_TOKEN environment variable.",
        ],
    },
    "soundverse": {
        "provider_display_name": "Soundverse Enterprise Gateway",
        "official_docs_url": "https://docs.soundverse.ai",
        "pricing_model": "$0.07-$0.11 per track + $0.10 for Demucs 6-stem separation",
        "cost_per_run_usd": 0.17,
        "free_trial_available": True,
        "free_trial_details": "10 trial credits on registration. Afterwards requires credit top-up.",
        "commercial_use_allowed": True,
        "license_type": "Commercial license with paid credits",
        "max_duration_s": 180.0,
        "output_formats": ["wav", "mp3"],
        "rate_limits": "60 requests / minute",
        "limitations": [
            "Free trial limited to 10 initial credits.",
            "Requires enterprise API key access.",
            "Requires SOUNDVERSE_API_KEY environment variable.",
        ],
    },
    "elevenlabs": {
        "provider_display_name": "ElevenLabs Music API",
        "official_docs_url": "https://elevenlabs.io/docs/api-reference/music",
        "pricing_model": "Included in paid subscription tiers (~$0.30 per minute equivalent in character/credit consumption)",
        "cost_per_run_usd": 0.30,
        "free_trial_available": False,
        "free_trial_details": "ElevenLabs free tier does not include the Music API. Music synthesis is restricted to paid Creator and Pro plans.",
        "commercial_use_allowed": True,
        "license_type": "Commercial license with paid subscription",
        "max_duration_s": 600.0,
        "output_formats": ["mp3"],
        "rate_limits": "Varies by subscription tier",
        "limitations": [
            "Music API has no free tier; requires active paid subscription.",
            "Highest cost per minute of all tested providers.",
            "Requires ELEVENLABS_API_KEY environment variable.",
        ],
    },
    "mock": {
        "provider_display_name": "IncuBrix Offline Mock Procedural Provider",
        "official_docs_url": "file:///c:/audio-gen/src/providers/mock_provider.py",
        "pricing_model": "100% Free ($0.00 / generation)",
        "cost_per_run_usd": 0.00,
        "free_trial_available": True,
        "free_trial_details": "Completely free, in-process, offline algorithmic synthesizer without API keys, limits, or billing.",
        "commercial_use_allowed": True,
        "license_type": "Public Domain / Apache 2.0 (Zero copyright training risks)",
        "max_duration_s": 300.0,
        "output_formats": ["wav"],
        "rate_limits": "Unlimited local compute",
        "limitations": [
            "Synthesized via procedural mathematical DSP oscillators rather than deep learning diffusion models.",
            "Designed for CI/CD test suites, zero-cost local development, and offline system testing.",
        ],
    },
}


@router.get(
    "/comparison",
    summary="Get verified music provider comparison matrix",
    description="Returns pricing, license, duration, stem support, and limitations for all evaluated providers.",
)
def get_provider_comparison() -> Dict[str, Any]:
    """Return catalog comparison of all evaluated music generation providers."""
    return {
        "recommended_provider": "stable_audio",
        "zero_cost_offline_provider": "mock",
        "providers": PROVIDER_SPEC_CATALOG,
    }


@router.get(
    "/status",
    summary="Get configured provider status and available environment keys",
    description="Check which providers have server-side environment variables configured.",
)
def get_providers_status() -> Dict[str, Any]:
    """Check configuration and presence of environment variables."""
    return {
        "active_provider": settings.music_provider,
        "configured_keys": {
            "stable_audio": bool(settings.stability_api_key and settings.stability_api_key.strip()),
            "replicate": bool(settings.replicate_api_token and settings.replicate_api_token.strip()),
            "soundverse": bool(settings.soundverse_api_key and settings.soundverse_api_key.strip()),
            "elevenlabs": bool(settings.elevenlabs_api_key and settings.elevenlabs_api_key.strip()),
            "mock": True,
        },
    }


def _scrub_secrets(text: str) -> str:
    """Mask credentials, tokens, and sensitive headers from diagnostic messages."""
    import re
    # Mask sk-..., r8_..., or Bearer tokens
    sanitized = re.sub(r"(sk-[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+", r"\1...", str(text))
    sanitized = re.sub(r"(r8_[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+", r"\1...", sanitized)
    sanitized = re.sub(r"(Bearer\s+)[^\s]+", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(xi-api-key['\":\s]+)[^\s,\"'}]+", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized


@router.post(
    "/test-connection",
    response_model=ProviderTestResponse,
    summary="Test provider authentication, balance, and optional short generation",
    description="Verify API credentials, inspect developer credits, and optionally perform a 5-second test synthesis.",
    responses={
        200: {"model": ProviderTestResponse, "description": "Provider test executed successfully"},
        400: {"model": StandardErrorResponse, "description": "Invalid test request parameters"},
    },
)
def test_provider_connection(payload: ProviderTestRequest) -> ProviderTestResponse:
    """Test provider authentication and execute short sample generation if requested."""
    target_provider = (payload.provider or settings.music_provider).lower()
    if target_provider == "auto":
        target_provider = "stable_audio" if settings.stability_api_key else "mock"

    spec = PROVIDER_SPEC_CATALOG.get(target_provider, PROVIDER_SPEC_CATALOG["mock"])

    try:
        provider = get_provider(target_provider)
    except ValueError as e:
        return ProviderTestResponse(
            provider=target_provider,
            authenticated=False,
            status="configuration_error",
            credits_balance=0.0,
            cost_per_run_usd=spec.get("cost_per_run_usd", 0.0),
            free_trial_available=spec.get("free_trial_available", False),
            free_trial_details=spec.get("free_trial_details", ""),
            commercial_use_allowed=spec.get("commercial_use_allowed", False),
            license_type=spec.get("license_type", "Unknown"),
            max_duration_s=spec.get("max_duration_s", 0.0),
            output_formats=spec.get("output_formats", []),
            sample_generation=None,
            limitations=spec.get("limitations", []),
            message=_scrub_secrets(str(e)),
        )

    # 1. Check connection and balance
    auth_ok = False
    status_str = "ok"
    credits_balance = None
    msg = "Authentication and connection successful."

    try:
        balance_info = provider.check_connection_and_balance()
        auth_ok = balance_info.get("authenticated", True)
        credits_balance = balance_info.get("credits_balance")
        if not auth_ok:
            status_str = "unauthenticated"
            msg = balance_info.get("error", "Authentication check failed.")
    except ValueError as exc:
        auth_ok = False
        exc_str = str(exc)
        is_credential_err = any(k in exc_str.lower() for k in ("api_key", "api_token", "not configured", "not set", "missing key", "credentials"))
        if is_credential_err:
            status_str = "unauthenticated"
            msg = f"Provider credentials not configured: {exc}"
        else:
            status_str = "configuration_error"
            msg = f"Provider configuration error: {exc}"
    except ProviderTimeoutException as exc:
        auth_ok = False
        status_str = "provider_outage"
        msg = f"Provider connection timed out: {exc}"
    except ProviderException as exc:
        auth_ok = False
        if exc.code == "AUTHENTICATION_FAILED":
            status_str = "unauthenticated"
        elif exc.code == "QUOTA_EXHAUSTED":
            status_str = "quota_exhausted"
        elif exc.code == "RATE_LIMIT_EXCEEDED":
            status_str = "rate_limited"
        elif exc.code in ("NETWORK_ERROR", "PROVIDER_TIMEOUT"):
            status_str = "provider_outage"
        else:
            status_str = "error"
        msg = f"Provider verification error: {exc}"
    except Exception as exc:
        auth_ok = False
        status_str = "error"
        msg = f"Connection check encountered error: {exc}"

    sample_result: Optional[ProviderTestSampleResult] = None

    # 2. Perform short live test generation if requested
    if payload.perform_sample_generation:
        if not auth_ok and target_provider != "mock":
            msg += " Sample generation was skipped because provider is not authenticated."
        else:
            try:
                t0 = time.time()
                gen_res = provider.generate_music(
                    prompt=payload.prompt or "Warm acoustic guitar background music",
                    duration_s=payload.duration_s,
                )
                elapsed = round(time.time() - t0, 3)

                sample_result = ProviderTestSampleResult(
                    duration_s=gen_res.duration_s,
                    format=gen_res.format,
                    sample_rate=gen_res.sample_rate,
                    cost_usd=gen_res.cost_usd,
                    credits_consumed=gen_res.raw_metadata.get("credits_charged", 0),
                    latency_s=elapsed,
                    sample_audio_size_bytes=len(gen_res.audio_bytes),
                    provider_raw_metadata=gen_res.raw_metadata,
                )
                msg += f" Sample generation completed in {elapsed}s (output: {gen_res.duration_s}s, {len(gen_res.audio_bytes)} bytes)."
            except ProviderTimeoutException as p_timeout:
                status_str = "provider_outage"
                msg += f" Sample generation timed out: {p_timeout}"
            except ProviderException as p_exc:
                if p_exc.code == "QUOTA_EXHAUSTED":
                    status_str = "quota_exhausted"
                elif p_exc.code == "RATE_LIMIT_EXCEEDED":
                    status_str = "rate_limited"
                elif p_exc.code in ("NETWORK_ERROR", "PROVIDER_TIMEOUT"):
                    status_str = "provider_outage"
                else:
                    status_str = "error"
                msg += f" Sample generation failed: {p_exc}"
            except Exception as exc:
                status_str = "error"
                msg += f" Sample generation encountered unexpected error: {exc}"

    return ProviderTestResponse(
        provider=target_provider,
        authenticated=auth_ok,
        status=status_str,
        credits_balance=credits_balance,
        cost_per_run_usd=spec.get("cost_per_run_usd", 0.0),
        free_trial_available=spec.get("free_trial_available", False),
        free_trial_details=spec.get("free_trial_details", ""),
        commercial_use_allowed=spec.get("commercial_use_allowed", False),
        license_type=spec.get("license_type", "Unknown"),
        max_duration_s=spec.get("max_duration_s", 0.0),
        output_formats=spec.get("output_formats", []),
        sample_generation=sample_result,
        limitations=spec.get("limitations", []),
        message=_scrub_secrets(msg),
    )

