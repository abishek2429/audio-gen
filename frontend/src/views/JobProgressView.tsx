import React, { useEffect, useState } from "react";
import { Copy, Check, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw } from "lucide-react";
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
          // Auto-trigger completion after brief delay
          setTimeout(() => {
            if (isSubscribed) onComplete(jobId);
          }, 1200);
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
    <div style={{ maxWidth: "700px", margin: "0 auto" }}>
      <div className="glass-panel" style={{ padding: "36px", textAlign: "center" }}>
        {/* Job Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", marginBottom: "16px" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Job Identifier:</span>
          <span className="font-mono" style={{ fontWeight: 700, color: "var(--accent-secondary)" }}>
            {jobId}
          </span>
          <button
            onClick={handleCopyId}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex" }}
            title="Copy Job ID"
            aria-label="Copy Job ID"
          >
            {copied ? <Check size={16} color="var(--success)" /> : <Copy size={16} />}
          </button>
        </div>

        {/* Status Title */}
        <h2 style={{ fontSize: "1.8rem", fontWeight: 800, marginBottom: "8px" }}>
          {status === "queued" && "Job Queued"}
          {status === "running" && "Synthesizing Audio..."}
          {status === "succeeded" && "Audio Generation Complete!"}
          {status === "failed" && "Processing Failed"}
        </h2>

        <p style={{ color: "var(--text-muted)", fontSize: "0.95rem", marginBottom: "28px" }}>
          {status === "queued" && "Waiting for audio worker pick-up..."}
          {status === "running" && "Executing multi-stage neural synthesis, stem separation, and 48 kHz finishing."}
          {status === "succeeded" && "All quality gates verified. Your mix and stems are ready."}
          {status === "failed" && "An error occurred during audio generation."}
        </p>

        {pollingError && (
          <div style={{ color: "var(--warning)", fontSize: "0.8rem", marginBottom: "16px" }}>
            Reconnecting to audio engine... ({pollingError})
          </div>
        )}

        {/* Progress Bar */}
        <div style={{ marginBottom: "32px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px" }}>
            <span style={{ color: "var(--text-muted)" }}>Progress</span>
            <span className="font-mono" style={{ color: "var(--accent-primary)" }}>
              {progress}%
            </span>
          </div>
          <div
            style={{
              height: "10px",
              background: "rgba(255, 255, 255, 0.08)",
              borderRadius: "var(--radius-full)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${progress}%`,
                background:
                  status === "failed"
                    ? "var(--danger)"
                    : "var(--accent-gradient)",
                transition: "width 0.4s ease",
              }}
            />
          </div>
        </div>

        {/* Step Progression Checkpoints */}
        <div style={{ textAlign: "left", display: "flex", flexDirection: "column", gap: "12px", marginBottom: "32px" }}>
          {steps.map((st, idx) => {
            const isDone = progress >= st.threshold;
            const isCurrent = progress < st.threshold && (idx === 0 || progress >= steps[idx - 1].threshold);
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "10px 14px",
                  background: isCurrent ? "rgba(139, 92, 246, 0.1)" : "rgba(255, 255, 255, 0.02)",
                  border: `1px solid ${isCurrent ? "rgba(139, 92, 246, 0.3)" : "var(--border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                  transition: "all 0.2s ease",
                }}
              >
                {isDone ? (
                  <CheckCircle2 size={18} color="var(--success)" />
                ) : isCurrent ? (
                  <div className="animate-spin" style={{ width: "18px", height: "18px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    ⏳
                  </div>
                ) : (
                  <div style={{ width: "18px", height: "18px", borderRadius: "50%", border: "2px solid var(--text-dim)" }} />
                )}
                <span
                  style={{
                    fontSize: "0.85rem",
                    fontWeight: isCurrent || isDone ? 600 : 400,
                    color: isDone ? "var(--text-main)" : isCurrent ? "var(--accent-secondary)" : "var(--text-dim)",
                  }}
                >
                  {st.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Failure Details */}
        {status === "failed" && job?.error && (
          <div
            style={{
              padding: "16px",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "var(--radius-md)",
              color: "var(--danger)",
              textAlign: "left",
              marginBottom: "24px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, marginBottom: "4px" }}>
              <AlertTriangle size={18} />
              <span>
                {typeof job.error === "string"
                  ? job.error
                  : `[${job.error.code}] ${job.error.message}`}
              </span>
            </div>
            {typeof job.error !== "string" && job.error.details && (
              <pre className="font-mono" style={{ fontSize: "0.75rem", background: "rgba(0,0,0,0.3)", padding: "8px", borderRadius: "4px", overflowX: "auto" }}>
                {JSON.stringify(job.error.details, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: "flex", justifyContent: "center", gap: "14px" }}>
          {status === "succeeded" && (
            <button onClick={() => onComplete(jobId)} className="btn btn-primary" style={{ padding: "12px 28px" }}>
              <span>Open in Audio Studio</span>
              <ArrowRight size={18} />
            </button>
          )}

          {status === "failed" && (
            <button onClick={onRetry} className="btn btn-secondary">
              <RefreshCw size={16} />
              <span>Create New Request</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
