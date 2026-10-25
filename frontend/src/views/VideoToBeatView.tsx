import React, { useState, useRef, useEffect } from "react";
import {
  Film,
  Upload,
  Sparkles,
  AlertCircle,
  Play,
  Pause,
  Clock,
  Layers,
  Activity,
  Scissors,
  Music,
} from "lucide-react";
import { apiClient, ApiError } from "../services/apiClient";
import type { VideoAnalysisResponse, MusicPlan } from "../types/api";

interface VideoToBeatViewProps {
  onJobCreated: (jobId: string, videoFile?: File) => void;
  isGenerating?: boolean;
}

export const VideoToBeatView: React.FC<VideoToBeatViewProps> = ({
  onJobCreated,
  isGenerating = false,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Analysis & Plan state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResponse | null>(null);
  const [selectedStyle, setSelectedStyle] = useState<string>("auto");
  const [editablePrompt, setEditablePrompt] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Video playback preview state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const styleOptions = [
    { id: "auto", label: "Auto (Match Mood)", icon: Sparkles, desc: "Automatic match based on visual dynamics" },
    { id: "cinematic", label: "Cinematic Orchestral", icon: Film, desc: "Dramatic brass, strings, and hybrid risers" },
    { id: "electronic", label: "Modern Electronic", icon: Activity, desc: "Driving 4/4 beats and pulsating synths" },
    { id: "corporate", label: "Uplifting Acoustic", icon: Sparkles, desc: "Bright acoustic guitars and light piano" },
    { id: "lo_fi", label: "Lo-Fi Chillhop", icon: Music, desc: "Vintage electric piano chords and mellow beats" },
    { id: "ambient", label: "Ambient Atmospheric", icon: Layers, desc: "Serene pads and evolving soundscapes" },
    { id: "action", label: "Driving Action", icon: Activity, desc: "Distorted rock guitars and heavy percussion" },
  ];

  // Clean up object URLs on unmount or file change
  useEffect(() => {
    return () => {
      if (videoPreviewUrl) {
        URL.revokeObjectURL(videoPreviewUrl);
      }
    };
  }, [videoPreviewUrl]);

  const handleFileChange = (file: File) => {
    setError(null);
    const validExtensions = [".mp4", ".mov", ".avi", ".webm", ".mkv"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

    if (!validExtensions.includes(ext)) {
      setError(`Unsupported video format "${ext}". Please upload an MP4, MOV, WEBM, or AVI file.`);
      return;
    }

    if (file.size > 52428800) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the 50 MB limit.`);
      return;
    }

    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }

    const url = URL.createObjectURL(file);
    setSelectedFile(file);
    setVideoPreviewUrl(url);
    setAnalysisResult(null);
    setIsPlaying(false);
    setCurrentTime(0);

    // Automatically trigger initial analysis
    triggerAnalysis(file, selectedStyle);
  };

  const triggerAnalysis = async (file: File, style: string) => {
    setIsAnalyzing(true);
    setError(null);
    try {
      const res = await apiClient.analyzeVideo(
        file,
        style === "auto" ? undefined : style
      );
      setAnalysisResult(res);
      setEditablePrompt(res.recommended_plan.prompt);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || "Failed to analyze video file.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStyleChange = (styleId: string) => {
    setSelectedStyle(styleId);
    if (selectedFile) {
      triggerAnalysis(selectedFile, styleId);
    }
  };

  const handleGenerate = async () => {
    if (!selectedFile) {
      setError("Please select a video file first.");
      return;
    }

    setError(null);
    try {
      const idempotencyKey = `vid-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
      const jobRes = await apiClient.createVideoJob(
        selectedFile,
        selectedStyle === "auto" ? undefined : selectedStyle,
        editablePrompt.trim() || undefined,
        idempotencyKey
      );
      onJobCreated(jobRes.job_id, selectedFile);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || "Failed to submit video-to-beat job.");
      }
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const plan: MusicPlan | undefined = analysisResult?.recommended_plan;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* File Upload Zone */}
      {!selectedFile ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileChange(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? "var(--accent-primary)" : "var(--border-default)"}`,
            borderRadius: "var(--radius-lg)",
            padding: "48px 24px",
            textAlign: "center",
            background: isDragging ? "var(--accent-subtle)" : "var(--bg-panel-subtle)",
            cursor: "pointer",
            transition: "all var(--transition-fast)",
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileChange(e.target.files[0]);
              }
            }}
          />
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "var(--accent-subtle)",
              color: "var(--accent-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 14px",
            }}
          >
            <Upload size={22} />
          </div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "6px" }}>
            Upload Video for Soundtrack Generation
          </h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "440px", margin: "0 auto 12px" }}>
            Drag and drop your video file here or click to browse. The engine extracts exact duration, cut timestamps, visual pacing, and keyframes.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: "10px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
            <span>MP4, MOV, WEBM, AVI</span>
            <span>•</span>
            <span>Max 50 MB</span>
            <span>•</span>
            <span>1.0s to 300.0s</span>
          </div>
        </div>
      ) : (
        /* Video Loaded Dashboard */
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Video Metadata & Live Preview Card */}
          <div className="panel" style={{ padding: "20px 24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Film size={20} color="var(--accent-primary)" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    {analysisResult && ` • ${analysisResult.metadata.width}x${analysisResult.metadata.height} (${analysisResult.metadata.aspect_ratio}) • ${analysisResult.metadata.fps} fps`}
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  setSelectedFile(null);
                  setVideoPreviewUrl(null);
                  setAnalysisResult(null);
                }}
                className="btn btn-secondary btn-sm"
              >
                Change Video
              </button>
            </div>

            {/* Video Player & Timeline Preview */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px" }}>
              <div
                style={{
                  position: "relative",
                  borderRadius: "var(--radius-md)",
                  overflow: "hidden",
                  background: "#000000",
                  aspectRatio: "16 / 9",
                  maxHeight: "360px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {videoPreviewUrl && (
                  <video
                    ref={videoRef}
                    src={videoPreviewUrl}
                    style={{ width: "100%", height: "100%", objectFit: "contain" }}
                    onTimeUpdate={() => {
                      if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
                    }}
                    onEnded={() => setIsPlaying(false)}
                    muted
                    playsInline
                  />
                )}
                {/* Play/Pause Overlay */}
                <button
                  onClick={togglePlay}
                  aria-label={isPlaying ? "Pause video" : "Play video"}
                  style={{
                    position: "absolute",
                    bottom: "16px",
                    left: "16px",
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    background: "rgba(17, 19, 25, 0.85)",
                    border: "1px solid var(--border-default)",
                    color: "#ffffff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    backdropFilter: "blur(4px)",
                  }}
                >
                  {isPlaying ? <Pause size={18} /> : <Play size={18} style={{ marginLeft: "2px" }} />}
                </button>
                <div
                  style={{
                    position: "absolute",
                    bottom: "16px",
                    right: "16px",
                    background: "rgba(17, 19, 25, 0.85)",
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "0.75rem",
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-secondary)",
                    backdropFilter: "blur(4px)",
                  }}
                >
                  {formatDuration(currentTime)} / {formatDuration(analysisResult?.metadata.duration_s || 0)}
                </div>
              </div>

              {/* Analysis Loading Indicator */}
              {isAnalyzing && (
                <div
                  style={{
                    padding: "16px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--bg-panel-subtle)",
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                  }}
                >
                  <div
                    style={{
                      width: "16px",
                      height: "16px",
                      border: "2px solid var(--accent-subtle)",
                      borderTopColor: "var(--accent-primary)",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                    Analyzing video frames, scene boundaries, and visual pacing...
                  </span>
                </div>
              )}

              {/* Visual Analysis Metrics Strip */}
              {analysisResult && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    <div className="badge badge-accent" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Clock size={12} />
                      <span>Exact Duration: {analysisResult.metadata.duration_s.toFixed(2)}s</span>
                    </div>
                    <div className="badge badge-success" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Activity size={12} />
                      <span>Pacing: {analysisResult.activity.pacing.toUpperCase()}</span>
                    </div>
                    <div className="badge badge-subtle" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Sparkles size={12} />
                      <span>Mood: {analysisResult.activity.detected_mood}</span>
                    </div>
                    <div className="badge badge-subtle" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Scissors size={12} />
                      <span>{analysisResult.scene_cuts.length} Scene Cuts Detected</span>
                    </div>
                  </div>

                  {/* Keyframe Timeline Strip */}
                  {analysisResult.keyframes.length > 0 && (
                    <div style={{ marginTop: "4px" }}>
                      <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                        Sampled Video Timeline
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: `repeat(${analysisResult.keyframes.length}, 1fr)`,
                          gap: "8px",
                          overflowX: "auto",
                        }}
                      >
                        {analysisResult.keyframes.map((kf, idx) => (
                          <div
                            key={idx}
                            style={{
                              position: "relative",
                              borderRadius: "var(--radius-sm)",
                              overflow: "hidden",
                              border: "1px solid var(--border-subtle)",
                              aspectRatio: "16 / 9",
                              background: "#000000",
                            }}
                          >
                            <img
                              src={kf.data_uri}
                              alt={`Keyframe at ${kf.timestamp_s}s`}
                              style={{ width: "100%", height: "100%", objectFit: "cover" }}
                            />
                            <div
                              style={{
                                position: "absolute",
                                bottom: "2px",
                                right: "4px",
                                background: "rgba(0,0,0,0.75)",
                                padding: "1px 4px",
                                borderRadius: "3px",
                                fontSize: "0.68rem",
                                fontFamily: "var(--font-mono)",
                                color: "#ffffff",
                              }}
                            >
                              {kf.timestamp_s.toFixed(1)}s
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Musical Style Selector */}
          <div className="panel" style={{ padding: "20px 24px" }}>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
              Musical Style & Genre
            </h2>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "14px" }}>
              Select a musical aesthetic or let the engine automatically match the visual mood and motion velocity.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
              {styleOptions.map((opt) => {
                const Icon = opt.icon;
                const isSelected = selectedStyle === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleStyleChange(opt.id)}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                      padding: "12px 14px",
                      borderRadius: "var(--radius-md)",
                      border: `1px solid ${isSelected ? "var(--accent-primary)" : "var(--border-subtle)"}`,
                      background: isSelected ? "var(--accent-subtle)" : "var(--bg-panel-subtle)",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all var(--transition-fast)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", width: "100%", marginBottom: "4px" }}>
                      <Icon size={15} color={isSelected ? "var(--accent-text)" : "var(--text-secondary)"} />
                      <span style={{ fontWeight: 600, fontSize: "0.85rem", color: isSelected ? "var(--text-primary)" : "var(--text-secondary)" }}>
                        {opt.label}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", lineHeight: 1.3 }}>
                      {opt.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Arrangement Plan Preview */}
          {plan && (
            <div className="panel" style={{ padding: "20px 24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <h2 style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "2px" }}>
                    Synchronized Arrangement Plan
                  </h2>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    Tempo: <strong style={{ color: "var(--text-primary)" }}>{plan.tempo_bpm} BPM</strong> • Key: <strong style={{ color: "var(--text-primary)" }}>{plan.key}</strong> • Target Duration: <strong style={{ color: "var(--text-primary)" }}>{plan.target_duration_s.toFixed(2)}s</strong>
                  </div>
                </div>

                <div className="badge badge-subtle">
                  {plan.genre}
                </div>
              </div>

              {/* Timestamped Sections */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Arrangement Sections Aligned to Video Cuts
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {plan.sections.map((sec, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "8px 12px",
                        background: "var(--bg-panel-subtle)",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "0.8rem",
                      }}
                    >
                      <span
                        className="font-mono"
                        style={{
                          background: "var(--accent-subtle)",
                          color: "var(--accent-text)",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontWeight: 600,
                          fontSize: "0.75rem",
                        }}
                      >
                        {sec.start_s.toFixed(1)}s
                      </span>
                      <span style={{ color: "var(--text-secondary)", flex: 1 }}>
                        {sec.mood}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Accents / Drops */}
              {plan.accents.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "16px" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Planned Musical Accents & Drops
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {plan.accents.map((acc, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "4px 8px",
                          background: "rgba(249, 115, 22, 0.12)",
                          border: "1px solid rgba(249, 115, 22, 0.25)",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "0.75rem",
                          color: "var(--stem-drums)",
                        }}
                      >
                        <span className="font-mono" style={{ fontWeight: 600 }}>{acc.timestamp_s.toFixed(1)}s:</span>
                        <span>{acc.musical_action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Editable Prompt */}
              <div>
                <label
                  htmlFor="video-prompt-input"
                  style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}
                >
                  Generation Prompt (Auto-Composed)
                </label>
                <textarea
                  id="video-prompt-input"
                  rows={2}
                  value={editablePrompt}
                  onChange={(e) => setEditablePrompt(e.target.value)}
                  style={{
                    width: "100%",
                    background: "var(--bg-input)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-md)",
                    padding: "10px 12px",
                    color: "var(--text-primary)",
                    fontSize: "0.85rem",
                    resize: "vertical",
                    outline: "none",
                  }}
                />
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "12px 16px",
                background: "var(--danger-subtle)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "var(--radius-md)",
                color: "var(--danger)",
                fontSize: "0.85rem",
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Action Button */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={handleGenerate}
              disabled={!selectedFile || isAnalyzing || isGenerating}
              className="btn btn-primary"
              style={{ padding: "12px 24px", fontSize: "0.95rem" }}
            >
              {isGenerating ? (
                <>
                  <div
                    style={{
                      width: "14px",
                      height: "14px",
                      border: "2px solid #ffffff",
                      borderTopColor: "transparent",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span>Generating Soundtrack...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Generate Video Soundtrack</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Upload Size / Format Error Banner */}
      {error && !selectedFile && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "12px 16px",
            background: "var(--danger-subtle)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-md)",
            color: "var(--danger)",
            fontSize: "0.85rem",
          }}
        >
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
