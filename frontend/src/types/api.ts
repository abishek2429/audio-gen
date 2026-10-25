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

export interface VideoMetadata {
  filename: string;
  duration_s: number;
  fps: number;
  width: number;
  height: number;
  frame_count: number;
  aspect_ratio: string;
  file_size_bytes: number;
}

export interface VideoActivityMetrics {
  avg_motion: number;
  max_motion: number;
  motion_variance: number;
  avg_brightness: number;
  avg_saturation: number;
  warm_color_ratio: number;
  pacing: string;
  detected_mood: string;
}

export interface KeyframeThumbnail {
  timestamp_s: number;
  data_uri: string;
}

export interface MusicalAccent {
  timestamp_s: number;
  event_description: string;
  musical_action: string;
}

export interface MusicPlan {
  genre: string;
  mood: string;
  tempo_bpm: number;
  key: string;
  rhythmic_style: string;
  intensity: string;
  instrumentation: string[];
  target_duration_s: number;
  sections: SectionPlan[];
  accents: MusicalAccent[];
  prompt: string;
}

export interface VideoAnalysisResponse {
  metadata: VideoMetadata;
  scene_cuts: number[];
  activity: VideoActivityMetrics;
  keyframes: KeyframeThumbnail[];
  accent_timestamps: number[];
  audio_present: boolean;
  recommended_plan: MusicPlan;
}

export interface VideoJobAcceptedResponse extends JobAcceptedResponse {
  plan?: MusicPlan;
  video_metadata?: VideoMetadata;
}

export interface ProviderTestSampleResult {
  duration_s: number;
  format: string;
  sample_rate: number;
  cost_usd: number;
  credits_consumed?: number;
  latency_s: number;
  sample_audio_size_bytes: number;
  provider_raw_metadata?: Record<string, any>;
}

export interface ProviderTestResponse {
  provider: string;
  authenticated: boolean;
  status: string;
  credits_balance?: number;
  cost_per_run_usd?: number;
  free_trial_available: boolean;
  free_trial_details: string;
  commercial_use_allowed: boolean;
  license_type: string;
  max_duration_s: number;
  output_formats: string[];
  sample_generation?: ProviderTestSampleResult;
  limitations: string[];
  message: string;
}

export interface ProviderComparisonResponse {
  recommended_provider: string;
  zero_cost_offline_provider: string;
  providers: Record<string, {
    provider_display_name: string;
    official_docs_url: string;
    pricing_model: string;
    cost_per_run_usd: number;
    free_trial_available: boolean;
    free_trial_details: string;
    commercial_use_allowed: boolean;
    license_type: string;
    max_duration_s: number;
    output_formats: string[];
    rate_limits: string;
    limitations: string[];
  }>;
}


