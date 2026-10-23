"""Job creation, idempotency validation, and status retrieval endpoints."""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import MusicJob
from src.models import (
    MusicJobRequest,
    JobAcceptedResponse,
    JobStatusResponse,
    JobResultURLs,
    StandardErrorResponse,
)
from src.security import validate_remote_url, SSRFBlockedException
from src.storage import get_storage_service
from src.tasks import dispatch_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Jobs"])


def compute_request_hash(req: MusicJobRequest) -> str:
    """Compute deterministic SHA-256 hash of the canonical request JSON."""
    canonical_json = json.dumps(req.model_dump(), sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@router.post(
    "/music/jobs",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create background music generation job",
    description="Enqueue an asynchronous music generation and stem separation job. Supports Idempotency-Key header.",
    responses={
        202: {"model": JobAcceptedResponse, "description": "Job accepted and queued"},
        400: {"model": StandardErrorResponse, "description": "Invalid request parameters"},
        409: {"model": StandardErrorResponse, "description": "Idempotency key reuse conflict"},
    },
)
def create_music_job(
    request: MusicJobRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
    db: Session = Depends(get_db),
):
    """Create or retrieve background music generation job."""
    # Pre-validate remote URLs against SSRF before creating record
    if request.narration_url:
        try:
            validate_remote_url(request.narration_url)
        except SSRFBlockedException as e:
            logger.warning("Rejected job with restricted narration_url '%s': %s", request.narration_url, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SSRF_BLOCKED",
                    "message": f"narration_url targets a restricted address: {e.message}",
                    "retryable": False,
                    "details": {"narration_url": request.narration_url},
                },
            )

    if request.callback_url:
        try:
            validate_remote_url(request.callback_url)
        except SSRFBlockedException as e:
            logger.warning("Rejected job with restricted callback_url '%s': %s", request.callback_url, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SSRF_BLOCKED",
                    "message": f"callback_url targets a restricted address: {e.message}",
                    "retryable": False,
                    "details": {"callback_url": request.callback_url},
                },
            )

    req_hash = compute_request_hash(request)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check Idempotency-Key
    if idempotency_key:
        existing = db.query(MusicJob).filter(MusicJob.idempotency_key == idempotency_key).first()
        if existing:
            # Case A: Same key, identical request -> return existing job (Safe Retry)
            if existing.request_hash == req_hash:
                logger.info(
                    "Idempotent hit for key '%s': returning existing job %s",
                    idempotency_key,
                    existing.id,
                )
                return JobAcceptedResponse(
                    job_id=existing.id,
                    status=existing.status,
                    progress=existing.progress,
                    created_at=existing.created_at.isoformat(),
                    message="Existing job returned for identical Idempotency-Key",
                )
            else:
                # Case B: Same key, different request -> HTTP 409 Conflict
                logger.warning(
                    "Idempotency conflict: key '%s' reused with differing request payload",
                    idempotency_key,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": f"Idempotency-Key '{idempotency_key}' was previously used with a different request payload.",
                        "retryable": False,
                        "details": {"idempotency_key": idempotency_key},
                    },
                )

    # Create new job
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    new_job = MusicJob(
        id=job_id,
        idempotency_key=idempotency_key,
        request_hash=req_hash,
        prompt=request.prompt,
        duration_s=request.duration_s,
        status="queued",
        progress=0,
        request_json=json.dumps(request.model_dump()),
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    logger.info("Created job %s (Idempotency-Key: %s)", job_id, idempotency_key)

    # Enqueue background execution
    dispatch_job(job_id)

    return JobAcceptedResponse(
        job_id=job_id,
        status="queued",
        progress=0,
        created_at=now_iso,
        message="Job accepted and queued for processing",
    )


@router.get(
    "/jobs",
    response_model=list[JobStatusResponse],
    summary="List all jobs",
    description="Retrieve a list of music generation jobs ordered by creation date descending.",
)
def list_jobs(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """List recent music jobs."""
    jobs = db.query(MusicJob).order_by(MusicJob.created_at.desc()).offset(offset).limit(limit).all()
    results = []
    for job in jobs:
        result_urls = None
        urls_dict = job.get_result_urls()
        if urls_dict:
            result_urls = JobResultURLs(**urls_dict)

        results.append(
            JobStatusResponse(
                job_id=job.id,
                status=job.status,
                progress=job.progress,
                result=result_urls,
                manifest=job.get_manifest(),
                error=job.get_error(),
                created_at=job.created_at.isoformat(),
                updated_at=job.updated_at.isoformat(),
            )
        )
    return results


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and download links",
    description="Retrieve the execution progress, final audio download links, and manifest for a given job.",
    responses={
        200: {"model": JobStatusResponse, "description": "Job details and status"},
        404: {"model": StandardErrorResponse, "description": "Job ID not found"},
    },
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Retrieve current status, progress, and download links for a job."""
    job = db.query(MusicJob).filter(MusicJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Job with ID '{job_id}' does not exist.",
                "retryable": False,
                "details": {"job_id": job_id},
            },
        )

    result_urls = None
    urls_dict = job.get_result_urls()
    if urls_dict:
        result_urls = JobResultURLs(**urls_dict)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        result=result_urls,
        manifest=job.get_manifest(),
        error=job.get_error(),
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.get(
    "/storage/{object_path:path}",
    summary="Download locally stored audio file",
    include_in_schema=False,
)
def get_local_storage_file(object_path: str):
    """Serve locally stored audio files when using local storage fallback."""
    storage = get_storage_service()
    file_path = storage.get_local_file_path(object_path)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    content_type = "audio/wav"
    if file_path.endswith(".mp3"):
        content_type = "audio/mpeg"
    elif file_path.endswith(".json"):
        content_type = "application/json"

    return FileResponse(file_path, media_type=content_type, filename=os.path.basename(file_path))
