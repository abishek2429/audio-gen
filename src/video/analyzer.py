"""Video analysis pipeline utilizing computer vision for timing, pacing, and mood extraction."""
import base64
import logging
import math
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}


class VideoAnalysisException(Exception):
    """Raised when video validation or CV analysis fails."""
    def __init__(self, message: str, code: str = "VIDEO_ANALYSIS_FAILED", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


@dataclass
class KeyframeThumbnail:
    """Representative video keyframe thumbnail."""
    timestamp_s: float
    data_uri: str


@dataclass
class VideoMetadata:
    """Core video file metadata."""
    filename: str
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int
    aspect_ratio: str
    file_size_bytes: int


@dataclass
class VideoActivityMetrics:
    """Visual motion and pacing metrics across the video."""
    avg_motion: float
    max_motion: float
    motion_variance: float
    avg_brightness: float
    avg_saturation: float
    warm_color_ratio: float
    pacing: str  # 'slow', 'moderate', 'fast-paced'
    detected_mood: str


@dataclass
class VideoAnalysisResult:
    """Complete structured video analysis output."""
    metadata: VideoMetadata
    scene_cuts: List[float]
    activity: VideoActivityMetrics
    keyframes: List[KeyframeThumbnail]
    accent_timestamps: List[float]
    audio_present: bool = False


class VideoAnalyzer:
    """Extracts duration, scene cuts, pacing, motion dynamics, and keyframes from video files."""

    def __init__(
        self,
        max_upload_size_bytes: int = 52428800,  # 50 MB
        min_duration_s: float = 1.0,
        max_duration_s: float = 300.0,
        sample_fps: float = 2.0,
    ):
        self.max_upload_size_bytes = max_upload_size_bytes
        self.min_duration_s = min_duration_s
        self.max_duration_s = max_duration_s
        self.sample_fps = sample_fps

    def analyze_bytes(self, video_bytes: bytes, filename: str = "upload.mp4") -> VideoAnalysisResult:
        """Analyze video content from in-memory bytes via an ephemeral tempfile."""
        if not video_bytes or len(video_bytes) == 0:
            raise VideoAnalysisException("Uploaded video file is empty (0 bytes).", code="EMPTY_VIDEO_FILE")

        if len(video_bytes) > self.max_upload_size_bytes:
            raise VideoAnalysisException(
                f"Video file size ({len(video_bytes)} bytes) exceeds maximum limit of {self.max_upload_size_bytes} bytes.",
                code="PAYLOAD_TOO_LARGE",
                details={"size_bytes": len(video_bytes), "max_bytes": self.max_upload_size_bytes},
            )

        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_VIDEO_EXTENSIONS:
            raise VideoAnalysisException(
                f"Unsupported video format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}",
                code="UNSUPPORTED_VIDEO_FORMAT",
                details={"extension": ext, "supported": list(SUPPORTED_VIDEO_EXTENSIONS)},
            )

        temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(temp_fd, "wb") as f:
                f.write(video_bytes)
            return self.analyze_file(temp_path, original_filename=filename)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning("Failed to clean up ephemeral video tempfile '%s': %s", temp_path, e)

    def analyze_file(self, video_path: str, original_filename: Optional[str] = None) -> VideoAnalysisResult:
        """Extract visual metadata, scenes, pacing, and representative keyframes from a video file."""
        if not os.path.exists(video_path):
            raise VideoAnalysisException(f"Video file not found: {video_path}", code="FILE_NOT_FOUND")

        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise VideoAnalysisException("Video file is empty (0 bytes).", code="EMPTY_VIDEO_FILE")

        if file_size > self.max_upload_size_bytes:
            raise VideoAnalysisException(
                f"Video file size ({file_size} bytes) exceeds maximum limit of {self.max_upload_size_bytes} bytes.",
                code="PAYLOAD_TOO_LARGE",
                details={"size_bytes": file_size, "max_bytes": self.max_upload_size_bytes},
            )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise VideoAnalysisException(
                "Unable to decode video file. The file may be corrupted, truncated, or encoded with an unsupported codec.",
                code="INVALID_VIDEO_FILE",
            )

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if fps <= 0 or math.isnan(fps) or math.isinf(fps):
                fps = 24.0

            if frame_count <= 0 or width <= 0 or height <= 0:
                # Attempt to count frames manually if metadata is missing
                frames_counted = 0
                sample_w, sample_h = 0, 0
                while cap.isOpened():
                    ret, fr = cap.read()
                    if not ret:
                        break
                    frames_counted += 1
                    if sample_w == 0:
                        sample_h, sample_w = fr.shape[:2]
                    if frames_counted > 3000:
                        break
                if frames_counted == 0:
                    raise VideoAnalysisException(
                        "Video stream contains no readable frames or is corrupted.",
                        code="EMPTY_VIDEO_STREAM",
                    )
                frame_count = frames_counted
                width = sample_w if width <= 0 else width
                height = sample_h if height <= 0 else height
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            duration_s = round(frame_count / fps, 2)

            if duration_s < self.min_duration_s or duration_s > self.max_duration_s:
                raise VideoAnalysisException(
                    f"Video duration of {duration_s:.2f}s is outside supported range ({self.min_duration_s:.1f}s to {self.max_duration_s:.1f}s).",
                    code="DURATION_OUT_OF_BOUNDS",
                    details={"duration_s": duration_s, "min_s": self.min_duration_s, "max_s": self.max_duration_s},
                )

            aspect_ratio = self._calculate_aspect_ratio(width, height)
            filename = original_filename or os.path.basename(video_path)

            metadata = VideoMetadata(
                filename=filename,
                duration_s=duration_s,
                fps=round(fps, 2),
                width=width,
                height=height,
                frame_count=frame_count,
                aspect_ratio=aspect_ratio,
                file_size_bytes=file_size,
            )

            # Sample frames and perform visual content analysis
            scene_cuts, activity, keyframes, accents = self._process_frames(cap, fps, frame_count, duration_s)

            return VideoAnalysisResult(
                metadata=metadata,
                scene_cuts=scene_cuts,
                activity=activity,
                keyframes=keyframes,
                accent_timestamps=accents,
                audio_present=False,  # VideoCapture does not read audio streams
            )

        finally:
            cap.release()

    def _calculate_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate human-readable aspect ratio."""
        if width <= 0 or height <= 0:
            return "unknown"
        gcd = math.gcd(width, height)
        w_ratio = width // gcd
        h_ratio = height // gcd
        # Normalize common broadcast standards
        ratio_val = width / height
        if abs(ratio_val - (16 / 9)) < 0.05:
            return "16:9"
        if abs(ratio_val - (9 / 16)) < 0.05:
            return "9:16"
        if abs(ratio_val - 1.0) < 0.05:
            return "1:1"
        if abs(ratio_val - (4 / 3)) < 0.05:
            return "4:3"
        return f"{w_ratio}:{h_ratio}"

    def _process_frames(
        self, cap: cv2.VideoCapture, fps: float, total_frames: int, duration_s: float
    ) -> Tuple[List[float], VideoActivityMetrics, List[KeyframeThumbnail], List[float]]:
        """Sample video frames to detect scene cuts, motion dynamics, visual mood, and keyframes."""
        sample_step = max(1, int(round(fps / self.sample_fps)))
        frame_idx = 0

        prev_hist: Optional[np.ndarray] = None
        prev_gray_small: Optional[np.ndarray] = None

        scene_cuts: List[float] = [0.0]  # First section always starts at 0.0s
        motion_scores: List[float] = []
        brightness_scores: List[float] = []
        saturation_scores: List[float] = []
        warm_scores: List[float] = []
        timestamps: List[float] = []

        # Keyframe candidate collection
        keyframe_indices = set()
        desired_keyframes = min(5, max(3, int(duration_s / 10.0)))
        step_kf = max(1, total_frames // (desired_keyframes + 1))
        for i in range(1, desired_keyframes + 1):
            keyframe_indices.add(min(total_frames - 1, i * step_kf))
        keyframe_indices.add(0)

        collected_keyframes: List[KeyframeThumbnail] = []

        while cap.isOpened() and frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break

            t_sec = round(frame_idx / fps, 2)

            # Collect keyframe thumbnail
            if frame_idx in keyframe_indices and len(collected_keyframes) < 6:
                kf_thumb = self._generate_keyframe_data_uri(frame)
                collected_keyframes.append(KeyframeThumbnail(timestamp_s=t_sec, data_uri=kf_thumb))
                keyframe_indices.discard(frame_idx)

            # Analyze on sample step
            if frame_idx % sample_step == 0:
                timestamps.append(t_sec)
                small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
                gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

                # 1. Color and Brightness Metrics
                h_chan = hsv[:, :, 0]
                s_chan = hsv[:, :, 1]
                v_chan = hsv[:, :, 2]

                brightness = float(np.mean(v_chan) / 255.0)
                saturation = float(np.mean(s_chan) / 255.0)
                brightness_scores.append(brightness)
                saturation_scores.append(saturation)

                # Warm hues: reds/oranges/yellows in HSV [0-30] or [150-180]
                warm_mask = ((h_chan <= 30) | (h_chan >= 150)) & (s_chan > 40)
                warm_ratio = float(np.sum(warm_mask) / warm_mask.size)
                warm_scores.append(warm_ratio)

                # 2. Motion score via frame difference
                if prev_gray_small is not None:
                    diff = cv2.absdiff(prev_gray_small, gray_small)
                    motion = float(np.mean(diff) / 255.0)
                else:
                    motion = 0.0
                motion_scores.append(motion)
                prev_gray_small = gray_small

                # 3. Scene Cut Detection via HSV Histogram Correlation
                hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                if prev_hist is not None:
                    similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    # If visual correlation drops below 0.62 and at least 1.5s since last cut
                    if similarity < 0.62:
                        if len(scene_cuts) == 0 or (t_sec - scene_cuts[-1]) >= 1.5:
                            if t_sec < duration_s - 1.0:
                                scene_cuts.append(t_sec)
                prev_hist = hist

            frame_idx += 1

        # Summary Metrics
        avg_motion = float(np.mean(motion_scores)) if motion_scores else 0.05
        max_motion = float(np.max(motion_scores)) if motion_scores else 0.1
        motion_var = float(np.var(motion_scores)) if motion_scores else 0.01

        avg_bright = float(np.mean(brightness_scores)) if brightness_scores else 0.5
        avg_sat = float(np.mean(saturation_scores)) if saturation_scores else 0.4
        avg_warm = float(np.mean(warm_scores)) if warm_scores else 0.3

        # Determine Pacing
        cut_freq = len(scene_cuts) / max(1.0, duration_s)
        if cut_freq >= 0.25 or avg_motion >= 0.20:
            pacing = "fast-paced"
        elif cut_freq <= 0.08 and avg_motion <= 0.07:
            pacing = "slow"
        else:
            pacing = "moderate"

        # Determine Visual Mood
        if avg_motion >= 0.20:
            detected_mood = "energetic & dynamic"
        elif avg_bright < 0.35:
            detected_mood = "dark & atmospheric"
        elif avg_warm > 0.45 and avg_bright > 0.50:
            detected_mood = "uplifting & warm"
        elif avg_sat < 0.20:
            detected_mood = "melancholic & reflective"
        else:
            detected_mood = "modern & cinematic"

        activity = VideoActivityMetrics(
            avg_motion=round(avg_motion, 4),
            max_motion=round(max_motion, 4),
            motion_variance=round(motion_var, 6),
            avg_brightness=round(avg_bright, 4),
            avg_saturation=round(avg_sat, 4),
            warm_color_ratio=round(avg_warm, 4),
            pacing=pacing,
            detected_mood=detected_mood,
        )

        # Identify Accent Timestamps (moments for musical drops or accents)
        accent_timestamps = self._extract_accent_timestamps(
            timestamps, motion_scores, scene_cuts, duration_s, avg_motion
        )

        # Sort keyframes chronologically
        collected_keyframes.sort(key=lambda kf: kf.timestamp_s)

        return scene_cuts, activity, collected_keyframes, accent_timestamps

    def _extract_accent_timestamps(
        self,
        timestamps: List[float],
        motion_scores: List[float],
        scene_cuts: List[float],
        duration_s: float,
        avg_motion: float,
    ) -> List[float]:
        """Identify candidate accent/drop points aligning with major visual transitions."""
        accents: List[float] = []
        if not motion_scores or len(motion_scores) != len(timestamps):
            return accents

        # Detect motion peaks (motion > mean + 1.25 * std)
        motion_std = float(np.std(motion_scores))
        threshold = avg_motion + 1.25 * motion_std

        candidate_accents: List[Tuple[float, float]] = []
        for t, m in zip(timestamps, motion_scores):
            if m > threshold and 2.0 <= t <= (duration_s - 2.0):
                candidate_accents.append((t, m))

        # Add major scene cut points (excluding intro at 0.0s)
        for cut in scene_cuts[1:]:
            if 2.0 <= cut <= (duration_s - 2.0):
                candidate_accents.append((cut, threshold + 0.05))

        # Sort candidates by intensity descending
        candidate_accents.sort(key=lambda x: x[1], reverse=True)

        # Select top accents spaced at least 3.0 seconds apart
        for t, _ in candidate_accents:
            if all(abs(t - existing) >= 3.0 for existing in accents):
                accents.append(round(t, 2))
                if len(accents) >= 4:
                    break

        accents.sort()
        return accents

    def _generate_keyframe_data_uri(self, frame: np.ndarray) -> str:
        """Encode a frame as a compact JPEG data URI."""
        thumb = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        ret, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ret:
            return ""
        b64 = base64.b64encode(buf).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
