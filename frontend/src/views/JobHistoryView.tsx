import React, { useEffect, useState } from "react";
import { Search, RefreshCw, Music, FileText } from "lucide-react";
import { apiClient } from "../services/apiClient";
import type { JobStatusResponse } from "../types/api";

interface JobHistoryViewProps {
  onNavigate: (tab: string, jobId?: string) => void;
}

export const JobHistoryView: React.FC<JobHistoryViewProps> = ({ onNavigate }) => {
  const [jobs, setJobs] = useState<JobStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.listJobs(50);
      setJobs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load job history from backend");
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = jobs.filter((j) => {
    const matchesStatus = statusFilter === "all" || j.status === statusFilter;
    const matchesSearch =
      search === "" ||
      j.job_id.toLowerCase().includes(search.toLowerCase()) ||
      (j.manifest?.prompt && j.manifest.prompt.toLowerCase().includes(search.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 800, letterSpacing: "-0.02em" }}>Job Generation History</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
            Real-time record of all synthesis jobs retrieved directly from the PostgreSQL backend.
          </p>
        </div>

        <button onClick={fetchJobs} disabled={loading} className="btn btn-secondary btn-sm">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: "260px" }}>
          <Search size={18} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search by prompt or Job ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-control"
            style={{ padding: "8px 12px", fontSize: "0.88rem" }}
          />
        </div>

        <div style={{ display: "flex", gap: "6px" }}>
          {["all", "succeeded", "failed", "running"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className="btn btn-sm"
              style={{
                backgroundColor: statusFilter === st ? "rgba(139, 92, 246, 0.2)" : "rgba(255, 255, 255, 0.03)",
                color: statusFilter === st ? "#fff" : "var(--text-muted)",
                borderColor: statusFilter === st ? "var(--accent-primary)" : "var(--border-subtle)",
                textTransform: "capitalize",
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Table of Jobs */}
      <div className="glass-panel" style={{ padding: "16px", overflowX: "auto" }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: "50px", color: "var(--text-dim)" }}>
            <div className="animate-spin" style={{ display: "inline-block", marginBottom: "8px" }}>⏳</div>
            <div>Retrieving jobs from API...</div>
          </div>
        ) : error ? (
          <div style={{ padding: "20px", color: "var(--danger)" }}>{error}</div>
        ) : filteredJobs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "50px 20px", color: "var(--text-muted)" }}>
            <Music size={36} color="var(--text-dim)" style={{ marginBottom: "12px" }} />
            <div style={{ fontWeight: 600 }}>No jobs match your filter criteria</div>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left", color: "var(--text-dim)" }}>
                <th style={{ padding: "12px 16px" }}>Job ID</th>
                <th style={{ padding: "12px 16px" }}>Prompt & Style</th>
                <th style={{ padding: "12px 16px" }}>Duration</th>
                <th style={{ padding: "12px 16px" }}>Status</th>
                <th style={{ padding: "12px 16px" }}>Created</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredJobs.map((job) => (
                <tr
                  key={job.job_id}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background 0.2s",
                  }}
                >
                  <td style={{ padding: "14px 16px" }}>
                    <span className="font-mono" style={{ fontWeight: 600, color: "var(--accent-secondary)" }}>
                      {job.job_id}
                    </span>
                  </td>

                  <td style={{ padding: "14px 16px", maxWidth: "320px" }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {job.manifest?.prompt || "Background instrumental music"}
                    </div>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <span className="font-mono">{job.manifest?.actual_duration_s ?? "--"}s</span>
                  </td>

                  <td style={{ padding: "14px 16px" }}>
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
                  </td>

                  <td style={{ padding: "14px 16px", color: "var(--text-dim)", fontSize: "0.8rem" }}>
                    {new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "8px" }}>
                      {job.status === "succeeded" && (
                        <>
                          <button
                            onClick={() => onNavigate("studio", job.job_id)}
                            className="btn btn-secondary btn-sm"
                            title="Open in Multitrack Studio"
                          >
                            Studio
                          </button>
                          <button
                            onClick={() => onNavigate("manifest", job.job_id)}
                            className="btn btn-outline btn-sm"
                            title="View Manifest"
                          >
                            <FileText size={13} />
                          </button>
                        </>
                      )}
                      {(job.status === "queued" || job.status === "running") && (
                        <button
                          onClick={() => onNavigate("studio", job.job_id)}
                          className="btn btn-outline btn-sm"
                        >
                          Progress
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
