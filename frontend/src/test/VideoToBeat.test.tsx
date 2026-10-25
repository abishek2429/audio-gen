import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MusicGeneratorView } from "../views/MusicGeneratorView";
import { VideoToBeatView } from "../views/VideoToBeatView";
import { AudioStudioView } from "../views/AudioStudioView";
import { apiClient } from "../services/apiClient";
import type { VideoAnalysisResponse, JobStatusResponse } from "../types/api";

const mockAnalysisResult: VideoAnalysisResponse = {
  metadata: {
    filename: "sample_video.mp4",
    duration_s: 24.5,
    fps: 30.0,
    width: 1920,
    height: 1080,
    frame_count: 735,
    aspect_ratio: "16:9",
    file_size_bytes: 10485760,
  },
  scene_cuts: [0.0, 6.2, 14.5, 20.0],
  activity: {
    avg_motion: 0.18,
    max_motion: 0.42,
    motion_variance: 0.007,
    avg_brightness: 0.65,
    avg_saturation: 0.52,
    warm_color_ratio: 0.48,
    pacing: "moderate",
    detected_mood: "uplifting & warm",
  },
  keyframes: [
    { timestamp_s: 0.0, data_uri: "data:image/jpeg;base64,keyframe1" },
    { timestamp_s: 6.2, data_uri: "data:image/jpeg;base64,keyframe2" },
  ],
  accent_timestamps: [6.2, 14.5],
  audio_present: false,
  recommended_plan: {
    genre: "Uplifting Acoustic & Tech",
    mood: "uplifting & warm",
    tempo_bpm: 118,
    key: "C major",
    rhythmic_style: "Bright syncopated acoustic groove with light hand percussion",
    intensity: "medium",
    instrumentation: ["bright acoustic guitars", "warm upright piano"],
    target_duration_s: 24.5,
    sections: [
      { start_s: 0.0, mood: "gentle intro" },
      { start_s: 6.2, mood: "build-up" },
      { start_s: 14.5, mood: "energetic peak drop" },
    ],
    accents: [
      { timestamp_s: 6.2, event_description: "cut", musical_action: "percussive drop" },
    ],
    prompt: "uplifting tech corporate acoustic, bright acoustic guitar picking, 24.5s",
  },
};

describe("Video-to-Beat Frontend Integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Mock URL.createObjectURL and revokeObjectURL in jsdom
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/sample-video");
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  it("allows switching between Prompt to Music and Video-to-Beat modes", () => {
    const onJobCreated = vi.fn();
    render(<MusicGeneratorView onJobCreated={onJobCreated} />);

    // Default: Prompt to Music
    expect(screen.getByLabelText(/Music Description & Mood/i)).toBeInTheDocument();

    // Click Video-to-Beat tab
    const videoTabBtn = screen.getByRole("button", { name: /Video-to-Beat/i });
    fireEvent.click(videoTabBtn);

    // Verify upload zone is displayed
    expect(screen.getByText(/Upload Video for Soundtrack Generation/i)).toBeInTheDocument();
  });

  it("handles video selection and renders visual analysis metrics and plan", async () => {
    const onJobCreated = vi.fn();
    vi.spyOn(apiClient, "analyzeVideo").mockResolvedValue(mockAnalysisResult);

    render(<VideoToBeatView onJobCreated={onJobCreated} />);

    const file = new File(["fake-mp4-content"], "test_clip.mp4", { type: "video/mp4" });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(apiClient.analyzeVideo).toHaveBeenCalledWith(file, undefined);
    });

    // Check analysis chips
    expect(await screen.findByText(/Exact Duration: 24.50s/i)).toBeInTheDocument();
    expect(screen.getByText(/PACING: MODERATE/i)).toBeInTheDocument();
    expect(screen.getByText(/Mood: uplifting & warm/i)).toBeInTheDocument();
    expect(screen.getByText(/4 Scene Cuts Detected/i)).toBeInTheDocument();

    // Check keyframe thumbnails
    expect(screen.getByAltText(/Keyframe at 0s/i)).toBeInTheDocument();

    // Check arrangement plan
    expect(screen.getByText(/Uplifting Acoustic & Tech/i)).toBeInTheDocument();
    expect(screen.getByText(/118 BPM/i)).toBeInTheDocument();
  });

  it("submits video-to-beat generation job when Generate is clicked", async () => {
    const onJobCreated = vi.fn();
    vi.spyOn(apiClient, "analyzeVideo").mockResolvedValue(mockAnalysisResult);
    vi.spyOn(apiClient, "createVideoJob").mockResolvedValue({
      job_id: "job_video_123",
      status: "queued",
      progress: 0,
      created_at: "2026-10-26T12:00:00Z",
      message: "Queued",
    });

    render(<VideoToBeatView onJobCreated={onJobCreated} />);

    const file = new File(["fake-mp4-content"], "ad.mp4", { type: "video/mp4" });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Exact Duration: 24.50s/i)).toBeInTheDocument();
    });

    const generateBtn = screen.getByRole("button", { name: /Generate Video Soundtrack/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(apiClient.createVideoJob).toHaveBeenCalledWith(
        file,
        undefined,
        expect.any(String),
        expect.stringMatching(/^vid-/)
      );
      expect(onJobCreated).toHaveBeenCalledWith("job_video_123", file);
    });
  });

  it("renders synchronized video audition player in AudioStudioView when video is present", () => {
    const mockJob: JobStatusResponse = {
      job_id: "job_video_finished",
      status: "succeeded",
      progress: 100,
      result: {
        mix_wav: "/storage/job_video_finished/mix.wav",
        stems: { drums: "/storage/job_video_finished/stems/drums.wav" },
        manifest: "/storage/job_video_finished/music_manifest.json",
      },
      manifest: {
        prompt: "uplifting acoustic",
        actual_duration_s: 24.5,
        sample_rate: 48000,
        tempo_bpm: 118,
        audio_metrics: { integrated_lufs: -16.0, true_peak_dbtp: -2.8 },
      },
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:01:00Z",
    };

    render(
      <AudioStudioView
        job={mockJob}
        videoUrl="blob:http://localhost/video-playback"
        videoFile={new File([""], "clip.mp4")}
        onNavigate={vi.fn()}
      />
    );

    // Verify Synchronized Video & Soundtrack Audition panel is rendered
    expect(screen.getByText(/Synchronized Video & Soundtrack Audition/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Play Synced/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Replay/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Video Audio Muted/i })).toBeInTheDocument();
    expect(screen.getByText(/Soundtrack Vol:/i)).toBeInTheDocument();
  });
});
