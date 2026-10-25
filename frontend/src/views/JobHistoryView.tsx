import React, { useEffect, useState } from "react";
import { Search, RefreshCw, Music, Clock, AlertCircle } from "lucide-react";
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

  useEffect(() => {
    let ignore = false;
    apiClient.listJobs(50).then(
      (data) => {
        if (!ignore) {
          setJobs(data);
          setLoading(false);
        }
      },
      (err: any) => {
        if (!ignore) {
          setError(err.message || "Failed to load job history from backend");
          setLoading(false);
        }
      }
    );
    return () => {
      ignore = true;
    };
  }, []);

  const filteredJobs = jobs.filter((j) => {
    const matchesStatus = statusFilter === "all" || j.status === statusFilter;
    const matchesSearch =
      search === "" ||
      j.job_id.toLowerCase().includes(search.toLowerCase()) ||
      (j.manifest?.prompt && j.manifest.prompt.toLowerCase().includes(search.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  const formatDate = (isoString?: string) => {
    if (!isoString) return "--";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.01em", color: "var(--text-primary)" }}>
            Generation History
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
            Past music generation jobs retrieved from the backend engine.
          </p>
        </div>

        <button onClick={fetchJobs} disabled={loading} className="btn btn-secondary btn-sm">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter and Search */}
      <div className="panel" style={{ padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "240px" }}>
          <Search size={15} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search by prompt or Job ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-control"
            style={{ padding: "6px 10px", fontSize: "0.82rem" }}
          />
        </div>

        <div style={{ display: "flex", gap: "4px" }}>
          {["all", "succeeded", "failed", "running"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className="btn btn-sm"
              style={{
                padding: "3px 10px",
                fontSize: "0.76rem",
                textTransform: "capitalize",
                background: statusFilter === st ? "var(--accent-subtle)" : "transparent",
                color: statusFilter === st ? "var(--accent-text)" : "var(--text-muted)",
                borderColor: statusFilter === st ? "var(--accent-primary)" : "var(--border-subtle)",
              }}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "12px 16px", background: "var(--danger-subtle)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "var(--radius-md)", color: "var(--danger)", fontSize: "0.82rem" }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Jobs List */}
      {loading ? (
        <div className="panel" style={{ padding: "36px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Loading generation history...
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="panel" style={{ padding: "48px 20px", textAlign: "center" }}>
          <Clock size={32} color="var(--text-muted)" style={{ marginBottom: "10px" }} />
          <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
            No jobs found
          </div>
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", maxWidth: "340px", margin: "0 auto 16px" }}>
            {search || statusFilter !== "all"
              ? "No jobs match your current search criteria."
              : "Generate a music cue in the studio to see your history here."}
          </div>
          <button onClick={() => onNavigate("studio")} className="btn btn-primary btn-sm">
            Go to Studio
          </button>
        </div>
      ) : (
        <div className="panel" style={{ overflow: "hidden" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {filteredJobs.map((j, idx) => {
              const isSucc = j.status === "succeeded";
              const duration = j.manifest?.duration_s || j.manifest?.actual_duration_s;

              return (
                <div
                  key={j.job_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "14px 18px",
                    borderBottom: idx < filteredJobs.length - 1 ? "1px solid var(--border-subtle)" : "none",
                    flexWrap: "wrap",
                    gap: "12px",
                    transition: "background var(--transition-fast)",
                  }}
                >
                  <div style={{ flex: 1, minWidth: "240px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
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
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        · {formatDate(j.created_at)}
                      </span>
                    </div>

                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {j.manifest?.prompt || "Instrumental Track"}
                    </div>

                    {duration && (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                        Duration: {duration}s · 48 kHz WAV
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {isSucc && (
                      <button
                        onClick={() => onNavigate("studio", j.job_id)}
                        className="btn btn-secondary btn-sm"
                        style={{ padding: "5px 12px" }}
                      >
                        <Music size={13} />
                        <span>Open in Studio</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
