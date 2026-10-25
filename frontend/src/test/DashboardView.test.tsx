import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardView } from '../views/DashboardView';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    listJobs: vi.fn(),
  },
}));

describe('DashboardView', () => {
  const mockJobs = [
    {
      job_id: 'job-succ-1',
      status: 'succeeded',
      progress: 100,
      created_at: '2026-10-23T10:00:00Z',
      manifest: {
        prompt: 'Inspiring piano cinematic soundtrack',
        duration_s: 30,
        output_metrics: { duration_s: 30.0 },
      },
    },
    {
      job_id: 'job-fail-2',
      status: 'failed',
      progress: 25,
      error: 'Network timeout',
      created_at: '2026-10-23T09:30:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard metrics and recent jobs from backend API', async () => {
    (apiClient.listJobs as any).mockResolvedValueOnce(mockJobs);

    const onNavigate = vi.fn();
    render(<DashboardView onNavigate={onNavigate} />);

    // Total jobs count = 2
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    expect(screen.getByText(/Inspiring piano cinematic soundtrack/i)).toBeInTheDocument();
    expect(screen.getByText(/job-succ-1/i)).toBeInTheDocument();
  });

  it('renders quick generation presets', async () => {
    (apiClient.listJobs as any).mockResolvedValueOnce([]);

    const onNavigate = vi.fn();
    render(<DashboardView onNavigate={onNavigate} />);

    await waitFor(() => {
      expect(apiClient.listJobs).toHaveBeenCalled();
    });

    expect(screen.getByText('Cinematic Trailer')).toBeInTheDocument();
    expect(screen.getByText('Tech Corporate')).toBeInTheDocument();
    expect(screen.getByText('Chill Lo-Fi')).toBeInTheDocument();
  });
});

