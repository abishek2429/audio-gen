import React, { useState } from "react";
import { Sparkles, ChevronDown, ChevronUp, Plus, Trash2, AlertCircle, Film } from "lucide-react";
import { apiClient, ApiError } from "../services/apiClient";
import type { MusicJobRequest, SectionPlan } from "../types/api";
import { VideoToBeatView } from "./VideoToBeatView";

interface MusicGeneratorViewProps {
  initialValues?: {
    prompt?: string;
    duration_s?: number;
    tempo?: number;
    key?: string;
  };
  onJobCreated: (jobId: string, videoFile?: File) => void;
  isGenerating?: boolean;
}

export const MusicGeneratorView: React.FC<MusicGeneratorViewProps> = ({
  initialValues,
  onJobCreated,
  isGenerating = false,
}) => {
  const [prompt, setPrompt] = useState(initialValues?.prompt || "");
  const [duration, setDuration] = useState(initialValues?.duration_s || 30);
  const [tempo, setTempo] = useState<number | "">(initialValues?.tempo || "");
  const [key, setKey] = useState(initialValues?.key || "");
  const [loopable, setLoopable] = useState(false);
  const [narrationUrl, setNarrationUrl] = useState("");
  const [sections, setSections] = useState<SectionPlan[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"prompt" | "video">("prompt");

  const examplePrompts = [
    { label: "Cinematic", text: "dramatic cinematic orchestral, soaring strings, epic drums, builds to climax" },
    { label: "Corporate", text: "uplifting tech corporate acoustic folk, bright acoustic guitars, light percussion" },
    { label: "Lo-Fi", text: "relaxing lo-fi chillhop with vintage vinyl crackle, gentle electric piano" },
    { label: "Electronic", text: "modern pulsating synthwave, driving electronic beats, clean melodic bassline" },
  ];

  const quickDurations = [15, 30, 45, 60];

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

    const idempotencyKey = `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

    const req: MusicJobRequest = {
      prompt: prompt.trim(),
      duration_s: Number(duration),
      tempo_bpm: tempo ? Number(tempo) : null,
      key: key || null,
      loopable,
      narration_url: narrationUrl.trim() || null,
      sections: sections.length > 0 ? sections : null,
      output: {
        sample_rate: 48000,
        target_lufs: -16.0,
        formats: ["wav", "mp3"],
      },
    };

    try {
      const resp = await apiClient.createJob(req, idempotencyKey);
      onJobCreated(resp.job_id);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || "Failed to start music generation. Please verify backend connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  const busy = loading || isGenerating;

  return (
    <div className="panel" style={{ padding: "24px 28px" }}>
      {/* Creation Mode Switcher: Prompt vs Video-to-Beat */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid var(--border-subtle)",
          paddingBottom: "16px",
          marginBottom: "20px",
        }}
      >
        <button
          type="button"
          onClick={() => setMode("prompt")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "var(--radius-md)",
            border: `1px solid ${mode === "prompt" ? "var(--accent-primary)" : "var(--border-subtle)"}`,
            background: mode === "prompt" ? "var(--accent-subtle)" : "transparent",
            color: mode === "prompt" ? "var(--accent-text)" : "var(--text-secondary)",
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all var(--transition-fast)",
          }}
        >
          <Sparkles size={15} />
          <span>Prompt to Music</span>
        </button>

        <button
          type="button"
          onClick={() => setMode("video")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "var(--radius-md)",
            border: `1px solid ${mode === "video" ? "var(--accent-primary)" : "var(--border-subtle)"}`,
            background: mode === "video" ? "var(--accent-subtle)" : "transparent",
            color: mode === "video" ? "var(--accent-text)" : "var(--text-secondary)",
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: "pointer",
            transition: "all var(--transition-fast)",
          }}
        >
          <Film size={15} />
          <span>Video-to-Beat</span>
        </button>
      </div>

      {mode === "video" ? (
        <VideoToBeatView onJobCreated={onJobCreated} isGenerating={isGenerating} />
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Prompt Input Area */}
        <div className="form-group">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" }}>
            <label htmlFor="prompt-input" className="form-label" style={{ margin: 0 }}>
              Music Description & Mood
            </label>
            <span style={{ fontSize: "0.75rem", color: prompt.length > 300 ? "var(--warning)" : "var(--text-muted)" }}>
              {prompt.length}/400
            </span>
          </div>

          <textarea
            id="prompt-input"
            aria-label="Music Description & Mood"
            value={prompt}
            maxLength={400}
            onChange={(e) => {
              setPrompt(e.target.value);
              if (error) setError(null);
            }}
            placeholder="Describe the mood, instruments, rhythm, and progression for your video cue..."
            className="form-control"
            style={{ minHeight: "88px" }}
            disabled={busy}
          />

          {/* Quick suggestions */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
            <span style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginRight: "2px" }}>Ideas:</span>
            {examplePrompts.map((ex) => (
              <button
                type="button"
                key={ex.label}
                onClick={() => setPrompt(ex.text)}
                disabled={busy}
                className="chip"
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>

        {/* Essential Controls: Duration */}
        <div className="form-group">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
            <label htmlFor="duration-slider" className="form-label" style={{ margin: 0 }}>
              Target duration in seconds
            </label>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{ display: "flex", gap: "4px" }}>
                {quickDurations.map((d) => (
                  <button
                    type="button"
                    key={d}
                    onClick={() => setDuration(d)}
                    disabled={busy}
                    className={`chip ${duration === d ? "chip-active" : ""}`}
                    style={{ padding: "2px 8px", fontSize: "0.74rem" }}
                  >
                    {d}s
                  </button>
                ))}
              </div>
              <span className="font-mono" style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--accent-text)", minWidth: "40px", textAlign: "right" }}>
                {duration}s
              </span>
            </div>
          </div>

          <input
            id="duration-slider"
            aria-label="Target duration in seconds"
            type="range"
            min={5}
            max={300}
            step={1}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            disabled={busy}
          />
        </div>

        {/* Advanced Settings Toggle */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="btn btn-ghost btn-sm"
            style={{ padding: "4px 8px", color: "var(--text-secondary)", fontSize: "0.78rem" }}
          >
            {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            <span>{showAdvanced ? "Hide Advanced Settings" : "Show Advanced Settings (Tempo, Key, Sections, Narration)"}</span>
          </button>
        </div>

        {/* Expandable Advanced Controls */}
        {showAdvanced && (
          <div
            className="panel-subtle"
            style={{
              padding: "16px 20px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {/* Row 1: Tempo & Key */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="form-group">
                <label htmlFor="tempo-input" className="form-label">
                  Tempo (BPM)
                </label>
                <input
                  id="tempo-input"
                  aria-label="Tempo"
                  type="number"
                  min={40}
                  max={240}
                  placeholder="Auto"
                  value={tempo}
                  onChange={(e) => setTempo(e.target.value ? Number(e.target.value) : "")}
                  className="form-control"
                  disabled={busy}
                />
              </div>

              <div className="form-group">
                <label htmlFor="key-select" className="form-label">
                  Musical Key
                </label>
                <select
                  id="key-select"
                  aria-label="Musical Key"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  className="form-control"
                  disabled={busy}
                >
                  <option value="">Auto (Best fit)</option>
                  {keysList.filter(Boolean).map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Row 2: Loopable & Narration URL */}
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "16px", alignItems: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.84rem", color: "var(--text-secondary)", cursor: "pointer", userSelect: "none" }}>
                <input
                  type="checkbox"
                  checked={loopable}
                  onChange={(e) => setLoopable(e.target.checked)}
                  disabled={busy}
                  style={{ accentColor: "var(--accent-primary)", width: "16px", height: "16px" }}
                />
                Seamless Loop
              </label>

              <div className="form-group" style={{ margin: 0 }}>
                <input
                  type="url"
                  placeholder="Optional Narration Audio URL (for voiceover ducking)..."
                  value={narrationUrl}
                  onChange={(e) => setNarrationUrl(e.target.value)}
                  className="form-control"
                  style={{ fontSize: "0.82rem", padding: "8px 12px" }}
                  disabled={busy}
                />
              </div>
            </div>

            {/* Row 3: Section Plan Cut Points */}
            <div className="form-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <span className="form-label" style={{ margin: 0 }}>
                  Video Cut Points / Sections ({sections.length})
                </span>
                <button
                  type="button"
                  onClick={handleAddSection}
                  disabled={busy}
                  className="btn btn-secondary btn-sm"
                  style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                >
                  <Plus size={13} />
                  <span>Add Cut Point</span>
                </button>
              </div>

              {sections.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {sections.map((sec, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        background: "var(--bg-canvas)",
                        padding: "6px 10px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <span className="font-mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", minWidth: "22px" }}>
                        #{idx + 1}
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>@</span>
                        <input
                          type="number"
                          step={0.5}
                          min={0}
                          max={duration}
                          value={sec.start_s}
                          onChange={(e) => handleUpdateSection(idx, "start_s", Number(e.target.value))}
                          className="form-control"
                          style={{ width: "65px", padding: "4px 8px", fontSize: "0.8rem" }}
                          disabled={busy}
                        />
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>s</span>
                      </div>
                      <input
                        type="text"
                        placeholder="Section mood (e.g. calm intro, energetic build-up)"
                        value={sec.mood}
                        onChange={(e) => handleUpdateSection(idx, "mood", e.target.value)}
                        className="form-control"
                        style={{ flex: 1, padding: "4px 8px", fontSize: "0.8rem" }}
                        disabled={busy}
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveSection(idx)}
                        aria-label="Remove section"
                        disabled={busy}
                        style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", padding: "4px" }}
                        title="Remove section"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Inline Error Notice */}
        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
              padding: "10px 14px",
              background: "var(--danger-subtle)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              borderRadius: "var(--radius-md)",
              color: "var(--danger)",
              fontSize: "0.82rem",
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
            <span>{error}</span>
          </div>
        )}

        {/* Primary Action Button */}
        <div>
          <button
            type="submit"
            disabled={busy}
            className="btn btn-primary btn-lg"
            style={{ width: "100%" }}
          >
            {busy ? (
              <>
                <div
                  style={{
                    width: "16px",
                    height: "16px",
                    border: "2px solid rgba(255, 255, 255, 0.3)",
                    borderTopColor: "#fff",
                    borderRadius: "50%",
                  }}
                  className="animate-spin"
                />
                <span>Generating Instrumental Music...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Generate Music Track</span>
              </>
            )}
          </button>
        </div>
      </form>
      )}
    </div>
  );
};
