import React, { useState } from "react";
import { Download, FileJson, ArrowLeft, Check, Copy } from "lucide-react";
import type { JobStatusResponse } from "../types/api";

interface ManifestViewProps {
  job: JobStatusResponse | null;
  onNavigate: (tab: string, jobId?: string) => void;
}

export const ManifestView: React.FC<ManifestViewProps> = ({ job, onNavigate }) => {
  const [copied, setCopied] = useState(false);

  if (!job || !job.manifest) {
    return (
      <div className="panel" style={{ padding: "48px 20px", textAlign: "center", maxWidth: "540px", margin: "0 auto" }}>
        <FileJson size={36} color="var(--text-muted)" style={{ marginBottom: "12px" }} />
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "6px" }}>No Manifest Selected</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", maxWidth: "380px", margin: "0 auto 16px" }}>
          Select a completed track from generation history to inspect its metadata manifest.
        </p>
        <button onClick={() => onNavigate("history")} className="btn btn-primary btn-sm">
          View History
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
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div className="panel" style={{ padding: "18px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <button
            onClick={() => onNavigate("studio", job.job_id)}
            className="btn btn-ghost btn-sm"
            style={{ padding: "0 0 6px 0", fontSize: "0.78rem" }}
          >
            <ArrowLeft size={13} />
            <span>Back to Studio</span>
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--text-primary)" }}>Technical Manifest</h1>
            <span className="font-mono" style={{ fontSize: "0.78rem", color: "var(--accent-text)" }}>
              [{job.job_id}]
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={handleCopyJson} className="btn btn-secondary btn-sm">
            {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
            <span>{copied ? "Copied" : "Copy JSON"}</span>
          </button>
          <button onClick={handleDownloadJson} className="btn btn-secondary btn-sm">
            <Download size={14} />
            <span>Download</span>
          </button>
        </div>
      </div>

      {/* JSON Viewer */}
      <div className="panel" style={{ padding: "16px" }}>
        <pre
          className="font-mono"
          style={{
            fontSize: "0.76rem",
            background: "var(--bg-canvas)",
            padding: "16px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            overflowX: "auto",
            maxHeight: "500px",
            color: "var(--text-secondary)",
          }}
        >
          {JSON.stringify(manifest, null, 2)}
        </pre>
      </div>
    </div>
  );
};
