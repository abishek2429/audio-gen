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
  color = "#8b5cf6",
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

  // Synchronize mute prop
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
      audioRef.current.play().then(() => setIsPlaying(true)).catch((err) => {
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

  // Render static mock waveform canvas for rich aesthetic
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const bars = 48;
    const barWidth = width / bars - 2;
    const progress = duration > 0 ? currentTime / duration : 0;

    for (let i = 0; i < bars; i++) {
      // Deterministic synthetic height based on title hash + bar index
      const seed = (title.charCodeAt(0) + i * 7) % 100;
      const barHeight = Math.max(4, (Math.sin(i * 0.3) * 0.4 + 0.5) * (seed / 100) * height * 0.85);
      const x = i * (barWidth + 2);
      const y = (height - barHeight) / 2;

      const isPlayed = i / bars <= progress;
      ctx.fillStyle = isPlayed ? color : "rgba(255, 255, 255, 0.15)";
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, 2);
      ctx.fill();
    }
  }, [currentTime, duration, color, title]);

  return (
    <div
      style={{
        background: "rgba(10, 15, 26, 0.6)",
        border: `1px solid ${isSolo ? color : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-md)",
        padding: "14px 18px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        boxShadow: isSolo ? `0 0 15px ${color}40` : "none",
        transition: "all 0.2s ease",
      }}
    >
      <audio ref={audioRef} src={resolvedUrl || undefined} preload="metadata" />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              backgroundColor: color,
              boxShadow: isPlaying ? `0 0 10px ${color}` : "none",
            }}
          />
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--text-main)" }}>{title}</div>
            {subtitle && <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>{subtitle}</div>}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {badge && (
            <span
              className="badge"
              style={{
                backgroundColor: `${badgeColor || color}20`,
                color: badgeColor || color,
                borderColor: `${badgeColor || color}40`,
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
                backgroundColor: isSolo ? color : "rgba(255, 255, 255, 0.05)",
                color: isSolo ? "#fff" : "var(--text-muted)",
                padding: "4px 8px",
              }}
              title="Solo stem"
            >
              S
            </button>
          )}

          {onMute && (
            <button
              onClick={onMute}
              className="btn btn-sm"
              style={{
                backgroundColor: isMuted ? "var(--danger)" : "rgba(255, 255, 255, 0.05)",
                color: isMuted ? "#fff" : "var(--text-muted)",
                padding: "4px 8px",
              }}
              title="Mute stem"
            >
              M
            </button>
          )}

          {resolvedUrl && (
            <a
              href={resolvedUrl}
              download={downloadFilename || `${title.toLowerCase().replace(/\s+/g, "_")}.wav`}
              className="btn btn-secondary btn-sm"
              title="Download uncompressed WAV"
              target="_blank"
              rel="noreferrer"
            >
              <Download size={14} />
            </a>
          )}
        </div>
      </div>

      {/* Waveform Canvas Visualizer */}
      <div style={{ position: "relative", width: "100%", height: "40px" }}>
        <canvas
          ref={canvasRef}
          width={400}
          height={40}
          style={{ width: "100%", height: "100%", display: "block" }}
        />
      </div>

      {/* Playback Controls & Scrubber */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button
          onClick={togglePlay}
          disabled={!resolvedUrl}
          className="btn btn-primary"
          style={{
            width: "36px",
            height: "36px",
            padding: 0,
            borderRadius: "50%",
            flexShrink: 0,
          }}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} style={{ marginLeft: "2px" }} />}
        </button>

        <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-dim)", minWidth: "35px" }}>
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

        <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-dim)", minWidth: "35px" }}>
          {formatTime(duration)}
        </span>

        <div style={{ display: "flex", alignItems: "center", gap: "4px", minWidth: "90px" }}>
          <button
            onClick={toggleMute}
            style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", display: "flex" }}
            aria-label="Toggle mute"
          >
            {isAudioMuted || isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
          </button>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={isAudioMuted || isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            style={{ width: "60px" }}
            aria-label="Volume"
          />
        </div>
      </div>
    </div>
  );
};
