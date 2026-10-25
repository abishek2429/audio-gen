"""Background job execution worker and pipeline orchestration."""
import io
import os
import json
import logging
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import numpy as np

try:
    import soundfile as sf
except Exception:
    sf = None

from src.config import settings
from src.database.session import SessionLocal
from src.database.models import MusicJob
from src.models import MusicJobRequest, MusicManifest
from src.logging_config import job_id_ctx
from src.providers import get_provider
from src.providers.base import ProviderException, ProviderTimeoutException, ProviderMalformedResponseException
from src.storage import get_storage_service, StorageException
from src.security import fetch_remote_audio, send_signed_callback, SecurityException
from src.audio.prompt_guard import analyze_and_guard_prompt
from src.audio.dsp import (
    load_audio_from_bytes,
    align_duration_and_finish_tail,
    normalize_loudness_and_peaks,
    apply_voiceover_ducking,
)
from src.audio.validator import validate_audio_pack
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

import threading
from concurrent.futures import Future, wait as futures_wait


class JobWorkerPool:
    """Manages in-process thread pool execution with future tracking and graceful shutdown."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_futures: Dict[str, Future] = {}
        self._lock = threading.Lock()
        self._shutting_down = False

    def submit_job(self, job_id: str) -> bool:
        """Submit a job execution task to the thread pool."""
        with self._lock:
            if self._shutting_down:
                try:
                    logger.warning("Worker pool is shutting down; rejecting job %s", job_id)
                except Exception:
                    pass
                return False
            if getattr(self._executor, "_shutdown", False):
                self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            future = self._executor.submit(execute_job_pipeline, job_id)
            self._active_futures[job_id] = future
            future.add_done_callback(lambda f: self._cleanup_future(job_id))
            return True

    def _cleanup_future(self, job_id: str):
        with self._lock:
            self._active_futures.pop(job_id, None)

    def active_job_count(self) -> int:
        with self._lock:
            return len(self._active_futures)

    def wait_for_active_jobs(self, timeout: Optional[float] = 10.0) -> bool:
        """Wait for currently active jobs to finish."""
        with self._lock:
            futures = list(self._active_futures.values())
        if not futures:
            return True
        done, not_done = futures_wait(futures, timeout=timeout)
        return len(not_done) == 0

    def shutdown(self, wait: bool = True, timeout: Optional[float] = 10.0):
        """Gracefully shut down the executor, waiting for active jobs."""
        with self._lock:
            self._shutting_down = True
            futures = list(self._active_futures.values())
        if wait and futures:
            futures_wait(futures, timeout=timeout)
        self._executor.shutdown(wait=wait)

    def reset_for_testing(self):
        """Clean shutdown and recreate pool for test fixtures."""
        self.shutdown(wait=True, timeout=5.0)
        with self._lock:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self._active_futures.clear()
            self._shutting_down = False


_worker_pool = JobWorkerPool(max_workers=4)
# Maintain _executor alias for backward compatibility
_executor = _worker_pool._executor


def wait_for_active_jobs(timeout: Optional[float] = 10.0) -> bool:
    """Wait for all running background worker threads to finish."""
    return _worker_pool.wait_for_active_jobs(timeout=timeout)


def shutdown_worker_pool(wait: bool = True, timeout: Optional[float] = 10.0):
    """Gracefully shutdown the in-process worker pool."""
    _worker_pool.shutdown(wait=wait, timeout=timeout)


def ensure_worker_pool_active():
    """Ensure the global worker pool is initialized and accepting jobs."""
    with _worker_pool._lock:
        if _worker_pool._shutting_down or getattr(_worker_pool._executor, "_shutdown", False):
            _worker_pool._executor = ThreadPoolExecutor(max_workers=_worker_pool.max_workers)
            _worker_pool._active_futures.clear()
            _worker_pool._shutting_down = False


def reset_worker_pool_for_testing():
    """Reset worker pool between test modules."""
    _worker_pool.reset_for_testing()



def execute_job_pipeline(job_id: str):
    """Execute the complete generation, separation, finishing, and upload pipeline."""
    job_id_ctx.set(job_id)
    storage = get_storage_service()

    with SessionLocal() as db:
        job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
        if not job:
            logger.error("Job %s not found in database", job_id)
            return

        if job.status in ("succeeded", "failed"):
            logger.info("Job %s already in terminal state '%s'", job_id, job.status)
            return

        # Mark as running
        job.status = "running"
        job.progress = 10
        db.commit()

        req_data = json.loads(job.request_json)
        req = MusicJobRequest(**req_data)

    logger.info("Starting processing for job %s (prompt: '%s', duration: %.1fs)", job_id, req.prompt, req.duration_s)
    manifest_warnings: list[str] = []

    try:
        start_total = time.time()

        # 1. Fetch narration audio if URL is provided
        speech_audio: Optional[np.ndarray] = None
        if req.narration_url:
            logger.info("Fetching remote narration audio from %s", req.narration_url)
            speech_bytes = fetch_remote_audio(req.narration_url, max_bytes=settings.max_upload_size_bytes)
            speech_audio, _ = load_audio_from_bytes(speech_bytes, target_sr=settings.default_sample_rate)

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({"progress": 25})
            db.commit()

        # 2. Prompt Analysis & Safety Guardrails
        prompt_analysis = analyze_and_guard_prompt(req.prompt)
        manifest_warnings.extend(prompt_analysis.warnings)
        effective_prompt = prompt_analysis.effective_prompt

        # 3. Music Generation via Provider Adapter
        provider = get_provider(settings.music_provider)
        logger.info("Generating music with provider '%s' (effective prompt: '%s')", provider.provider_name, effective_prompt)
        t0_gen = time.time()
        gen_res = provider.generate_music(
            prompt=effective_prompt,
            duration_s=req.duration_s,
            tempo_bpm=req.tempo_bpm,
            key=req.key,
            seed=req.seed,
        )
        t_gen = time.time() - t0_gen

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({"progress": 45})
            db.commit()

        # Upload raw generated audio
        raw_gen_ext = gen_res.format
        storage.upload_file(
            gen_res.audio_bytes,
            f"{job_id}/raw_generation.{raw_gen_ext}",
            content_type=f"audio/{raw_gen_ext}",
        )

        # 3. Stem Separation via Provider Adapter
        logger.info("Separating stems with provider '%s'", provider.provider_name)
        t0_sep = time.time()
        sep_res = provider.separate_stems(
            audio_bytes=gen_res.audio_bytes,
            sample_rate=settings.default_sample_rate,
        )
        t_sep = time.time() - t0_sep

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({"progress": 65})
            db.commit()

        # 4. DSP Finishing (48 kHz, Duration Alignment, Intentional Ending, LUFS, True Peak)
        logger.info("Applying DSP finishing pipeline...")
        t0_dsp = time.time()
        sr = settings.default_sample_rate

        raw_mix_audio, _ = load_audio_from_bytes(gen_res.audio_bytes, target_sr=sr)
        aligned_mix = align_duration_and_finish_tail(
            raw_mix_audio,
            target_duration_s=req.duration_s,
            sr=sr,
            fade_tail_s=1.2,
        )

        aligned_stems: Dict[str, np.ndarray] = {}
        for stem_name, stem_bytes in sep_res.stems.items():
            s_audio, _ = load_audio_from_bytes(stem_bytes, target_sr=sr)
            aligned_stem = align_duration_and_finish_tail(
                s_audio,
                target_duration_s=req.duration_s,
                sr=sr,
                fade_tail_s=1.2,
            )
            aligned_stems[stem_name] = aligned_stem

        # BS.1770-4 normalization
        finished_mix, finished_stems, measured_lufs, measured_dbtp, applied_gain = normalize_loudness_and_peaks(
            mix=aligned_mix,
            stems=aligned_stems,
            sr=sr,
            target_lufs=req.output.target_lufs,
            ceiling_dbtp=settings.target_true_peak_dbtp,
        )

        # Voiceover ducking if narration provided
        ducked_mix: Optional[np.ndarray] = None
        if speech_audio is not None:
            speech_mono = np.mean(speech_audio, axis=1) if speech_audio.ndim > 1 else speech_audio
            speech_rms = float(np.sqrt(np.mean(speech_mono ** 2)))
            speech_rms_dbfs = float(20.0 * np.log10(speech_rms + 1e-12))
            if speech_rms_dbfs < -45.0:
                logger.warning("No speech activity detected in narration track (RMS: %.2f dBFS)", speech_rms_dbfs)
                manifest_warnings.append(
                    f"No speech activity detected in narration track (RMS {speech_rms_dbfs:.1f} dBFS < -45 dBFS); "
                    f"sidechain ducking bypassed to preserve nominal music dynamics."
                )
                ducked_mix = np.copy(finished_mix)
            else:
                logger.info("Applying sidechain voiceover ducking (-10 dB)...")
                ducked_mix, _ = apply_voiceover_ducking(finished_mix, speech_audio, sr=sr, ducking_db=10.0)
                flen = int(0.1 * sr)
                n_f = len(speech_mono) // flen
                if n_f > 0:
                    f_p = [float(np.mean(speech_mono[i * flen : (i + 1) * flen] ** 2)) for i in range(n_f)]
                    silent_ratio = sum(1 for p in f_p if 10 * np.log10(p + 1e-12) < -35.0) / n_f
                    if silent_ratio > 0.4 and req.duration_s >= 10.0:
                        manifest_warnings.append(
                            "Narration contains extended silent intervals (>10s); sidechain ducking smoothly restored nominal volume during pauses."
                        )

        t_dsp = time.time() - t0_dsp

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({"progress": 80})
            db.commit()

        # 5. Upload Finished Audio Files to Storage & Collect Download URLs
        logger.info("Uploading finished audio assets to storage...")
        result_urls: Dict[str, Any] = {"stems": {}}

        # Encode mix.wav
        mix_buf = io.BytesIO()
        sf.write(mix_buf, finished_mix, sr, format="WAV", subtype="PCM_24")
        mix_url = storage.upload_file(mix_buf.getvalue(), f"{job_id}/mix.wav", content_type="audio/wav")
        result_urls["mix_wav"] = mix_url

        # Encode mix.mp3
        try:
            mp3_buf = io.BytesIO()
            sf.write(mp3_buf, finished_mix, sr, format="MP3")
            mp3_url = storage.upload_file(mp3_buf.getvalue(), f"{job_id}/mix.mp3", content_type="audio/mpeg")
            result_urls["mix_mp3"] = mp3_url
        except Exception:
            pass

        # Upload ducked mix if generated
        if ducked_mix is not None:
            ducked_buf = io.BytesIO()
            sf.write(ducked_buf, ducked_mix, sr, format="WAV", subtype="PCM_24")
            ducked_url = storage.upload_file(
                ducked_buf.getvalue(), f"{job_id}/mix_ducked.wav", content_type="audio/wav"
            )
            result_urls["mix_ducked_wav"] = ducked_url

        # Upload individual stems
        stem_manifest_map: Dict[str, str] = {}
        stem_gains_map: Dict[str, float] = {}

        for stem_name, stem_arr in finished_stems.items():
            s_buf = io.BytesIO()
            sf.write(s_buf, stem_arr, sr, format="WAV", subtype="PCM_24")
            s_url = storage.upload_file(
                s_buf.getvalue(), f"{job_id}/stems/{stem_name}.wav", content_type="audio/wav"
            )
            result_urls["stems"][stem_name] = s_url
            stem_manifest_map[stem_name] = f"stems/{stem_name}.wav"
            stem_gains_map[stem_name] = 1.0

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({"progress": 90})
            db.commit()

        # 6. Validation & Manifest Generation
        with tempfile.TemporaryDirectory() as tmp_val_dir:
            tmp_mix_path = os.path.join(tmp_val_dir, "mix.wav")
            tmp_stems_dir = os.path.join(tmp_val_dir, "stems")
            os.makedirs(tmp_stems_dir, exist_ok=True)

            sf.write(tmp_mix_path, finished_mix, sr, format="WAV", subtype="PCM_24")
            for stem_name, stem_arr in finished_stems.items():
                sf.write(os.path.join(tmp_stems_dir, f"{stem_name}.wav"), stem_arr, sr, format="WAV", subtype="PCM_24")

            # Write temp manifest for validator
            tmp_manifest_path = os.path.join(tmp_val_dir, "music_manifest.json")
            with open(tmp_manifest_path, "w", encoding="utf-8") as f:
                json.dump({"job_id": job_id, "requested_duration_s": req.duration_s, "stem_gains": stem_gains_map}, f)

            val_report = validate_audio_pack(tmp_val_dir, requested_duration_s=req.duration_s)

        # Upload validation report
        val_url = storage.upload_file(
            json.dumps(val_report.model_dump(), indent=2).encode("utf-8"),
            f"{job_id}/validation_report.json",
            content_type="application/json",
        )
        result_urls["validation_report"] = val_url

        # Compute musical beat grid
        detected_bpm = gen_res.raw_metadata.get("tempo_bpm", req.tempo_bpm or 110)
        detected_key = gen_res.raw_metadata.get("key", req.key or "C major")
        beat_interval_s = 60.0 / detected_bpm
        num_beats = int(req.duration_s / beat_interval_s)
        beat_grid = [round(b * beat_interval_s, 4) for b in range(min(32, num_beats + 1))]

        total_elapsed = time.time() - start_total
        total_cost = gen_res.cost_usd + sep_res.cost_usd

        # Build official manifest
        manifest = MusicManifest(
            job_id=job_id,
            prompt=req.prompt,
            requested_duration_s=req.duration_s,
            actual_duration_s=round(len(finished_mix) / sr, 4),
            sample_rate=sr,
            tempo_bpm=detected_bpm,
            key=detected_key,
            sections=[s.model_dump() for s in (req.sections or [])] or [{"start_s": 0.0, "mood": req.prompt}],
            beat_grid_s=beat_grid,
            stems=stem_manifest_map,
            stem_gains=stem_gains_map,
            models={
                "music_generator": f"{provider.provider_name}:{getattr(provider, 'model_version', 'v1')}",
                "stem_separator": f"{provider.provider_name}:{getattr(provider, 'separation_engine', 'v1')}",
            },
            provider=provider.provider_name,
            seed=req.seed,
            audio_metrics={
                "integrated_lufs": round(measured_lufs, 2),
                "true_peak_dbtp": round(measured_dbtp, 2),
                "master_gain": round(applied_gain, 4),
            },
            timings_s={
                "generation_time_s": round(t_gen, 3),
                "separation_time_s": round(t_sep, 3),
                "dsp_time_s": round(t_dsp, 3),
                "total_elapsed_s": round(total_elapsed, 3),
            },
            cost_usd=round(total_cost, 4),
            commercial_license={
                "commercial_cleared": True,
                "license_type": "Royalty-Free Commercial Video Sync",
                "attribution_required": False,
                "terms_reference": "SOURCES.md",
            },
            warnings=manifest_warnings,
        )

        manifest_url = storage.upload_file(
            json.dumps(manifest.model_dump(), indent=2).encode("utf-8"),
            f"{job_id}/music_manifest.json",
            content_type="application/json",
        )
        result_urls["manifest"] = manifest_url

        # 7. Update Database with Success State
        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({
                "status": "succeeded",
                "progress": 100,
                "result_urls_json": json.dumps(result_urls),
                "manifest_json": json.dumps(manifest.model_dump()),
            })
            db.commit()

        logger.info("Job %s succeeded in %.2fs (Cost: $%.4f)", job_id, total_elapsed, total_cost)

        # 8. Webhook Notification if callback_url configured
        if req.callback_url:
            logger.info("Sending signed webhook callback for job %s to %s", job_id, req.callback_url)
            cb_payload = {
                "event": "job.completed",
                "job_id": job_id,
                "status": "succeeded",
                "result": result_urls,
                "manifest": manifest.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            send_signed_callback(req.callback_url, cb_payload, settings.callback_secret)

    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        error_code = "PROCESSING_FAILED"
        if isinstance(e, SecurityException):
            error_code = e.code
        elif isinstance(e, ProviderException):
            error_code = e.code
        elif isinstance(e, StorageException):
            error_code = e.code
        elif "timeout" in str(e).lower() or isinstance(e, TimeoutError):
            error_code = "PROVIDER_TIMEOUT"
        elif "malformed" in str(e).lower() or "corrupt" in str(e).lower():
            error_code = "PROVIDER_MALFORMED_RESPONSE"

        with SessionLocal() as db:
            db.query(MusicJob).filter(MusicJob.id == job_id).update({
                "status": "failed",
                "progress": 100,
                "error_code": error_code,
                "error_message": str(e),
                "error_details_json": json.dumps({"exception": e.__class__.__name__}),
            })
            db.commit()

        if req.callback_url:
            cb_payload = {
                "event": "job.failed",
                "job_id": job_id,
                "status": "failed",
                "error": {"code": error_code, "message": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            send_signed_callback(req.callback_url, cb_payload, settings.callback_secret)


@celery_app.task(name="process_music_job", bind=True)
def celery_process_music_job(self, job_id: str):
    """Celery worker task wrapper."""
    execute_job_pipeline(job_id)


def dispatch_job(job_id: str):
    """Dispatch job to Celery worker or in-process thread pool depending on configuration."""
    if settings.celery_enabled:
        try:
            celery_process_music_job.delay(job_id)
            logger.info("Enqueued job %s to Celery broker", job_id)
            return
        except Exception as e:
            logger.warning("Celery enqueue failed (%s), running via in-process executor", e)

    # In-process asynchronous execution
    submitted = _worker_pool.submit_job(job_id)
    if submitted:
        logger.info("Submitted job %s to in-process thread executor", job_id)
    else:
        logger.warning("Worker pool is shutting down; job %s could not be queued", job_id)

