import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobProgressView } from '../views/JobProgressView';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getJob: vi.fn(),
  },
}));

describe('JobProgressView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('polls job status and displays progress percentage', async () => {
    (apiClient.getJob as any).mockResolvedValueOnce({
      job_id: 'test-job-progress',
      status: 'running',
      progress: 60,
      created_at: '2026-10-23T10:00:00Z',
    });

    const onComplete = vi.fn();
    const onRetry = vi.fn();

    render(
      <JobProgressView
        jobId="test-job-progress"
        onComplete={onComplete}
        onRetry={onRetry}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('60%')).toBeInTheDocument();
      expect(screen.getByText(/Multitrack stem separation/i)).toBeInTheDocument();
    });
  });

  it('displays error details when job status is failed', async () => {
    (apiClient.getJob as any).mockResolvedValueOnce({
      job_id: 'test-job-fail',
      status: 'failed',
      progress: 40,
      error: { code: 'PROVIDER_ERROR', message: 'Audio provider API rate limited' },
      created_at: '2026-10-23T10:00:00Z',
    });

    const onComplete = vi.fn();
    const onRetry = vi.fn();

    render(
      <JobProgressView
        jobId="test-job-fail"
        onComplete={onComplete}
        onRetry={onRetry}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Processing Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Audio provider API rate limited/i)).toBeInTheDocument();
      expect(screen.getByText(/PROVIDER_ERROR/i)).toBeInTheDocument();
    });
  });
});
