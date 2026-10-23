import { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { DashboardView } from "./views/DashboardView";
import { MusicGeneratorView } from "./views/MusicGeneratorView";
import { JobProgressView } from "./views/JobProgressView";
import { AudioStudioView } from "./views/AudioStudioView";
import { ManifestView } from "./views/ManifestView";
import { JobHistoryView } from "./views/JobHistoryView";
import { apiClient } from "./services/apiClient";
import type { JobStatusResponse } from "./types/api";

export function App() {
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<JobStatusResponse | null>(null);
  const [generatorPresets, setGeneratorPresets] = useState<{
    prompt?: string;
    duration_s?: number;
    tempo?: number;
    key?: string;
  } | undefined>(undefined);

  // Load job details when currentJobId changes
  useEffect(() => {
    if (!currentJobId) return;

    apiClient
      .getJob(currentJobId)
      .then((data) => setCurrentJob(data))
      .catch((err) => console.warn("Failed to fetch active job details:", err));
  }, [currentJobId]);

  const handleNavigate = (tab: string, jobId?: string) => {
    if (jobId) {
      setCurrentJobId(jobId);
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    setActiveTab("progress");
  };

  const handleJobCompleted = (jobId: string) => {
    setCurrentJobId(jobId);
    // Reload full job details with result links and manifest
    apiClient.getJob(jobId).then((data) => {
      setCurrentJob(data);
      setActiveTab("studio");
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Navbar activeTab={activeTab} onTabChange={handleNavigate} />

      <main className="container" style={{ flex: 1, padding: "32px 20px" }}>
        {activeTab === "dashboard" && (
          <DashboardView
            onNavigate={handleNavigate}
            onSelectPreset={(p) => setGeneratorPresets(p)}
          />
        )}

        {activeTab === "generate" && (
          <MusicGeneratorView
            initialValues={generatorPresets}
            onJobCreated={handleJobCreated}
          />
        )}

        {activeTab === "progress" && currentJobId && (
          <JobProgressView
            jobId={currentJobId}
            onComplete={handleJobCompleted}
            onRetry={() => setActiveTab("generate")}
          />
        )}

        {activeTab === "studio" && (
          <AudioStudioView job={currentJob} onNavigate={handleNavigate} />
        )}

        {activeTab === "manifest" && (
          <ManifestView job={currentJob} onNavigate={handleNavigate} />
        )}

        {activeTab === "history" && (
          <JobHistoryView onNavigate={handleNavigate} />
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "24px 0",
          background: "rgba(10, 14, 23, 0.9)",
          color: "var(--text-dim)",
          fontSize: "0.8rem",
          marginTop: "40px",
        }}
      >
        <div
          className="container"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            IncuBrix AI Background Music Engine · Engineering Assessment 1
          </div>
          <div style={{ display: "flex", gap: "16px" }}>
            <span>48 kHz 24-bit PCM WAV</span>
            <span>ITU-R BS.1770-4 (-16 LUFS)</span>
            <span>Commercial Rights Verified</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
