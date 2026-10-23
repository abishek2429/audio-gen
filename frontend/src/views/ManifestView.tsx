import React, { useState } from "react";
import { Download, FileJson, ArrowLeft, ShieldCheck, Clock, Check, Copy } from "lucide-react";
import type { JobStatusResponse } from "../types/api";

interface ManifestViewProps {
  job: JobStatusResponse | null;
  onNavigate: (tab: string, jobId?: string) => void;
}

export const ManifestView: React.FC<ManifestViewProps> = ({ job, onNavigate }) => {
  const [copied, setCopied] = useState(false);

  if (!job || !job.manifest) {
    return (
      <div className="glass-panel" style={{ padding: "60px 20px", textAlign: "center" }}>
        <FileJson size={42} color="var(--text-dim)" style={{ marginBottom: "14px" }} />
        <h2 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: "8px" }}>No Manifest Selected</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: "420px", margin: "0 auto 20px" }}>
          Select a completed job from the history to inspect its machine-readable metadata manifest.
        </p>
        <button onClick={() => onNavigate("history")} className="btn btn-primary">
          View Job History
        </button>
      </div>
    );
  }

  const manifest = job.manifest;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(manifest, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `manifest_${job.job_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div
        className="glass-panel"
        style={{
          padding: "24px 30px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <button
            onClick={() => onNavigate("studio", job.job_id)}
            style={{
              background: "none",
              border: "none",
              color: "var(--text-dim)",
              fontSize: "0.8rem",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              cursor: "pointer",
              marginBottom: "6px",
            }}
          >
            <ArrowLeft size={14} /> Open in Audio Studio
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "1.6rem", fontWeight: 800 }}>Production Manifest</h1>
            <span className="badge badge-info">music_manifest.json</span>
          </div>
          <p className="font-mono" style={{ color: "var(--accent-secondary)", fontSize: "0.85rem", marginTop: "4px" }}>
            Job: {manifest.job_id}
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleCopyJson} className="btn btn-secondary btn-sm">
            {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
            <span>{copied ? "Copied" : "Copy JSON"}</span>
          </button>
          <button onClick={handleDownloadJson} className="btn btn-primary btn-sm">
            <Download size={14} />
            <span>Download JSON</span>
          </button>
        </div>
      </div>

      {/* Structured Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Composition & Model Provenance */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "16px" }}>Model & Engine Provenance</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.88rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Music Generator</span>
              <span className="font-mono" style={{ color: "#fff" }}>{manifest.models?.music_generator || "mock:v1"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Stem Separator</span>
              <span className="font-mono" style={{ color: "#fff" }}>{manifest.models?.stem_separator || "mock:v1"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Tempo & Key</span>
              <span style={{ fontWeight: 600 }}>{manifest.tempo_bpm} BPM · {manifest.key}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Random Seed</span>
              <span className="font-mono">{manifest.seed ?? "None"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-dim)" }}>API Cost</span>
              <span className="font-mono" style={{ color: "var(--success)" }}>${Number(manifest.cost_usd || 0).toFixed(4)}</span>
            </div>
          </div>
        </div>

        {/* Commercial Licensing & Clearance */}
        <div className="glass-panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <ShieldCheck size={20} color="var(--success)" />
            <h2 style={{ fontSize: "1.1rem", fontWeight: 700 }}>Commercial Rights & Provenance</h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.88rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Commercial Clearance</span>
              <span className="badge badge-success">Cleared for Video Sync</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>License Type</span>
              <span>{manifest.commercial_license?.license_type || "Royalty-Free Sync"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--text-dim)" }}>Attribution Required</span>
              <span>{manifest.commercial_license?.attribution_required ? "Yes" : "No"}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-dim)" }}>Terms Audit</span>
              <span className="font-mono" style={{ color: "var(--accent-secondary)" }}>SOURCES.md</span>
            </div>
          </div>
        </div>
      </div>

      {/* Latency & Audio Metrics */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Clock size={18} color="var(--accent-primary)" />
          <span>Execution Latency Breakdown</span>
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
          <div style={{ padding: "12px", background: "rgba(10, 14, 23, 0.5)", borderRadius: "var(--radius-md)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Music Generation</div>
            <div className="font-mono" style={{ fontSize: "1.2rem", fontWeight: 700 }}>
              {manifest.timings_s?.generation_time_s ?? "--"}s
            </div>
          </div>
          <div style={{ padding: "12px", background: "rgba(10, 14, 23, 0.5)", borderRadius: "var(--radius-md)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Stem Separation</div>
            <div className="font-mono" style={{ fontSize: "1.2rem", fontWeight: 700 }}>
              {manifest.timings_s?.separation_time_s ?? "--"}s
            </div>
          </div>
          <div style={{ padding: "12px", background: "rgba(10, 14, 23, 0.5)", borderRadius: "var(--radius-md)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>DSP Finishing</div>
            <div className="font-mono" style={{ fontSize: "1.2rem", fontWeight: 700 }}>
              {manifest.timings_s?.dsp_time_s ?? "--"}s
            </div>
          </div>
          <div style={{ padding: "12px", background: "rgba(10, 14, 23, 0.5)", borderRadius: "var(--radius-md)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Total Elapsed</div>
            <div className="font-mono" style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-secondary)" }}>
              {manifest.timings_s?.total_elapsed_s ?? "--"}s
            </div>
          </div>
        </div>
      </div>

      {/* Raw JSON View */}
      <div className="glass-panel" style={{ padding: "24px" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "12px" }}>Raw Manifest Payload</h2>
        <pre
          className="font-mono"
          style={{
            background: "rgba(8, 11, 18, 0.95)",
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8rem",
            color: "#e2e8f0",
            maxHeight: "360px",
            overflow: "auto",
            lineHeight: 1.5,
          }}
        >
          {JSON.stringify(manifest, null, 2)}
        </pre>
      </div>
    </div>
  );
};
