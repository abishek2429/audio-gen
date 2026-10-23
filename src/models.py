"""Data models and schemas for IncuBrix AI Background Music Engine."""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class SectionPlan(BaseModel):
    """Mood change section at a specific edit point."""
    start_s: float = Field(..., ge=0.0, description="Start time in seconds")
    mood: str = Field(..., description="Mood or instrumentation instruction for this section")


class OutputConfig(BaseModel):
    """Audio rendering and format settings."""
    sample_rate: int = Field(default=48000, description="Target sample rate in Hz")
    target_lufs: float = Field(default=-16.0, description="Target integrated loudness in LUFS")
    formats: List[str] = Field(default_factory=lambda: ["wav", "mp3"], description="Output container formats")


class MusicJobRequest(BaseModel):
    """Primary request payload matching the IncuBrix Integration Standard."""
    prompt: str = Field(..., min_length=1, description="Text prompt describing mood, genre, and instrumentation")
    duration_s: float = Field(..., ge=5.0, le=300.0, description="Duration in seconds (5.0 to 300.0s)")
    sections: Optional[List[SectionPlan]] = Field(default=None, description="Optional mood changes at video edit points")
    tempo_bpm: Optional[int] = Field(default=None, ge=40, le=240, description="Optional fixed tempo in BPM")
    key: Optional[str] = Field(default=None, description="Optional musical key (e.g., 'C major', 'A minor')")
    loopable: bool = Field(default=False, description="Whether audio must loop seamlessly")
    narration_url: Optional[str] = Field(default=None, description="Optional URL to voiceover audio for auto-ducking")
    seed: Optional[int] = Field(default=None, description="Optional random seed for reproducible synthesis")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output audio configuration")


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
