import { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { MusicGeneratorView } from "./views/MusicGeneratorView";
import { JobProgressView } from "./views/JobProgressView";
import { AudioStudioView } from "./views/AudioStudioView";
import { JobHistoryView } from "./views/JobHistoryView";
import { apiClient } from "./services/apiClient";
import type { JobStatusResponse } from "./types/api";

export function App() {
  const [activeTab, setActiveTab] = useState<string>("studio");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<JobStatusResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
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
      .then((data) => {
        setCurrentJob(data);
        if (data.status === "succeeded") {
          setIsGenerating(false);
        }
      })
      .catch((err) => console.warn("Failed to fetch active job details:", err));
  }, [currentJobId]);

  const handleNavigate = (tab: string, jobId?: string) => {
    if (jobId) {
      setCurrentJobId(jobId);
    }
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleJobCreated = (jobId: string, uploadedVideo?: File) => {
    setCurrentJobId(jobId);
    setIsGenerating(true);
    if (uploadedVideo) {
      setVideoFile(uploadedVideo);
      if (videoUrl) URL.revokeObjectURL(videoUrl);
      setVideoUrl(URL.createObjectURL(uploadedVideo));
    }
    setActiveTab("studio");
  };

  const handleJobCompleted = (jobId: string) => {
    setCurrentJobId(jobId);
    setIsGenerating(false);
    apiClient.getJob(jobId).then((data) => {
      setCurrentJob(data);
    });
  };

  const handleNewGeneration = () => {
    setCurrentJob(null);
    setCurrentJobId(null);
    setIsGenerating(false);
    setGeneratorPresets(undefined);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", backgroundColor: "var(--bg-canvas)" }}>
      <Navbar activeTab={activeTab} onTabChange={handleNavigate} />

      <main className="container" style={{ flex: 1, padding: "28px 20px" }}>
        {/* Studio Destination: Unified Music Generation & Audio Workspace */}
        {(activeTab === "studio" || activeTab === "generate" || activeTab === "progress") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* If currently processing a job, show real-time progress card */}
            {isGenerating && currentJobId ? (
              <JobProgressView
                jobId={currentJobId}
                onComplete={handleJobCompleted}
                onRetry={handleNewGeneration}
              />
            ) : currentJob && currentJob.status === "succeeded" ? (
              /* If job succeeded, display clean audio studio results */
              <AudioStudioView
                job={currentJob}
                videoUrl={videoUrl}
                videoFile={videoFile}
                onNavigate={handleNavigate}
                onNewGeneration={handleNewGeneration}
              />
            ) : (
              /* Primary Prompt & Generation Studio */
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ marginBottom: "4px" }}>
                  <h1 style={{ fontSize: "1.5rem", fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
                    AI Background Music Studio
                  </h1>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "2px" }}>
                    Generate original instrumental cues timed to video edit points with uncompressed 48 kHz WAV stems.
                  </p>
                </div>

                <MusicGeneratorView
                  initialValues={generatorPresets}
                  onJobCreated={handleJobCreated}
                  isGenerating={isGenerating}
                />
              </div>
            )}
          </div>
        )}

        {/* History Destination: Compact Previous Generations */}
        {activeTab === "history" && (
          <JobHistoryView onNavigate={handleNavigate} />
        )}
      </main>

      {/* Minimal Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "16px 0",
          background: "var(--bg-panel)",
          color: "var(--text-muted)",
          fontSize: "0.78rem",
          marginTop: "48px",
        }}
      >
        <div
          className="container"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <div>IncuBrix Studio · Professional AI Background Music Engine</div>
          <div style={{ display: "flex", gap: "14px" }}>
            <span>48 kHz 24-bit WAV</span>
            <span>ITU-R BS.1770-4 (-16 LUFS)</span>
            <span>Commercial License</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
