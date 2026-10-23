/**
 * TypeScript API contracts matching OpenAPI 3.1 schema.
 */

export interface SectionPlan {
  start_s: number;
  mood: string;
}

export interface OutputConfig {
  sample_rate: number;
  target_lufs: number;
  formats: string[];
}

export interface MusicJobRequest {
  prompt: string;
  duration_s: number;
  sections?: SectionPlan[] | null;
  tempo_bpm?: number | null;
  key?: string | null;
  loopable?: boolean;
  narration_url?: string | null;
  callback_url?: string | null;
  seed?: number | null;
  output?: OutputConfig;
}

export interface JobAcceptedResponse {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  created_at: string;
  message: string;
}

export interface JobResultURLs {
  mix_wav: string;
  mix_mp3?: string | null;
  mix_ducked_wav?: string | null;
  stems: Record<string, string>;
  manifest: string;
  validation_report?: string | null;
}

export interface ErrorDetail {
  code: string;
  message: string;
  retryable?: boolean;
  details?: Record<string, any>;
}

export interface StandardErrorResponse {
  error: ErrorDetail;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  result?: JobResultURLs | null;
  manifest?: Record<string, any> | null;
  error?: ErrorDetail | null;
  created_at: string;
  updated_at: string;
}

export interface HealthCheckResponse {
  status: string;
  service?: string;
  version?: string;
}

export interface ReadyCheckResponse {
  status: string;
  checks: Record<string, string>;
}
