import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobHistoryView } from '../views/JobHistoryView';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    listJobs: vi.fn(),
  },
}));

describe('JobHistoryView', () => {
  const mockJobs = [
    {
      job_id: 'job-alpha-123',
      status: 'succeeded',
      progress: 100,
      created_at: '2026-10-23T10:00:00Z',
      manifest: {
        prompt: 'Futuristic synthwave soundtrack',
        duration_s: 45,
        output_metrics: { duration_s: 45.0 },
      },
    },
    {
      job_id: 'job-beta-456',
      status: 'failed',
      progress: 50,
      error: 'Separation pipeline timeout',
      created_at: '2026-10-23T09:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders history table with search and filtering', async () => {
    (apiClient.listJobs as any).mockResolvedValueOnce(mockJobs);

    const onNavigate = vi.fn();
    render(<JobHistoryView onNavigate={onNavigate} />);

    await waitFor(() => {
      expect(screen.getByText('Futuristic synthwave soundtrack')).toBeInTheDocument();
      expect(screen.getByText('job-beta-456')).toBeInTheDocument();
    });

    // Test search filter
    const searchInput = screen.getByPlaceholderText(/Search by prompt or Job ID/i);
    fireEvent.change(searchInput, { target: { value: 'synthwave' } });

    expect(screen.getByText('Futuristic synthwave soundtrack')).toBeInTheDocument();
    expect(screen.queryByText('job-beta-456')).not.toBeInTheDocument();
  });
});
