import React, { useEffect, useState } from "react";
import { PlusCircle, Music, CheckCircle2, XCircle, Clock, ArrowRight, ShieldCheck, Waves } from "lucide-react";
import { apiClient } from "../services/apiClient";
import type { JobStatusResponse } from "../types/api";

interface DashboardViewProps {
  onNavigate: (tab: string, jobId?: string) => void;
  onSelectPreset?: (preset: { prompt: string; duration_s: number; tempo?: number; key?: string }) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate, onSelectPreset }) => {
  const [jobs, setJobs] = useState<JobStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.listJobs(10);
      setJobs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load recent jobs");
    } finally {
      setLoading(false);
    }
  };

  const totalJobs = jobs.length;
  const successfulJobs = jobs.filter((j) => j.status === "succeeded").length;
  const failedJobs = jobs.filter((j) => j.status === "failed").length;
  const activeJobs = jobs.filter((j) => j.status === "queued" || j.status === "running").length;

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
    onNavigate("generate");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* Hero Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "36px",
          background: "linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(6, 182, 212, 0.08) 100%), var(--bg-card)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "24px",
          border: "1px solid rgba(139, 92, 246, 0.25)",
        }}
      >
        <div style={{ maxWidth: "640px" }}>
          <div className="badge badge-info" style={{ marginBottom: "12px" }}>
            Production-Ready AI Audio Engine
          </div>
          <h1 style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "10px", lineHeight: 1.2 }}>
            Original Background Music Timed to Your Video Edit
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.95rem", lineHeight: 1.6 }}>
            Generate commercially cleared original music cues matching your video duration within 0.05 seconds, delivered with uncompressed 48 kHz WAV audio and genuine 5-way instrument stems.
          </p>
        </div>

        <button
          onClick={() => onNavigate("generate")}
          className="btn btn-primary"
          style={{ padding: "14px 26px", fontSize: "1rem" }}
        >
          <PlusCircle size={20} />
          <span>Create Music Track</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-dim)", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Total Jobs</span>
            <Music size={18} color="var(--accent-primary)" />
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "#fff" }}>{totalJobs}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>Across all providers</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-dim)", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Successful</span>
            <CheckCircle2 size={18} color="var(--success)" />
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--success)" }}>{successfulJobs}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>100% verified compliance</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-dim)", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Failed Jobs</span>
            <XCircle size={18} color="var(--danger)" />
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--danger)" }}>{failedJobs}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>Handled errors & retries</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-dim)", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Active / Queued</span>
            <Clock size={18} color="var(--warning)" />
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 800, color: "var(--warning)" }}>{activeJobs}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>Processing in background</div>
        </div>

        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--text-dim)", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Audio Standards</span>
            <ShieldCheck size={18} color="var(--accent-secondary)" />
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--accent-secondary)", marginTop: "6px" }}>-16 LUFS · 48 kHz</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>True Peak ≤ -1.0 dBTP</div>
        </div>
      </div>

      {/* Preset Inspiration Row */}
      <div>
        <div style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Waves size={18} color="var(--accent-secondary)" />
          <span>Quick Production Presets</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
          {presets.map((p, idx) => (
            <div
              key={idx}
              className="glass-panel"
              style={{
                padding: "20px",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "14px",
              }}
              onClick={() => handleApplyPreset(p)}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 700, fontSize: "1rem", color: "#fff" }}>{p.title}</span>
                  <span className="badge badge-info">{p.tag}</span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.5 }}>"{p.prompt}"</p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-subtle)", paddingTop: "10px" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                  {p.duration_s}s · {p.tempo} BPM · {p.key}
                </span>
                <span style={{ fontSize: "0.8rem", color: "var(--accent-primary)", fontWeight: 600, display: "flex", alignItems: "center", gap: "4px" }}>
                  Use Preset <ArrowRight size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Generations List */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>Recent Generations</div>
          <button onClick={() => onNavigate("history")} className="btn btn-secondary btn-sm">
            View All History
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--text-dim)" }}>
            <div className="animate-spin" style={{ display: "inline-block", marginBottom: "8px" }}>⏳</div>
            <div>Loading recent generations from backend...</div>
          </div>
        ) : error ? (
          <div style={{ padding: "20px", background: "rgba(239, 68, 68, 0.1)", borderRadius: "var(--radius-md)", color: "var(--danger)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
            {error}
          </div>
        ) : jobs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <Music size={36} color="var(--text-dim)" style={{ marginBottom: "12px" }} />
            <div style={{ fontWeight: 600, fontSize: "1rem", marginBottom: "6px" }}>No generation jobs found yet</div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-dim)", maxWidth: "380px", margin: "0 auto 16px" }}>
              Submit your first mood description to synthesize an exact-length background track with multitrack stems.
            </p>
            <button onClick={() => onNavigate("generate")} className="btn btn-primary btn-sm">
              Create First Track
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {jobs.slice(0, 5).map((job) => (
              <div
                key={job.job_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "14px 18px",
                  background: "rgba(10, 14, 23, 0.5)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div style={{ minWidth: "220px", flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <span className="font-mono" style={{ fontSize: "0.8rem", color: "var(--accent-secondary)", fontWeight: 600 }}>
                      {job.job_id}
                    </span>
                    <span
                      className={`badge ${
                        job.status === "succeeded"
                          ? "badge-success"
                          : job.status === "failed"
                          ? "badge-danger"
                          : "badge-warning"
                      }`}
                    >
                      {job.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-main)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "450px" }}>
                    {job.manifest?.prompt || "Background instrumental music"}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                    {job.manifest?.actual_duration_s ? `${job.manifest.actual_duration_s}s` : ""}
                  </span>
                  {job.status === "succeeded" && (
                    <button
                      onClick={() => onNavigate("studio", job.job_id)}
                      className="btn btn-secondary btn-sm"
                    >
                      Open in Studio
                    </button>
                  )}
                  {job.status === "queued" || job.status === "running" ? (
                    <button
                      onClick={() => onNavigate("studio", job.job_id)}
                      className="btn btn-outline btn-sm"
                    >
                      View Progress
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
