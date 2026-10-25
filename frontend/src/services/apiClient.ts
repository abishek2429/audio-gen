/**
 * Reusable API Client for IncuBrix AI Background Music Engine.
 */
import type {
  MusicJobRequest,
  JobAcceptedResponse,
  JobStatusResponse,
  HealthCheckResponse,
  ReadyCheckResponse,
  ErrorDetail,
  VideoAnalysisResponse,
  VideoJobAcceptedResponse,
  ProviderTestResponse,
  ProviderComparisonResponse,
} from "../types/api";


const DEFAULT_API_URL = import.meta.env.DEV
  ? "http://localhost:8000"
  : "https://audio-gen-two.vercel.app";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_URL).replace(/\/+$/, "");

export class ApiError extends Error {
  code: string;
  statusCode: number;
  retryable: boolean;
  details: Record<string, any>;

  constructor(statusCode: number, errorDetail: ErrorDetail) {
    super(errorDetail.message || "An API error occurred");
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.code = errorDetail.code || "UNKNOWN_ERROR";
    this.retryable = errorDetail.retryable ?? false;
    this.details = errorDetail.details || {};
  }
}

export function resolveAudioUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("blob:")) {
    return url;
  }
  return `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail: ErrorDetail = {
      code: `HTTP_${res.status}`,
      message: res.statusText || "Request failed",
      retryable: res.status >= 500,
    };
    try {
      const data = await res.json();
      if (data && data.error) {
        errorDetail = data.error;
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(res.status, errorDetail);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async getHealth(): Promise<HealthCheckResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthCheckResponse>(res);
  },

  async getReady(): Promise<ReadyCheckResponse> {
    const res = await fetch(`${API_BASE_URL}/ready`);
    return handleResponse<ReadyCheckResponse>(res);
  },

  async createJob(
    request: MusicJobRequest,
    idempotencyKey?: string
  ): Promise<JobAcceptedResponse> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/music/jobs`, {
      method: "POST",
      headers,
      body: jsonStringifyCanonical(request),
    });
    return handleResponse<JobAcceptedResponse>(res);
  },

  async getJob(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(jobId)}`);
    return handleResponse<JobStatusResponse>(res);
  },

  async listJobs(limit = 50, offset = 0): Promise<JobStatusResponse[]> {
    const res = await fetch(`${API_BASE_URL}/api/v1/jobs?limit=${limit}&offset=${offset}`);
    return handleResponse<JobStatusResponse[]>(res);
  },

  async analyzeVideo(
    file: File,
    style?: string,
    promptOverride?: string
  ): Promise<VideoAnalysisResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (style) formData.append("style", style);
    if (promptOverride) formData.append("prompt_override", promptOverride);

    const res = await fetch(`${API_BASE_URL}/api/v1/video/analyze`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<VideoAnalysisResponse>(res);
  },

  async createVideoJob(
    file: File,
    style?: string,
    promptOverride?: string,
    idempotencyKey?: string
  ): Promise<VideoJobAcceptedResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (style) formData.append("style", style);
    if (promptOverride) formData.append("prompt_override", promptOverride);

    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/video/jobs`, {
      method: "POST",
      headers,
      body: formData,
    });
    return handleResponse<VideoJobAcceptedResponse>(res);
  },

  async testProviderConnection(
    provider?: string,
    performSampleGeneration = false,
    prompt?: string,
    durationS = 5.0
  ): Promise<ProviderTestResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/providers/test-connection`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider,
        perform_sample_generation: performSampleGeneration,
        prompt,
        duration_s: durationS,
      }),
    });
    return handleResponse<ProviderTestResponse>(res);
  },

  async getProviderComparison(): Promise<ProviderComparisonResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/providers/comparison`);
    return handleResponse<ProviderComparisonResponse>(res);
  },
};

function jsonStringifyCanonical(obj: any): string {
  return JSON.stringify(obj);
}

