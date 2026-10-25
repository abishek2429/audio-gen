"""API endpoints for video upload, visual analysis, and video-to-beat generation."""
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.config import settings
from src.database.session import get_db
from src.database.models import MusicJob
from src.models import (
    MusicJobRequest,
    StandardErrorResponse,
    VideoAnalysisResponse,
    VideoMetadataResponse,
    VideoActivityResponse,
    KeyframeThumbnailResponse,
    MusicalAccentResponse,
    MusicPlanResponse,
    VideoJobAcceptedResponse,
)
from src.tasks import dispatch_job
from src.video.analyzer import (
    VideoAnalyzer,
    VideoAnalysisException,
    VideoAnalysisResult,
)
from src.video.arranger import VideoArranger, MusicPlan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/video", tags=["Video-to-Beat"])


def _map_analysis_to_response(analysis: VideoAnalysisResult, plan: MusicPlan) -> VideoAnalysisResponse:
    """Format domain video analysis and music plan into standardized API response."""
    return VideoAnalysisResponse(
        metadata=VideoMetadataResponse(
            filename=analysis.metadata.filename,
            duration_s=analysis.metadata.duration_s,
            fps=analysis.metadata.fps,
            width=analysis.metadata.width,
            height=analysis.metadata.height,
            frame_count=analysis.metadata.frame_count,
            aspect_ratio=analysis.metadata.aspect_ratio,
            file_size_bytes=analysis.metadata.file_size_bytes,
        ),
        scene_cuts=analysis.scene_cuts,
        activity=VideoActivityResponse(
            avg_motion=analysis.activity.avg_motion,
            max_motion=analysis.activity.max_motion,
            motion_variance=analysis.activity.motion_variance,
            avg_brightness=analysis.activity.avg_brightness,
            avg_saturation=analysis.activity.avg_saturation,
            warm_color_ratio=analysis.activity.warm_color_ratio,
            pacing=analysis.activity.pacing,
            detected_mood=analysis.activity.detected_mood,
        ),
        keyframes=[
            KeyframeThumbnailResponse(timestamp_s=kf.timestamp_s, data_uri=kf.data_uri)
            for kf in analysis.keyframes
        ],
        accent_timestamps=analysis.accent_timestamps,
        audio_present=analysis.audio_present,
        recommended_plan=MusicPlanResponse(
            genre=plan.genre,
            mood=plan.mood,
            tempo_bpm=plan.tempo_bpm,
            key=plan.key,
            rhythmic_style=plan.rhythmic_style,
            intensity=plan.intensity,
            instrumentation=plan.instrumentation,
            target_duration_s=plan.target_duration_s,
            sections=plan.sections,
            accents=[
                MusicalAccentResponse(
                    timestamp_s=acc.timestamp_s,
                    event_description=acc.event_description,
                    musical_action=acc.musical_action,
                )
                for acc in plan.accents
            ],
            prompt=plan.prompt,
        ),
    )


@router.post(
    "/analyze",
    response_model=VideoAnalysisResponse,
    summary="Analyze video visual dynamics and generate musical arrangement plan",
    description="Upload a video file to extract duration, scene cuts, pacing, mood, and a synchronized music plan.",
    responses={
        200: {"model": VideoAnalysisResponse, "description": "Video analyzed successfully"},
        400: {"model": StandardErrorResponse, "description": "Invalid video file, unsupported format, or corrupt data"},
        413: {"model": StandardErrorResponse, "description": "Video file exceeds upload size limit"},
    },
)
async def analyze_video(
    file: UploadFile = File(..., description="Supported video file (.mp4, .mov, .avi, .webm)"),
    style: Optional[str] = Form(None, description="Optional style preference ('cinematic', 'electronic', 'corporate', etc.)"),
    prompt_override: Optional[str] = Form(None, description="Optional custom prompt instructions"),
):
    """Analyze video frames and compose structured musical plan."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_FILENAME",
                "message": "Upload filename must be provided.",
                "retryable": False,
                "details": {},
            },
        )

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded video stream: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UPLOAD_READ_FAILED",
                "message": f"Failed to read uploaded video file: {exc}",
                "retryable": False,
                "details": {},
            },
        )

    analyzer = VideoAnalyzer(max_upload_size_bytes=settings.max_upload_size_bytes)
    arranger = VideoArranger()

    try:
        analysis = analyzer.analyze_bytes(content, filename=file.filename)
        plan = arranger.create_plan(
            analysis=analysis,
            style_preference=style,
            custom_prompt_override=prompt_override,
        )
        return _map_analysis_to_response(analysis, plan)
    except VideoAnalysisException as e:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if e.code == "PAYLOAD_TOO_LARGE" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": e.code,
                "message": e.message,
                "retryable": False,
                "details": e.details,
            },
        )
    except Exception as e:
        logger.exception("Unexpected error during video analysis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "VIDEO_ANALYSIS_FAILED",
                "message": f"Unexpected error processing video: {str(e)}",
                "retryable": True,
                "details": {},
            },
        )


@router.post(
    "/jobs",
    response_model=VideoJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Video-to-Beat background music generation job",
    description="Upload video, extract timing and mood, and enqueue background soundtrack generation.",
    responses={
        202: {"model": VideoJobAcceptedResponse, "description": "Video-to-beat job accepted and queued"},
        400: {"model": StandardErrorResponse, "description": "Invalid video or request parameters"},
        409: {"model": StandardErrorResponse, "description": "Idempotency key reuse conflict"},
        413: {"model": StandardErrorResponse, "description": "Video file exceeds upload limit"},
    },
)
async def create_video_job(
    file: UploadFile = File(..., description="Video file to soundtrack"),
    style: Optional[str] = Form(None, description="Optional style preference"),
    prompt_override: Optional[str] = Form(None, description="Optional custom prompt instructions"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Analyze video, create music plan, and enqueue music generation job."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_FILENAME",
                "message": "Upload filename must be provided.",
                "retryable": False,
                "details": {},
            },
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UPLOAD_READ_FAILED",
                "message": f"Failed to read uploaded video file: {exc}",
                "retryable": False,
                "details": {},
            },
        )

    analyzer = VideoAnalyzer(max_upload_size_bytes=settings.max_upload_size_bytes)
    arranger = VideoArranger()

    try:
        analysis = analyzer.analyze_bytes(content, filename=file.filename)
        plan = arranger.create_plan(
            analysis=analysis,
            style_preference=style,
            custom_prompt_override=prompt_override,
        )
    except VideoAnalysisException as e:
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if e.code == "PAYLOAD_TOO_LARGE" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": e.code,
                "message": e.message,
                "retryable": False,
                "details": e.details,
            },
        )

    # Construct standard MusicJobRequest
    job_req = MusicJobRequest(
        prompt=plan.prompt,
        duration_s=plan.target_duration_s,
        sections=plan.sections,
        tempo_bpm=plan.tempo_bpm,
        key=plan.key,
        loopable=False,
    )

    req_json = json.dumps(job_req.model_dump(), sort_keys=True)
    req_hash = hashlib.sha256(req_json.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check Idempotency-Key
    if idempotency_key:
        existing = db.query(MusicJob).filter(MusicJob.idempotency_key == idempotency_key).first()
        if existing:
            if existing.request_hash == req_hash:
                logger.info("Idempotent hit for key '%s': returning existing job %s", idempotency_key, existing.id)
                return VideoJobAcceptedResponse(
                    job_id=existing.id,
                    status=existing.status,
                    progress=existing.progress,
                    created_at=existing.created_at.isoformat(),
                    message="Existing job returned for identical Idempotency-Key",
                )
            else:
                logger.warning("Idempotency conflict: key '%s' reused with differing request payload", idempotency_key)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": f"Idempotency-Key '{idempotency_key}' was previously used with a different request payload.",
                        "retryable": False,
                        "details": {"idempotency_key": idempotency_key},
                    },
                )

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    new_job = MusicJob(
        id=job_id,
        idempotency_key=idempotency_key,
        request_hash=req_hash,
        prompt=job_req.prompt,
        duration_s=job_req.duration_s,
        status="queued",
        progress=0,
        request_json=req_json,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    logger.info("Created Video-to-Beat job %s (Duration: %.2fs, Prompt: '%s')", job_id, job_req.duration_s, job_req.prompt)

    # Enqueue background execution via existing job dispatcher
    dispatch_job(job_id)

    plan_resp = MusicPlanResponse(
        genre=plan.genre,
        mood=plan.mood,
        tempo_bpm=plan.tempo_bpm,
        key=plan.key,
        rhythmic_style=plan.rhythmic_style,
        intensity=plan.intensity,
        instrumentation=plan.instrumentation,
        target_duration_s=plan.target_duration_s,
        sections=plan.sections,
        accents=[
            MusicalAccentResponse(
                timestamp_s=acc.timestamp_s,
                event_description=acc.event_description,
                musical_action=acc.musical_action,
            )
            for acc in plan.accents
        ],
        prompt=plan.prompt,
    )

    metadata_resp = VideoMetadataResponse(
        filename=analysis.metadata.filename,
        duration_s=analysis.metadata.duration_s,
        fps=analysis.metadata.fps,
        width=analysis.metadata.width,
        height=analysis.metadata.height,
        frame_count=analysis.metadata.frame_count,
        aspect_ratio=analysis.metadata.aspect_ratio,
        file_size_bytes=analysis.metadata.file_size_bytes,
    )

    return VideoJobAcceptedResponse(
        job_id=job_id,
        status="queued",
        progress=0,
        created_at=now_iso,
        message="Video analyzed and soundtrack generation queued",
        plan=plan_resp,
        video_metadata=metadata_resp,
    )
