"""Automated tests for VideoArranger musical arrangement and timing plan engine."""
import pytest
from src.video.analyzer import (
    VideoMetadata,
    VideoActivityMetrics,
    VideoAnalysisResult,
    KeyframeThumbnail,
)
from src.video.arranger import VideoArranger, MusicPlan
from src.models import MusicJobRequest


def make_mock_analysis(duration_s: float = 20.0, cuts: list = None, pacing: str = "moderate"):
    cuts = cuts if cuts is not None else [0.0, 5.0, 11.0, 16.5]
    metadata = VideoMetadata(
        filename="clip.mp4",
        duration_s=duration_s,
        fps=24.0,
        width=1920,
        height=1080,
        frame_count=int(duration_s * 24),
        aspect_ratio="16:9",
        file_size_bytes=1024 * 1024,
    )
    activity = VideoActivityMetrics(
        avg_motion=0.18,
        max_motion=0.45,
        motion_variance=0.008,
        avg_brightness=0.62,
        avg_saturation=0.55,
        warm_color_ratio=0.48,
        pacing=pacing,
        detected_mood="uplifting & warm",
    )
    keyframes = [KeyframeThumbnail(timestamp_s=0.0, data_uri="data:image/jpeg;base64,...")]
    accents = [5.0, 11.0]

    return VideoAnalysisResult(
        metadata=metadata,
        scene_cuts=cuts,
        activity=activity,
        keyframes=keyframes,
        accent_timestamps=accents,
        audio_present=False,
    )


def test_video_arranger_creates_valid_plan():
    """Verify VideoArranger generates valid MusicPlan with accurate duration and valid section gaps."""
    analysis = make_mock_analysis(duration_s=30.0)
    arranger = VideoArranger()

    plan = arranger.create_plan(analysis, style_preference="cinematic")

    assert isinstance(plan, MusicPlan)
    assert plan.genre == "Cinematic Orchestral"
    assert plan.target_duration_s == 30.0
    assert 60 <= plan.tempo_bpm <= 160
    assert len(plan.key) > 0
    assert len(plan.sections) >= 2
    assert plan.sections[0].start_s == 0.0

    # Verify all sections respect the 1.5s separation rule and stay <= duration
    for i in range(1, len(plan.sections)):
        gap = plan.sections[i].start_s - plan.sections[i - 1].start_s
        assert gap >= 1.5, f"Section gap too small: {gap}s"
        assert plan.sections[i].start_s <= 30.0

    # Ensure plan can be passed directly to MusicJobRequest without validation error
    job_req = MusicJobRequest(
        prompt=plan.prompt,
        duration_s=plan.target_duration_s,
        sections=plan.sections,
        tempo_bpm=plan.tempo_bpm,
        key=plan.key,
    )
    assert job_req.duration_s == 30.0


def test_video_arranger_automatic_style_inference():
    """Verify style selection automatically adapts to visual mood and pacing."""
    arranger = VideoArranger()

    # Fast-paced test
    fast_analysis = make_mock_analysis(duration_s=15.0, pacing="fast-paced")
    fast_plan = arranger.create_plan(fast_analysis, style_preference=None)
    assert fast_plan.tempo_bpm >= 100

    # Short video (e.g. 6.0s) produces valid sections
    short_analysis = make_mock_analysis(duration_s=6.0, cuts=[0.0, 2.5])
    short_plan = arranger.create_plan(short_analysis)
    assert short_plan.target_duration_s == 6.0
    assert len(short_plan.sections) >= 1
