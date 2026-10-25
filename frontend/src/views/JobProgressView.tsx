import React, { useEffect, useState } from "react";
import { Copy, Check, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw, Loader2 } from "lucide-react";
import { apiClient } from "../services/apiClient";
import type { JobStatusResponse } from "../types/api";

interface JobProgressViewProps {
  jobId: string;
  onComplete: (jobId: string) => void;
  onRetry: () => void;
}

export const JobProgressView: React.FC<JobProgressViewProps> = ({
  jobId,
  onComplete,
  onRetry,
}) => {
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [pollingError, setPollingError] = useState<string | null>(null);

  useEffect(() => {
    let isSubscribed = true;
    let timerId: any = null;

    const poll = async () => {
      try {
        const data = await apiClient.getJob(jobId);
        if (!isSubscribed) return;
        setJob(data);

        if (data.status === "succeeded") {
          setTimeout(() => {
            if (isSubscribed) onComplete(jobId);
          }, 800);
        } else if (data.status !== "failed") {
          timerId = setTimeout(poll, 1000);
        }
      } catch (err: any) {
        if (!isSubscribed) return;
        setPollingError(err.message || "Failed to poll job status");
        timerId = setTimeout(poll, 2000);
      }
    };

    poll();

    return () => {
      isSubscribed = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [jobId]);

  const handleCopyId = () => {
    navigator.clipboard.writeText(jobId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const progress = job?.progress || 0;
  const status = job?.status || "queued";

  const steps = [
    { label: "Request validated & queued", threshold: 10 },
    { label: "Instrumental music generation", threshold: 45 },
    { label: "Multitrack stem separation", threshold: 65 },
    { label: "DSP finishing & loudness normalization", threshold: 80 },
    { label: "Audio packaging & MinIO upload", threshold: 90 },
    { label: "Quality verification & manifest assembly", threshold: 100 },
  ];

  return (
    <div className="panel" style={{ padding: "28px", maxWidth: "680px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Job ID:</span>
          <span className="font-mono" style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--accent-text)" }}>
            {jobId}
          </span>
          <button
            onClick={handleCopyId}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", padding: "2px" }}
            title="Copy Job ID"
            aria-label="Copy Job ID"
          >
            {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
          </button>
        </div>

        <span
          className={`badge ${
            status === "succeeded"
              ? "badge-success"
              : status === "failed"
              ? "badge-danger"
              : "badge-neutral"
          }`}
        >
          {status}
        </span>
      </div>

      {/* Title */}
      <h2 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: "6px" }}>
        {status === "queued" && "Queued for Synthesis"}
        {status === "running" && "Synthesizing Instrumental Audio"}
        {status === "succeeded" && "Audio Generation Complete"}
        {status === "failed" && "Processing Failed"}
      </h2>

      <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "24px" }}>
        {status === "queued" && "Waiting for audio worker to allocate synthesis slot..."}
        {status === "running" && "Generating instrumental tracks, isolating stems, and applying ITU-R BS.1770-4 normalization."}
        {status === "succeeded" && "All stems and master mix have been packaged and verified."}
        {status === "failed" && "The audio worker was unable to complete this generation."}
      </p>

      {pollingError && (
        <div style={{ color: "var(--warning)", fontSize: "0.78rem", marginBottom: "14px" }}>
          Reconnecting to backend service... ({pollingError})
        </div>
      )}

      {/* Progress Bar */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", fontWeight: 600, marginBottom: "6px" }}>
          <span style={{ color: "var(--text-muted)" }}>Progress</span>
          <span className="font-mono" style={{ color: "var(--accent-text)" }}>
            {progress}%
          </span>
        </div>
        <div
          style={{
            height: "6px",
            background: "var(--bg-canvas)",
            borderRadius: "var(--radius-full)",
            overflow: "hidden",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              background: status === "failed" ? "var(--danger)" : "var(--accent-primary)",
              transition: "width 0.3s ease",
            }}
          />
        </div>
      </div>

      {/* Steps List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "24px" }}>
        {steps.map((st, idx) => {
          const isDone = progress >= st.threshold;
          const isCurrent = progress < st.threshold && (idx === 0 || progress >= steps[idx - 1].threshold);
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 12px",
                background: isCurrent ? "var(--accent-subtle)" : "var(--bg-panel-subtle)",
                border: `1px solid ${isCurrent ? "var(--border-accent)" : "var(--border-subtle)"}`,
                borderRadius: "var(--radius-sm)",
              }}
            >
              {isDone ? (
                <CheckCircle2 size={15} color="var(--success)" style={{ flexShrink: 0 }} />
              ) : isCurrent ? (
                <Loader2 size={15} color="var(--accent-text)" className="animate-spin" style={{ flexShrink: 0 }} />
              ) : (
                <div style={{ width: "15px", height: "15px", borderRadius: "50%", border: "1px solid var(--text-muted)", flexShrink: 0 }} />
              )}
              <span
                style={{
                  fontSize: "0.82rem",
                  fontWeight: isCurrent || isDone ? 600 : 400,
                  color: isDone ? "var(--text-primary)" : isCurrent ? "var(--accent-text)" : "var(--text-muted)",
                }}
              >
                {st.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Error Details */}
      {status === "failed" && job?.error && (
        <div
          style={{
            padding: "12px 14px",
            background: "var(--danger-subtle)",
            border: "1px solid rgba(239, 68, 68, 0.25)",
            borderRadius: "var(--radius-md)",
            color: "var(--danger)",
            fontSize: "0.82rem",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 600, marginBottom: "4px" }}>
            <AlertTriangle size={15} />
            <span>
              {typeof job.error === "string" ? job.error : `[${job.error.code}] ${job.error.message}`}
            </span>
          </div>
          {typeof job.error !== "string" && job.error.details && Object.keys(job.error.details).length > 0 && (
            <pre className="font-mono" style={{ fontSize: "0.72rem", background: "rgba(0,0,0,0.25)", padding: "6px", borderRadius: "4px", overflowX: "auto", marginTop: "4px" }}>
              {JSON.stringify(job.error.details, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
        {status === "succeeded" && (
          <button onClick={() => onComplete(jobId)} className="btn btn-primary">
            <span>Open in Audio Studio</span>
            <ArrowRight size={14} />
          </button>
        )}

        {status === "failed" && (
          <button onClick={onRetry} className="btn btn-secondary">
            <RefreshCw size={14} />
            <span>Try Again</span>
          </button>
        )}
      </div>
    </div>
  );
};
