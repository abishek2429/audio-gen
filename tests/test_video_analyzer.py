"""Automated tests for VideoAnalyzer computer vision pipeline."""
import os
import tempfile
import cv2
import numpy as np
import pytest

from src.video.analyzer import (
    VideoAnalyzer,
    VideoAnalysisException,
    VideoAnalysisResult,
)


def generate_test_video_bytes(
    duration_s: float = 4.0,
    fps: float = 24.0,
    width: int = 320,
    height: int = 240,
    scene_cuts_at: list = None,
) -> bytes:
    """Helper to synthesize an MP4 video in memory with controlled cuts and motion."""
    scene_cuts_at = scene_cuts_at or [2.0]
    total_frames = int(round(duration_s * fps))

    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

        current_color = (30, 40, 200)  # Reddish
        cut_frames = {int(round(c * fps)) for c in scene_cuts_at}

        for f_idx in range(total_frames):
            if f_idx in cut_frames:
                current_color = (200, 150, 20) if current_color[0] == 30 else (30, 40, 200)

            frame = np.full((height, width, 3), current_color, dtype=np.uint8)
            # Add dynamic motion
            circle_x = int((f_idx * 12) % width)
            cv2.circle(frame, (circle_x, height // 2), 25, (255, 255, 255), -1)
            writer.write(frame)

        writer.release()

        with open(path, "rb") as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_video_analyzer_valid_video():
    """Verify video analyzer correctly extracts metadata, cuts, pacing, and keyframes."""
    video_bytes = generate_test_video_bytes(duration_s=6.0, fps=24.0, scene_cuts_at=[2.5, 4.5])
    analyzer = VideoAnalyzer()

    result = analyzer.analyze_bytes(video_bytes, filename="sample_clip.mp4")

    assert isinstance(result, VideoAnalysisResult)
    assert result.metadata.filename == "sample_clip.mp4"
    assert abs(result.metadata.duration_s - 6.0) <= 0.15
    assert result.metadata.fps == 24.0
    assert result.metadata.width == 320
    assert result.metadata.height == 240
    assert result.metadata.aspect_ratio == "4:3"

    # Verify scene cut detection
    assert len(result.scene_cuts) >= 2
    assert result.scene_cuts[0] == 0.0
    # One of the detected cuts should be near 2.5s
    has_cut_near_2_5 = any(abs(c - 2.5) <= 0.8 for c in result.scene_cuts)
    assert has_cut_near_2_5

    # Verify activity and visual metrics
    assert result.activity.avg_motion >= 0.0
    assert result.activity.pacing in ("slow", "moderate", "fast-paced")
    assert len(result.activity.detected_mood) > 0

    # Verify keyframe thumbnails
    assert len(result.keyframes) >= 2
    for kf in result.keyframes:
        assert kf.data_uri.startswith("data:image/jpeg;base64,")
        assert 0.0 <= kf.timestamp_s <= result.metadata.duration_s


def test_video_analyzer_rejects_empty_file():
    """Verify 0-byte video file is safely rejected with descriptive exception."""
    analyzer = VideoAnalyzer()
    with pytest.raises(VideoAnalysisException) as exc_info:
        analyzer.analyze_bytes(b"", filename="empty.mp4")

    assert exc_info.value.code == "EMPTY_VIDEO_FILE"


def test_video_analyzer_rejects_unsupported_extension():
    """Verify unsupported file extensions are safely rejected."""
    analyzer = VideoAnalyzer()
    with pytest.raises(VideoAnalysisException) as exc_info:
        analyzer.analyze_bytes(b"dummy data", filename="song.mp3")

    assert exc_info.value.code == "UNSUPPORTED_VIDEO_FORMAT"


def test_video_analyzer_rejects_payload_too_large():
    """Verify files exceeding max size limit are rejected."""
    analyzer = VideoAnalyzer(max_upload_size_bytes=100)
    with pytest.raises(VideoAnalysisException) as exc_info:
        analyzer.analyze_bytes(b"X" * 150, filename="video.mp4")

    assert exc_info.value.code == "PAYLOAD_TOO_LARGE"


def test_video_analyzer_rejects_corrupted_video():
    """Verify corrupted non-video bytes are safely rejected without crash."""
    analyzer = VideoAnalyzer()
    with pytest.raises(VideoAnalysisException) as exc_info:
        analyzer.analyze_bytes(b"NOT_A_VALID_MP4_HEADER_RANDOM_GARBAGE_BYTES_1234567890", filename="corrupt.mp4")

    assert exc_info.value.code in ("INVALID_VIDEO_FILE", "EMPTY_VIDEO_STREAM")


def test_video_analyzer_duration_boundary_rejection():
    """Verify videos outside min/max duration bounds are rejected."""
    # 0.5s video when min is 2.0s
    short_video = generate_test_video_bytes(duration_s=0.5, fps=24.0)
    analyzer = VideoAnalyzer(min_duration_s=2.0)

    with pytest.raises(VideoAnalysisException) as exc_info:
        analyzer.analyze_bytes(short_video, filename="too_short.mp4")

    assert exc_info.value.code == "DURATION_OUT_OF_BOUNDS"
