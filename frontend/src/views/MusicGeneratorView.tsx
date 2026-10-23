import React, { useState } from "react";
import { Sparkles, RefreshCw, AlertCircle, Plus, Trash2, ShieldAlert } from "lucide-react";
import { apiClient, ApiError } from "../services/apiClient";
import type { MusicJobRequest, SectionPlan } from "../types/api";

interface MusicGeneratorViewProps {
  initialValues?: {
    prompt?: string;
    duration_s?: number;
    tempo?: number;
    key?: string;
  };
  onJobCreated: (jobId: string) => void;
}

export const MusicGeneratorView: React.FC<MusicGeneratorViewProps> = ({
  initialValues,
  onJobCreated,
}) => {
  const [prompt, setPrompt] = useState(initialValues?.prompt || "");
  const [duration, setDuration] = useState(initialValues?.duration_s || 30);
  const [tempo, setTempo] = useState<number | "">(initialValues?.tempo || "");
  const [key, setKey] = useState(initialValues?.key || "");
  const [loopable, setLoopable] = useState(false);
  const [narrationUrl, setNarrationUrl] = useState("");
  const [seed, setSeed] = useState<number | "">("");
  const [sampleRate, setSampleRate] = useState(48000);
  const [targetLufs, setTargetLufs] = useState(-16.0);
  const [formats, setFormats] = useState<string[]>(["wav", "mp3"]);
  const [sections, setSections] = useState<SectionPlan[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const keysList = [
    "",
    "C major",
    "G major",
    "D minor",
    "A minor",
    "F major",
    "E minor",
    "Bb major",
    "D major",
  ];

  const handleAddSection = () => {
    const nextStart = sections.length === 0 ? 0 : Math.min(duration - 2, sections[sections.length - 1].start_s + 10);
    setSections([...sections, { start_s: Math.max(0, nextStart), mood: "" }]);
  };

  const handleRemoveSection = (idx: number) => {
    setSections(sections.filter((_, i) => i !== idx));
  };

  const handleUpdateSection = (idx: number, field: "start_s" | "mood", val: any) => {
    const updated = [...sections];
    updated[idx] = { ...updated[idx], [field]: val };
    setSections(updated);
  };

  const handleRandomizeSeed = () => {
    setSeed(Math.floor(Math.random() * 999999) + 1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError("Please describe the music you want to generate.");
      return;
    }
    if (duration < 5 || duration > 300) {
      setError("Duration must be between 5.0 and 300.0 seconds.");
      return;
    }

    setLoading(true);
    setError(null);

    // Create unique idempotency key for this submission attempt
    const idempotencyKey = `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

    const req: MusicJobRequest = {
      prompt: prompt.trim(),
      duration_s: Number(duration),
      tempo_bpm: tempo ? Number(tempo) : null,
      key: key || null,
      loopable,
      narration_url: narrationUrl.trim() || null,
      seed: seed ? Number(seed) : null,
      sections: sections.length > 0 ? sections : null,
      output: {
        sample_rate: sampleRate,
        target_lufs: Number(targetLufs),
        formats,
      },
    };

    try {
      const resp = await apiClient.createJob(req, idempotencyKey);
      onJobCreated(resp.job_id);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || "Failed to create music generation job");
      }
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "860px", margin: "0 auto" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.8rem", fontWeight: 800, letterSpacing: "-0.02em", marginBottom: "6px" }}>
          Compose Original Background Music
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.95rem" }}>
          Configure musical timing, style constraints, and multitrack stems for video synchronization.
        </p>
      </div>

      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-md)",
            padding: "14px 18px",
            color: "var(--danger)",
            marginBottom: "20px",
            fontSize: "0.9rem",
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      <form noValidate onSubmit={handleSubmit} className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "22px" }}>
        {/* Prompt */}
        <div className="form-group">
          <label className="form-label" htmlFor="prompt-input" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Music Description & Mood <span style={{ color: "var(--accent-primary)" }}>*</span></span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Instrumental only</span>
          </label>
          <textarea
            id="prompt-input"
            className="form-control"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. warm, optimistic acoustic folk with bright acoustic guitars, builds to an uplifting commercial finish"
            required
            rows={3}
          />
        </div>

        {/* Duration Slider & Input */}
        <div className="form-group">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <label className="form-label" htmlFor="duration-input">
              Duration (Exact Length): <strong style={{ color: "#fff" }}>{duration} seconds</strong>
            </label>
            <span className="badge badge-info font-mono" style={{ fontSize: "0.7rem" }}>
              ±0.05s precision
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <input
              type="range"
              min={5}
              max={300}
              step={1}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              id="duration-slider"
              aria-label="Target duration in seconds"
            />
            <input
              type="number"
              min={5}
              max={300}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="form-control font-mono"
              style={{ width: "90px", textAlign: "center" }}
              id="duration-input"
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px" }}>
            <span>5s (Short cut)</span>
            <span>45s (Standard promo)</span>
            <span>300s (5-min form)</span>
          </div>
        </div>

        {/* Musical Parameters: Tempo & Key */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="tempo-input">
              Tempo (BPM): <span style={{ color: "var(--text-dim)" }}>{tempo ? `${tempo} BPM` : "Auto-detect"}</span>
            </label>
            <input
              id="tempo-input"
              type="number"
              min={40}
              max={240}
              placeholder="e.g. 110"
              value={tempo}
              onChange={(e) => setTempo(e.target.value === "" ? "" : Number(e.target.value))}
              className="form-control font-mono"
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="key-select">
              Musical Key: <span style={{ color: "var(--text-dim)" }}>{key || "Auto-harmonize"}</span>
            </label>
            <select
              id="key-select"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="form-control"
            >
              <option value="">Auto (Model Decides)</option>
              {keysList.filter(Boolean).map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Dynamic Section Mood Changes */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>Video Section Changes (Advanced)</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                Align mood or instrumentation changes to video cut points.
              </div>
            </div>
            <button type="button" onClick={handleAddSection} className="btn btn-secondary btn-sm">
              <Plus size={14} /> Add Cut Point
            </button>
          </div>

          {sections.length === 0 ? (
            <div style={{ padding: "14px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "var(--radius-md)", fontSize: "0.8rem", color: "var(--text-dim)", textAlign: "center" }}>
              No custom sections defined. The piece will evolve continuously across the full duration.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {sections.map((sec, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    background: "rgba(10, 14, 23, 0.7)",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Start (s):</span>
                    <input
                      type="number"
                      step={0.5}
                      min={0}
                      max={duration}
                      value={sec.start_s}
                      onChange={(e) => handleUpdateSection(idx, "start_s", parseFloat(e.target.value) || 0)}
                      className="form-control font-mono"
                      style={{ width: "75px", padding: "6px 8px", fontSize: "0.85rem" }}
                    />
                  </div>

                  <input
                    type="text"
                    placeholder="Section mood (e.g., build-up, drums drop out, uplifting climax)"
                    value={sec.mood}
                    onChange={(e) => handleUpdateSection(idx, "mood", e.target.value)}
                    className="form-control"
                    style={{ flex: 1, padding: "6px 12px", fontSize: "0.85rem" }}
                  />

                  <button
                    type="button"
                    onClick={() => handleRemoveSection(idx)}
                    style={{ background: "none", border: "none", color: "var(--danger)", cursor: "pointer", padding: "6px" }}
                    aria-label="Remove section"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Voiceover Narration URL (Auto-Ducking) */}
        <div className="form-group" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "16px", marginBottom: 0 }}>
          <label className="form-label" htmlFor="narration-url-input" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Voiceover Narration Audio URL (Optional)</span>
            <span style={{ fontSize: "0.75rem", color: "var(--accent-secondary)" }}>Sidechain Ducking (-10 dB)</span>
          </label>
          <input
            id="narration-url-input"
            type="url"
            value={narrationUrl}
            onChange={(e) => setNarrationUrl(e.target.value)}
            placeholder="https://example.com/voiceover.wav"
            className="form-control"
          />
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
            <ShieldAlert size={14} color="var(--text-dim)" />
            <span>Protected against SSRF. Private/internal network URLs are strictly forbidden.</span>
          </div>
        </div>

        {/* Loopable Toggle */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 0" }}>
          <input
            type="checkbox"
            id="loopable-toggle"
            checked={loopable}
            onChange={(e) => setLoopable(e.target.checked)}
            style={{ width: "18px", height: "18px", accentColor: "var(--accent-primary)", cursor: "pointer" }}
          />
          <label htmlFor="loopable-toggle" className="form-label" style={{ marginBottom: 0, cursor: "pointer", fontSize: "0.9rem" }}>
            Loopable Music Cue (smooth seamless loop for infinite background beds)
          </label>
        </div>

        {/* Advanced Output Settings */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", borderTop: "1px solid var(--border-subtle)", paddingTop: "16px" }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="seed-input">Random Seed (Reproducibility)</label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                id="seed-input"
                type="number"
                placeholder="Random"
                value={seed}
                onChange={(e) => setSeed(e.target.value === "" ? "" : Number(e.target.value))}
                className="form-control font-mono"
              />
              <button type="button" onClick={handleRandomizeSeed} className="btn btn-secondary btn-sm" title="Generate random seed">
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="sample-rate-select">Sample Rate</label>
            <select
              id="sample-rate-select"
              value={sampleRate}
              onChange={(e) => setSampleRate(Number(e.target.value))}
              className="form-control font-mono"
            >
              <option value={48000}>48,000 Hz (Video Standard)</option>
              <option value={44100}>44,100 Hz (CD Audio)</option>
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" htmlFor="lufs-select">Loudness Target (ITU-R BS.1770-4)</label>
            <select
              id="lufs-select"
              value={targetLufs}
              onChange={(e) => setTargetLufs(Number(e.target.value))}
              className="form-control font-mono"
            >
              <option value={-16.0}>-16.0 LUFS (Video / Web Standard)</option>
              <option value={-14.0}>-14.0 LUFS (Spotify / YouTube)</option>
              <option value={-23.0}>-23.0 LUFS (Broadcast EBU R128)</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Output Formats</label>
            <div style={{ display: "flex", gap: "16px", alignItems: "center", height: "38px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={formats.includes("wav")}
                  onChange={(e) => {
                    if (e.target.checked) setFormats([...formats, "wav"]);
                    else setFormats(formats.filter((f) => f !== "wav"));
                  }}
                  style={{ accentColor: "var(--accent-primary)" }}
                />
                WAV (PCM)
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={formats.includes("mp3")}
                  onChange={(e) => {
                    if (e.target.checked) setFormats([...formats, "mp3"]);
                    else setFormats(formats.filter((f) => f !== "mp3"));
                  }}
                  style={{ accentColor: "var(--accent-primary)" }}
                />
                MP3 (320 kbps)
              </label>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div style={{ paddingTop: "12px" }}>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ width: "100%", padding: "14px", fontSize: "1.05rem" }}
          >
            {loading ? (
              <>
                <div className="animate-spin">⏳</div>
                <span>Submitting Generation Task...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Generate Music Track ({duration}s · 5 Stems)</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
