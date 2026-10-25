import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, Volume2, VolumeX, Download } from "lucide-react";
import { resolveAudioUrl } from "../services/apiClient";

interface AudioWaveformProps {
  title: string;
  audioUrl?: string | null;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  color?: string;
  downloadFilename?: string;
  onSolo?: () => void;
  onMute?: () => void;
  isMuted?: boolean;
  isSolo?: boolean;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({
  title,
  audioUrl,
  subtitle,
  badge,
  badgeColor,
  color = "var(--accent-primary)",
  downloadFilename,
  onSolo,
  onMute,
  isMuted = false,
  isSolo = false,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isAudioMuted, setIsAudioMuted] = useState(false);

  const resolvedUrl = resolveAudioUrl(audioUrl);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration || 0);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", updateTime);
    audio.addEventListener("loadedmetadata", updateDuration);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", updateTime);
      audio.removeEventListener("loadedmetadata", updateDuration);
      audio.removeEventListener("ended", handleEnded);
    };
  }, [resolvedUrl]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.muted = isMuted || isAudioMuted;
    }
  }, [isMuted, isAudioMuted]);

  const togglePlay = () => {
    if (!audioRef.current || !resolvedUrl) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => {
          console.warn("Audio playback failed:", err);
        });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    setVolume(vol);
    if (audioRef.current) {
      audioRef.current.volume = vol;
      setIsAudioMuted(vol === 0);
    }
  };

  const toggleMute = () => {
    if (onMute) {
      onMute();
    } else {
      setIsAudioMuted(!isAudioMuted);
    }
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Render clean audio bar canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const bars = 44;
    const barWidth = width / bars - 2;
    const progress = duration > 0 ? currentTime / duration : 0;

    for (let i = 0; i < bars; i++) {
      const seed = (title.charCodeAt(0) + i * 7) % 100;
      const barHeight = Math.max(3, (Math.sin(i * 0.28) * 0.35 + 0.55) * (seed / 100) * height * 0.82);
      const x = i * (barWidth + 2);
      const y = (height - barHeight) / 2;

      const isPlayed = i / bars <= progress;
      ctx.fillStyle = isPlayed ? (color.startsWith("var") ? "#6366f1" : color) : "#232734";
      ctx.beginPath();
      if (typeof ctx.roundRect === "function") {
        ctx.roundRect(x, y, barWidth, barHeight, 1.5);
      } else {
        ctx.rect(x, y, barWidth, barHeight);
      }
      ctx.fill();
    }
  }, [currentTime, duration, color, title]);


  return (
    <div
      style={{
        background: "var(--bg-panel-subtle)",
        border: `1px solid ${isSolo ? "var(--accent-primary)" : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-md)",
        padding: "12px 16px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        transition: "border-color var(--transition-fast)",
      }}
    >
      <audio ref={audioRef} src={resolvedUrl || undefined} preload="metadata" />

      {/* Track Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: color.startsWith("var") ? "var(--accent-primary)" : color,
            }}
          />
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "var(--text-primary)" }}>{title}</div>
            {subtitle && <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{subtitle}</div>}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {badge && (
            <span
              className="badge"
              style={{
                backgroundColor: "var(--bg-canvas)",
                color: badgeColor || "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {badge}
            </span>
          )}

          {onSolo && (
            <button
              onClick={onSolo}
              className="btn btn-sm"
              style={{
                padding: "3px 8px",
                fontSize: "0.72rem",
                fontWeight: 600,
                background: isSolo ? "var(--accent-primary)" : "var(--bg-canvas)",
                color: isSolo ? "#fff" : "var(--text-muted)",
                borderColor: isSolo ? "var(--accent-primary)" : "var(--border-subtle)",
              }}
              title="Solo stem"
            >
              SOLO
            </button>
          )}

          {onMute && (
            <button
              onClick={onMute}
              className="btn btn-sm"
              style={{
                padding: "3px 8px",
                fontSize: "0.72rem",
                fontWeight: 600,
                background: isMuted ? "var(--danger)" : "var(--bg-canvas)",
                color: isMuted ? "#fff" : "var(--text-muted)",
                borderColor: isMuted ? "var(--danger)" : "var(--border-subtle)",
              }}
              title="Mute stem"
            >
              MUTE
            </button>
          )}

          {resolvedUrl && (
            <a
              href={resolvedUrl}
              download={downloadFilename || `${title.toLowerCase().replace(/\s+/g, "_")}.wav`}
              className="btn btn-secondary btn-sm"
              style={{ padding: "4px 8px" }}
              title="Download uncompressed WAV"
              target="_blank"
              rel="noreferrer"
            >
              <Download size={13} />
            </a>
          )}
        </div>
      </div>

      {/* Visualizer Canvas */}
      <div style={{ position: "relative", width: "100%", height: "26px" }}>
        <canvas
          ref={canvasRef}
          width={360}
          height={26}
          style={{ width: "100%", height: "100%", display: "block" }}
        />
      </div>

      {/* Controls Bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <button
          onClick={togglePlay}
          disabled={!resolvedUrl}
          className="btn btn-primary"
          style={{
            width: "30px",
            height: "30px",
            padding: 0,
            borderRadius: "50%",
            flexShrink: 0,
          }}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause size={13} /> : <Play size={13} style={{ marginLeft: "1.5px" }} />}
        </button>

        <span className="font-mono" style={{ fontSize: "0.74rem", color: "var(--text-muted)", minWidth: "32px" }}>
          {formatTime(currentTime)}
        </span>

        <input
          type="range"
          min={0}
          max={duration || 100}
          step={0.05}
          value={currentTime}
          onChange={handleSeek}
          disabled={!resolvedUrl}
          style={{ flex: 1 }}
          aria-label="Seek track position"
        />

        <span className="font-mono" style={{ fontSize: "0.74rem", color: "var(--text-muted)", minWidth: "32px" }}>
          {formatTime(duration)}
        </span>

        <div style={{ display: "flex", alignItems: "center", gap: "4px", minWidth: "80px" }}>
          <button
            onClick={toggleMute}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", padding: "2px" }}
            aria-label="Toggle mute"
          >
            {isAudioMuted || isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={isAudioMuted || isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            style={{ width: "50px" }}
            aria-label="Volume"
          />
        </div>
      </div>
    </div>
  );
};
