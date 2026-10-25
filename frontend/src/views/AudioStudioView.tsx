import React, { useState, useRef, useEffect } from "react";
import {
  Layers,
  Download,
  Music,
  ChevronDown,
  ChevronUp,
  Plus,
  Code,
  CheckCircle,
  Film,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Upload,
} from "lucide-react";
import { AudioWaveform } from "../components/AudioWaveform";
import { resolveAudioUrl } from "../services/apiClient";
import type { JobStatusResponse } from "../types/api";

interface AudioStudioViewProps {
  job: JobStatusResponse | null;
  videoUrl?: string | null;
  videoFile?: File | null;
  onNavigate: (tab: string, jobId?: string) => void;
  onNewGeneration?: () => void;
}

export const AudioStudioView: React.FC<AudioStudioViewProps> = ({
  job,
  videoUrl: initialVideoUrl,
  videoFile: initialVideoFile,
  onNavigate,
  onNewGeneration,
}) => {
  const [soloStem, setSoloStem] = useState<string | null>(null);
  const [mutedStems, setMutedStems] = useState<Record<string, boolean>>({});
  const [stemsExpanded, setStemsExpanded] = useState(true);
  const [manifestExpanded, setManifestExpanded] = useState(false);

  // Video Audition state
  const [overrideVideoUrl, setOverrideVideoUrl] = useState<string | null>(null);
  const [overrideVideoFile, setOverrideVideoFile] = useState<File | null>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);

  const activeVideoUrl = overrideVideoUrl ?? initialVideoUrl ?? null;
  const activeVideoFile = overrideVideoFile ?? initialVideoFile ?? null;

  // Synchronized Video + Soundtrack playback state
  const videoRef = useRef<HTMLVideoElement>(null);
  const soundtrackAudioRef = useRef<HTMLAudioElement>(null);
  const [isSyncPlaying, setIsSyncPlaying] = useState(false);
  const [syncTime, setSyncTime] = useState(0);
  const [syncDuration, setSyncDuration] = useState(0);
  const [soundtrackVolume, setSoundtrackVolume] = useState(1.0);
  const [videoAudioMuted, setVideoAudioMuted] = useState(true);

  // Sync Audio Volume
  useEffect(() => {
    if (soundtrackAudioRef.current) {
      soundtrackAudioRef.current.volume = soundtrackVolume;
    }
  }, [soundtrackVolume]);

  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (overrideVideoUrl && overrideVideoUrl.startsWith("blob:")) {
        URL.revokeObjectURL(overrideVideoUrl);
      }
      const url = URL.createObjectURL(file);
      setOverrideVideoFile(file);
      setOverrideVideoUrl(url);
      setIsSyncPlaying(false);
      setSyncTime(0);
    }
  };

  const toggleSyncPlay = () => {
    const video = videoRef.current;
    const audio = soundtrackAudioRef.current;

    if (!video || !audio) return;

    if (isSyncPlaying) {
      video.pause();
      audio.pause();
      setIsSyncPlaying(false);
    } else {
      // Sync positions exactly before playing
      audio.currentTime = video.currentTime;
      video.play().catch(console.warn);
      audio.play().catch(console.warn);
      setIsSyncPlaying(true);
    }
  };

  const handleSyncSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetTime = parseFloat(e.target.value);
    setSyncTime(targetTime);

    if (videoRef.current) {
      videoRef.current.currentTime = targetTime;
    }
    if (soundtrackAudioRef.current) {
      soundtrackAudioRef.current.currentTime = targetTime;
    }
  };

  const handleReplay = () => {
    const video = videoRef.current;
    const audio = soundtrackAudioRef.current;
    if (!video || !audio) return;

    video.currentTime = 0;
    audio.currentTime = 0;
    setSyncTime(0);
    video.play().catch(console.warn);
    audio.play().catch(console.warn);
    setIsSyncPlaying(true);
  };

  if (!job) {
    return (
      <div className="panel" style={{ padding: "48px 24px", textAlign: "center", maxWidth: "600px", margin: "0 auto" }}>
        <Music size={36} color="var(--text-muted)" style={{ marginBottom: "12px" }} />
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "6px" }}>No Audio Track Loaded</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", maxWidth: "400px", margin: "0 auto 20px" }}>
          Describe your video cue or upload a video to generate an instrumental track with separate stems.
        </p>
        <button
          onClick={() => {
            if (onNewGeneration) onNewGeneration();
            else onNavigate("studio");
          }}
          className="btn btn-primary"
        >
          <Plus size={15} />
          <span>Create New Track</span>
        </button>
      </div>
    );
  }

  const manifest = job.manifest || {};
  const result = job.result;
  const stems: Record<string, string> = result?.stems || {};
  const audioMetrics = manifest.audio_metrics || {};
  const resolvedMixUrl = resolveAudioUrl(result?.mix_wav);

  const handleToggleSolo = (name: string) => {
    setSoloStem(soloStem === name ? null : name);
  };

  const handleToggleMute = (name: string) => {
    setMutedStems((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const stemColors: Record<string, string> = {
    drums: "var(--stem-drums)",
    bass: "var(--stem-bass)",
    harmony: "var(--stem-harmony)",
    melody: "var(--stem-melody)",
    vocals: "var(--stem-vocals)",
  };

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Hidden Synchronized Audio Element for Mix Playback with Video */}
      {resolvedMixUrl && (
        <audio
          ref={soundtrackAudioRef}
          src={resolvedMixUrl}
          preload="auto"
          onEnded={() => {
            setIsSyncPlaying(false);
            if (videoRef.current) videoRef.current.pause();
          }}
        />
      )}

      {/* Track Header Card */}
      <div className="panel" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "14px" }}>
          <div style={{ flex: 1, minWidth: "260px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span className="badge badge-success">
                <CheckCircle size={11} /> Ready
              </span>
              <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {job.job_id}
              </span>
              {activeVideoFile && (
                <span className="badge badge-accent" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Film size={11} /> {activeVideoFile.name}
                </span>
              )}
            </div>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.01em", color: "var(--text-primary)", marginBottom: "4px" }}>
              {manifest.prompt ? `"${manifest.prompt}"` : "Synchronized Instrumental Soundtrack"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {onNewGeneration && (
              <button onClick={onNewGeneration} className="btn btn-secondary btn-sm">
                <Plus size={14} />
                <span>New Generation</span>
              </button>
            )}
            {result?.mix_wav && (
              <a
                href={resolveAudioUrl(result.mix_wav)}
                download="mix.wav"
                className="btn btn-primary btn-sm"
                target="_blank"
                rel="noreferrer"
              >
                <Download size={14} />
                <span>Download Mix</span>
              </a>
            )}
          </div>
        </div>

        {/* Audio Engine Quality Chips */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "18px",
            marginTop: "16px",
            paddingTop: "14px",
            borderTop: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}
        >
          <div>
            <span style={{ color: "var(--text-muted)" }}>Duration: </span>
            <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {manifest.actual_duration_s ? `${manifest.actual_duration_s.toFixed(2)}s` : `${job.manifest?.requested_duration_s || 30.0}s`}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Sample Rate: </span>
            <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {manifest.sample_rate ? `${manifest.sample_rate / 1000} kHz 24-bit` : "48 kHz 24-bit"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Loudness: </span>
            <span className="font-mono" style={{ color: "var(--accent-text)", fontWeight: 600 }}>
              {audioMetrics.integrated_lufs ? `${audioMetrics.integrated_lufs} LUFS` : "-16.0 LUFS"}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>True Peak: </span>
            <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {audioMetrics.true_peak_dbtp ? `${audioMetrics.true_peak_dbtp} dBTP` : "≤ -1.0 dBTP"}
            </span>
          </div>
          {manifest.tempo_bpm && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Tempo: </span>
              <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                {manifest.tempo_bpm} BPM {manifest.key ? `· ${manifest.key}` : ""}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Synchronized Video + Soundtrack Audition Card */}
      {activeVideoUrl ? (
        <div className="panel" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Film size={18} color="var(--accent-primary)" />
              <div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  Synchronized Video & Soundtrack Audition
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                  Video visual cuts aligned in lockstep with the generated 48 kHz soundtrack.
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                ref={videoInputRef}
                type="file"
                accept="video/mp4,video/quicktime,video/webm"
                style={{ display: "none" }}
                onChange={handleVideoUpload}
              />
              <button
                type="button"
                onClick={() => videoInputRef.current?.click()}
                className="btn btn-secondary btn-sm"
              >
                <Upload size={13} />
                <span>Replace Video</span>
              </button>
            </div>
          </div>

          {/* Synchronized Player Canvas */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "14px",
              background: "#000000",
              borderRadius: "var(--radius-md)",
              padding: "12px",
              border: "1px solid var(--border-default)",
            }}
          >
            <div
              style={{
                position: "relative",
                width: "100%",
                maxHeight: "380px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <video
                ref={videoRef}
                src={activeVideoUrl}
                style={{ width: "100%", maxHeight: "380px", objectFit: "contain" }}
                playsInline
                muted={videoAudioMuted}
                onLoadedMetadata={() => {
                  if (videoRef.current) setSyncDuration(videoRef.current.duration);
                }}
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setSyncTime(videoRef.current.currentTime);
                    // Drift correction if needed
                    if (soundtrackAudioRef.current && Math.abs(soundtrackAudioRef.current.currentTime - videoRef.current.currentTime) > 0.15) {
                      soundtrackAudioRef.current.currentTime = videoRef.current.currentTime;
                    }
                  }
                }}
                onEnded={() => {
                  setIsSyncPlaying(false);
                  if (soundtrackAudioRef.current) soundtrackAudioRef.current.pause();
                }}
              />
            </div>

            {/* Transport & Control Bar */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                background: "var(--bg-panel-subtle)",
                padding: "12px 16px",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {/* Scrub Bar */}
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-secondary)", minWidth: "40px" }}>
                  {formatTime(syncTime)}
                </span>
                <input
                  type="range"
                  min={0}
                  max={syncDuration || manifest.actual_duration_s || 30.0}
                  step={0.05}
                  value={syncTime}
                  onChange={handleSyncSeek}
                  style={{
                    flex: 1,
                    accentColor: "var(--accent-primary)",
                    cursor: "pointer",
                    height: "5px",
                  }}
                />
                <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", minWidth: "40px" }}>
                  {formatTime(syncDuration || manifest.actual_duration_s || 30.0)}
                </span>
              </div>

              {/* Action Buttons Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <button
                    onClick={toggleSyncPlay}
                    className="btn btn-primary btn-sm"
                    style={{ padding: "6px 14px" }}
                  >
                    {isSyncPlaying ? <Pause size={14} /> : <Play size={14} />}
                    <span>{isSyncPlaying ? "Pause Both" : "Play Synced"}</span>
                  </button>

                  <button
                    onClick={handleReplay}
                    className="btn btn-secondary btn-sm"
                    title="Replay from beginning"
                  >
                    <RotateCcw size={14} />
                    <span>Replay</span>
                  </button>

                  {/* Video Original Audio Mute Toggle */}
                  <button
                    onClick={() => setVideoAudioMuted(!videoAudioMuted)}
                    className="btn btn-secondary btn-sm"
                    style={{
                      color: videoAudioMuted ? "var(--text-muted)" : "var(--warning)",
                    }}
                    title={videoAudioMuted ? "Video original audio is muted (soundtrack only)" : "Video original audio is enabled"}
                  >
                    {videoAudioMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                    <span>{videoAudioMuted ? "Video Audio Muted" : "Video Audio On"}</span>
                  </button>
                </div>

                {/* Soundtrack Volume Slider */}
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Volume2 size={14} color="var(--text-muted)" />
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Soundtrack Vol:</span>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={soundtrackVolume}
                    onChange={(e) => setSoundtrackVolume(parseFloat(e.target.value))}
                    style={{ width: "80px", accentColor: "var(--accent-primary)" }}
                  />
                  <span className="font-mono" style={{ fontSize: "0.72rem", color: "var(--text-muted)", minWidth: "30px" }}>
                    {Math.round(soundtrackVolume * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Prompt user to attach video if not already present */
        <div
          className="panel"
          style={{
            padding: "16px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
            background: "var(--bg-panel-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Film size={18} color="var(--accent-primary)" />
            <div>
              <div style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Audition Against Video
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Attach a video clip to play synchronously alongside this soundtrack cue.
              </div>
            </div>
          </div>

          <div>
            <input
              ref={videoInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm"
              style={{ display: "none" }}
              onChange={handleVideoUpload}
            />
            <button
              onClick={() => videoInputRef.current?.click()}
              className="btn btn-secondary btn-sm"
            >
              <Upload size={13} />
              <span>Attach Video</span>
            </button>
          </div>
        </div>
      )}

      {/* Master Mix Player */}
      <div className="panel" style={{ padding: "18px 22px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div>
            <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Final Instrumental Mix</div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              Full stereo master, loudness-normalized with smooth cosine ending.
            </div>
          </div>
        </div>

        <AudioWaveform
          title="Master Mix"
          subtitle="48 kHz 24-bit PCM WAV (-16 LUFS)"
          audioUrl={result?.mix_wav}
          badge="Full Mix"
          badgeColor="var(--accent-primary)"
          color="var(--accent-primary)"
          downloadFilename="mix.wav"
        />
      </div>

      {/* Ducked Mix (rendered only if voiceover was provided) */}
      {result?.mix_ducked_wav && (
        <div className="panel" style={{ padding: "18px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Voiceover Ducked Mix</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                Attenuated by 10 dB under voiceover narration with smooth attack/release.
              </div>
            </div>
            <a
              href={resolveAudioUrl(result.mix_ducked_wav)}
              download="mix_ducked.wav"
              className="btn btn-secondary btn-sm"
              target="_blank"
              rel="noreferrer"
            >
              <Download size={13} />
              <span>Download Ducked</span>
            </a>
          </div>

          <AudioWaveform
            title="Ducked Music Bed"
            subtitle="Music sidechained under speech"
            audioUrl={result.mix_ducked_wav}
            badge="Ducked"
            badgeColor="var(--stem-harmony)"
            color="var(--stem-harmony)"
            downloadFilename="mix_ducked.wav"
          />
        </div>
      )}

      {/* Multitrack Stems Section (Collapsible) */}
      {Object.keys(stems).length > 0 && (
        <div className="panel" style={{ padding: "18px 22px" }}>
          <div
            onClick={() => setStemsExpanded(!stemsExpanded)}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="var(--accent-primary)" />
              <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Instrument Stems ({Object.keys(stems).length} Tracks)
              </span>
              <span style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                (Separated acoustic parts; sum reconstructs master mix)
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {soloStem && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSoloStem(null);
                  }}
                  className="btn btn-secondary btn-sm"
                  style={{ padding: "2px 8px", fontSize: "0.72rem" }}
                >
                  Clear Solo ({soloStem})
                </button>
              )}
              {stemsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </div>

          {stemsExpanded && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "14px" }}>
              {Object.entries(stems).map(([stemName, stemUrl]) => {
                const color = stemColors[stemName.toLowerCase()] || "var(--accent-primary)";
                const isStemMuted = !!mutedStems[stemName] || (soloStem !== null && soloStem !== stemName);
                const isStemSolo = soloStem === stemName;

                return (
                  <AudioWaveform
                    key={stemName}
                    title={`${stemName.charAt(0).toUpperCase() + stemName.slice(1)}`}
                    subtitle="48 kHz uncompressed WAV stem"
                    audioUrl={stemUrl as string}
                    badge="Stem"
                    badgeColor={color}
                    color={color}
                    downloadFilename={`${stemName}.wav`}
                    onSolo={() => handleToggleSolo(stemName)}
                    onMute={() => handleToggleMute(stemName)}
                    isMuted={isStemMuted}
                    isSolo={isStemSolo}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Technical Details & Manifest (Collapsible) */}
      <div className="panel" style={{ padding: "14px 20px" }}>
        <div
          onClick={() => setManifestExpanded(!manifestExpanded)}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <Code size={14} />
            <span>Technical Verification & Manifest</span>
          </div>
          {manifestExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>

        {manifestExpanded && (
          <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)" }}>
            <pre
              className="font-mono"
              style={{
                fontSize: "0.75rem",
                background: "var(--bg-canvas)",
                padding: "14px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-subtle)",
                overflowX: "auto",
                maxHeight: "280px",
                color: "var(--text-secondary)",
              }}
            >
              {JSON.stringify(manifest, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
