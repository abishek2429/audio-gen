import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, resolveAudioUrl, ApiError } from '../services/apiClient';

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('resolves relative and absolute audio URLs properly', () => {
    expect(resolveAudioUrl('http://storage.com/mix.wav')).toBe('http://storage.com/mix.wav');
    expect(resolveAudioUrl('https://storage.com/mix.wav')).toBe('https://storage.com/mix.wav');
    expect(resolveAudioUrl('/api/v1/storage/job_123/mix.wav')).toContain('/api/v1/storage/job_123/mix.wav');
    expect(resolveAudioUrl('')).toBe('');
  });

  it('createJob sends proper POST payload and returns job ID', async () => {
    const mockResponse = {
      job_id: 'job_test_123',
      status: 'queued',
      progress: 0,
      created_at: '2026-10-23T12:00:00Z',
      message: 'Job accepted',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as any);

    const res = await apiClient.createJob(
      { prompt: 'test mood', duration_s: 15.0 },
      'idemp-key-test'
    );

    expect(res.job_id).toBe('job_test_123');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/music/jobs'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'Idempotency-Key': 'idemp-key-test',
        }),
      })
    );
  });

  it('throws ApiError with code when HTTP error occurs', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({
        error: {
          code: 'IDEMPOTENCY_CONFLICT',
          message: 'Key reused with different request payload',
        },
      }),
    } as any);

    await expect(
      apiClient.createJob({ prompt: 'test', duration_s: 10 })
    ).rejects.toThrow(ApiError);
  });
});
