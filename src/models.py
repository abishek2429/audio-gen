"""Data models and OpenAPI 3.1 schemas for IncuBrix AI Background Music Engine."""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class SectionPlan(BaseModel):
    """Mood change section at a specific video cut point."""
    model_config = ConfigDict(extra="forbid")
    start_s: float = Field(..., ge=0.0, description="Start time in seconds")
    mood: str = Field(..., min_length=1, description="Mood or instrumentation instruction for this section")


class OutputConfig(BaseModel):
    """Audio rendering and format settings."""
    model_config = ConfigDict(extra="forbid")
    sample_rate: int = Field(default=48000, description="Target sample rate in Hz (default: 48000)")
    target_lufs: float = Field(default=-16.0, description="Target integrated loudness in LUFS (default: -16.0)")
    formats: List[str] = Field(default_factory=lambda: ["wav", "mp3"], description="Output container formats")

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        if v not in (44100, 48000):
            raise ValueError(f"Unsupported sample_rate: {v}. Supported rates are 44100 and 48000 Hz.")
        return v

    @field_validator("target_lufs")
    @classmethod
    def validate_target_lufs(cls, v: float) -> float:
        if not (-30.0 <= v <= -6.0):
            raise ValueError(f"target_lufs ({v}) must be between -30.0 and -6.0 LUFS.")
        return v

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: List[str]) -> List[str]:
        valid_formats = {"wav", "mp3"}
        for fmt in v:
            if fmt.lower() not in valid_formats:
                raise ValueError(f"Unsupported format '{fmt}'. Supported formats are 'wav' and 'mp3'.")
        return [fmt.lower() for fmt in v]


class MusicJobRequest(BaseModel):
    """Primary request payload matching the IncuBrix Integration Standard."""
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(..., min_length=1, description="Text prompt describing mood, genre, and instrumentation")
    duration_s: float = Field(..., ge=5.0, le=300.0, description="Duration in seconds (5.0 to 300.0s)")
    sections: Optional[List[SectionPlan]] = Field(default=None, description="Optional mood changes at video edit points")
    tempo_bpm: Optional[int] = Field(default=None, ge=40, le=240, description="Optional fixed tempo in BPM")
    key: Optional[str] = Field(default=None, description="Optional musical key (e.g., 'C major', 'A minor')")
    loopable: bool = Field(default=False, description="Whether audio must loop seamlessly")
    narration_url: Optional[str] = Field(default=None, description="Optional URL to voiceover audio for auto-ducking")
    callback_url: Optional[str] = Field(default=None, description="Optional webhook URL to receive HMAC-signed job completion")
    seed: Optional[int] = Field(default=None, description="Optional random seed for reproducible synthesis")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output audio configuration")

    @model_validator(mode="after")
    def validate_sections_timing(self) -> "MusicJobRequest":
        if self.sections:
            sorted_sections = sorted(self.sections, key=lambda s: s.start_s)
            for i, sec in enumerate(sorted_sections):
                if sec.start_s > self.duration_s:
                    raise ValueError(
                        f"Section start_s ({sec.start_s}s) begins after requested track duration ({self.duration_s}s)."
                    )
                if i > 0:
                    gap = sec.start_s - sorted_sections[i - 1].start_s
                    if gap < 1.5:
                        raise ValueError(
                            f"Sections must be at least 1.5 seconds apart to allow musical transitions; "
                            f"sections at {sorted_sections[i - 1].start_s}s and {sec.start_s}s have gap {gap:.2f}s."
                        )
        return self


class JobAcceptedResponse(BaseModel):
    """HTTP 202 Accepted response returned on job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(default="queued", description="Initial job status ('queued')")
    progress: int = Field(default=0, ge=0, le=100, description="Job progress percentage (0-100)")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    message: str = Field(default="Job accepted and queued for processing", description="Human-readable status message")


class JobResultURLs(BaseModel):
    """Download links to finished audio assets."""
    mix_wav: str = Field(..., description="Direct download URL for finished 48kHz mix.wav")
    mix_mp3: Optional[str] = Field(default=None, description="Download URL for finished mix.mp3")
    mix_ducked_wav: Optional[str] = Field(default=None, description="Download URL for narration-ducked mix.wav")
    stems: Dict[str, str] = Field(default_factory=dict, description="Download URLs for individual instrument stems")
    manifest: str = Field(..., description="Download URL for music_manifest.json")
    validation_report: Optional[str] = Field(default=None, description="Download URL for validation_report.json")


class ErrorDetail(BaseModel):
    """Standardized error structure per Integration Standard Point 5."""
    code: str = Field(..., description="UPPER_SNAKE_CASE error code")
    message: str = Field(..., description="Descriptive error message")
    retryable: bool = Field(default=False, description="Whether the request can be safely retried")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context or validation details")


class StandardErrorResponse(BaseModel):
    """Root error response schema."""
    error: ErrorDetail


class JobStatusResponse(BaseModel):
    """Detailed job status returned by GET /api/v1/jobs/{job_id}."""
    job_id: str
    status: str = Field(..., description="Status: 'queued', 'running', 'succeeded', 'failed'")
    progress: int = Field(..., ge=0, le=100, description="Progress from 0 to 100")
    result: Optional[JobResultURLs] = None
    manifest: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None
    created_at: str
    updated_at: str


class MusicManifest(BaseModel):
    """Comprehensive metadata manifest delivered with every finished music job."""
    job_id: str
    prompt: str
    requested_duration_s: float
    actual_duration_s: float
    sample_rate: int
    tempo_bpm: int
    key: str
    sections: List[Dict[str, Any]]
    beat_grid_s: List[float]
    stems: Dict[str, str]
    stem_gains: Dict[str, float]
    models: Dict[str, str]
    provider: str
    seed: Optional[int] = None
    audio_metrics: Dict[str, float]
    timings_s: Dict[str, float]
    cost_usd: float
    commercial_license: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class GateResult(BaseModel):
    """Single quality gate evaluation."""
    passed: bool
    details: Dict[str, Any]


class ValidationReport(BaseModel):
    """Mathematical audio verification report evaluating all IncuBrix Must-Have criteria."""
    job_id: str
    overall_passed: bool
    evaluated_at: str
    gates: Dict[str, GateResult]
    summary: str


class VideoMetadataResponse(BaseModel):
    """Video file metadata returned by video analysis."""
    filename: str
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int
    aspect_ratio: str
    file_size_bytes: int


class VideoActivityResponse(BaseModel):
    """Motion, visual pacing, and mood metrics."""
    avg_motion: float
    max_motion: float
    motion_variance: float
    avg_brightness: float
    avg_saturation: float
    warm_color_ratio: float
    pacing: str
    detected_mood: str


class KeyframeThumbnailResponse(BaseModel):
    """Timestamped keyframe thumbnail encoded as a base64 JPEG data URI."""
    timestamp_s: float
    data_uri: str


class MusicalAccentResponse(BaseModel):
    """Timestamped musical accent cue aligned with a visual cut or motion event."""
    timestamp_s: float
    event_description: str
    musical_action: str


class MusicPlanResponse(BaseModel):
    """Recommended musical arrangement plan generated from video analysis."""
    genre: str
    mood: str
    tempo_bpm: int
    key: str
    rhythmic_style: str
    intensity: str
    instrumentation: List[str]
    target_duration_s: float
    sections: List[SectionPlan]
    accents: List[MusicalAccentResponse]
    prompt: str


class VideoAnalysisResponse(BaseModel):
    """Complete video analysis and recommended musical arrangement plan."""
    metadata: VideoMetadataResponse
    scene_cuts: List[float]
    activity: VideoActivityResponse
    keyframes: List[KeyframeThumbnailResponse]
    accent_timestamps: List[float]
    audio_present: bool = False
    recommended_plan: MusicPlanResponse


class VideoJobAcceptedResponse(JobAcceptedResponse):
    """Response returned upon submitting a Video-to-Beat generation job."""
    plan: Optional[MusicPlanResponse] = None
    video_metadata: Optional[VideoMetadataResponse] = None

