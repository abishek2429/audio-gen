import React, { useEffect, useState } from "react";
import { PlusCircle, Music, Sparkles } from "lucide-react";
import { apiClient } from "../services/apiClient";
import type { JobStatusResponse } from "../types/api";

interface DashboardViewProps {
  onNavigate: (tab: string, jobId?: string) => void;
  onSelectPreset?: (preset: { prompt: string; duration_s: number; tempo?: number; key?: string }) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate, onSelectPreset }) => {
  const [jobs, setJobs] = useState<JobStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    apiClient
      .listJobs(10)
      .then((data) => {
        if (mounted) setJobs(data);
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const totalJobs = jobs.length;

  const presets = [
    {
      title: "Cinematic Trailer",
      prompt: "dramatic cinematic orchestral, soaring strings, epic drums, builds to climax",
      duration_s: 45,
      tempo: 96,
      key: "D minor",
      tag: "Cinematic",
    },
    {
      title: "Tech Corporate",
      prompt: "uplifting tech corporate acoustic folk, bright acoustic guitars, light percussion",
      duration_s: 30,
      tempo: 110,
      key: "C major",
      tag: "Corporate",
    },
    {
      title: "Chill Lo-Fi",
      prompt: "relaxing lo-fi chillhop with vintage vinyl crackle, gentle electric piano",
      duration_s: 20,
      tempo: 84,
      key: "A minor",
      tag: "Lo-Fi",
    },
  ];

  const handleApplyPreset = (preset: (typeof presets)[0]) => {
    if (onSelectPreset) {
      onSelectPreset({
        prompt: preset.prompt,
        duration_s: preset.duration_s,
        tempo: preset.tempo,
        key: preset.key,
      });
    }
    onNavigate("studio");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header Banner */}
      <div className="panel" style={{ padding: "28px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <span className="badge badge-success" style={{ marginBottom: "8px" }}>
              AI Music Studio
            </span>
            <h1 style={{ fontSize: "1.6rem", fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
              Background Music for Video Production
            </h1>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", marginTop: "4px", maxWidth: "560px" }}>
              Original instrumental music timed to your video edit points, with 48 kHz uncompressed WAV and separate instrument stems.
            </p>
          </div>

          <button onClick={() => onNavigate("studio")} className="btn btn-primary">
            <PlusCircle size={15} />
            <span>Open Studio</span>
          </button>
        </div>

        {/* Minimal metrics row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "24px",
            marginTop: "20px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border-subtle)",
            fontSize: "0.82rem",
          }}
        >
          <div>
            <span style={{ color: "var(--text-muted)" }}>Total Jobs: </span>
            <span className="font-mono" style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {totalJobs}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Audio Standards: </span>
            <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
              48 kHz · -16 LUFS · ≤ -1 dBTP
            </span>
          </div>
        </div>
      </div>

      {/* Quick Presets */}
      <div>
        <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
          <Sparkles size={15} color="var(--accent-primary)" />
          <span>Quick Inspiration Presets</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
          {presets.map((p) => (
            <div
              key={p.title}
              className="panel"
              style={{
                padding: "16px 18px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "12px",
                cursor: "pointer",
              }}
              onClick={() => handleApplyPreset(p)}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>{p.title}</span>
                  <span className="badge badge-neutral">{p.duration_s}s</span>
                </div>
                <p style={{ color: "var(--text-muted)", fontSize: "0.78rem", lineHeight: 1.4 }}>
                  "{p.prompt}"
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--accent-text)" }}>
                <span>{p.tempo} BPM · {p.key}</span>
                <span style={{ fontWeight: 600 }}>Use Preset →</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Jobs */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Recent Tracks
          </span>
          <button onClick={() => onNavigate("history")} className="btn btn-ghost btn-sm" style={{ padding: "2px 8px", fontSize: "0.78rem" }}>
            View All ({totalJobs})
          </button>
        </div>

        {loading ? (
          <div className="panel" style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Loading...
          </div>
        ) : jobs.length === 0 ? (
          <div className="panel" style={{ padding: "28px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            No tracks generated yet. Click "Open Studio" to start.
          </div>
        ) : (
          <div className="panel" style={{ overflow: "hidden" }}>
            {jobs.slice(0, 5).map((j, idx) => (
              <div
                key={j.job_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 18px",
                  borderBottom: idx < Math.min(jobs.length, 5) - 1 ? "1px solid var(--border-subtle)" : "none",
                  gap: "12px",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                    <span
                      className={`badge ${
                        j.status === "succeeded"
                          ? "badge-success"
                          : j.status === "failed"
                          ? "badge-danger"
                          : "badge-neutral"
                      }`}
                    >
                      {j.status}
                    </span>
                    <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {j.job_id}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.86rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {j.manifest?.prompt || "Instrumental Cue"}
                  </div>
                </div>

                {j.status === "succeeded" && (
                  <button onClick={() => onNavigate("studio", j.job_id)} className="btn btn-secondary btn-sm" style={{ padding: "4px 10px", fontSize: "0.78rem" }}>
                    <Music size={13} />
                    <span>Open</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
