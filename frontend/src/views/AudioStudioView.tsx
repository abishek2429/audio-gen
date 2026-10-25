import React, { useState } from "react";
import { Layers, Download, Music, ChevronDown, ChevronUp, Plus, Code, CheckCircle } from "lucide-react";
import { AudioWaveform } from "../components/AudioWaveform";
import type { JobStatusResponse } from "../types/api";

interface AudioStudioViewProps {
  job: JobStatusResponse | null;
  onNavigate: (tab: string, jobId?: string) => void;
  onNewGeneration?: () => void;
}

export const AudioStudioView: React.FC<AudioStudioViewProps> = ({
  job,
  onNavigate,
  onNewGeneration,
}) => {
  const [soloStem, setSoloStem] = useState<string | null>(null);
  const [mutedStems, setMutedStems] = useState<Record<string, boolean>>({});
  const [stemsExpanded, setStemsExpanded] = useState(true);
  const [manifestExpanded, setManifestExpanded] = useState(false);

  if (!job) {
    return (
      <div className="panel" style={{ padding: "48px 24px", textAlign: "center", maxWidth: "600px", margin: "0 auto" }}>
        <Music size={36} color="var(--text-muted)" style={{ marginBottom: "12px" }} />
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "6px" }}>No Audio Track Loaded</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", maxWidth: "400px", margin: "0 auto 20px" }}>
          Describe your video cue in the studio prompt to generate an instrumental track with separate stems.
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
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
            </div>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.01em", color: "var(--text-primary)", marginBottom: "4px" }}>
              {manifest.prompt ? `"${manifest.prompt}"` : "Instrumental Background Cue"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {onNewGeneration && (
              <button onClick={onNewGeneration} className="btn btn-secondary btn-sm">
                <Plus size={14} />
                <span>New Track</span>
              </button>
            )}
            {result?.mix_wav && (
              <a
                href={result.mix_wav}
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

        {/* Compact Metadata Row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "18px",
            flexWrap: "wrap",
            paddingTop: "14px",
            marginTop: "14px",
            borderTop: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
          }}
        >
          <div>
            <span style={{ color: "var(--text-muted)" }}>Duration: </span>
            <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {manifest.actual_duration_s ?? manifest.duration_s ?? "--"}s
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Format: </span>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
              48 kHz · 24-bit WAV
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
              href={result.mix_ducked_wav}
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
