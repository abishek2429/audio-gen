import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MusicGeneratorView } from '../views/MusicGeneratorView';

describe('MusicGeneratorView', () => {
  it('renders form inputs correctly', () => {
    const onJobCreated = vi.fn();
    render(<MusicGeneratorView onJobCreated={onJobCreated} />);

    expect(screen.getByLabelText(/Music Description & Mood/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Target duration in seconds/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tempo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Musical Key/i)).toBeInTheDocument();
  });

  it('displays validation error if prompt is empty on submit', async () => {
    const onJobCreated = vi.fn();
    render(<MusicGeneratorView onJobCreated={onJobCreated} />);

    const submitBtn = screen.getByRole('button', { name: /Generate Music Track/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Please describe the music you want to generate/i)).toBeInTheDocument();
    expect(onJobCreated).not.toHaveBeenCalled();
  });

  it('allows adding and removing cut point sections', () => {
    const onJobCreated = vi.fn();
    render(<MusicGeneratorView onJobCreated={onJobCreated} />);

    const addSectionBtn = screen.getByRole('button', { name: /Add Cut Point/i });
    fireEvent.click(addSectionBtn);

    expect(screen.getByPlaceholderText(/Section mood/i)).toBeInTheDocument();

    const removeBtn = screen.getByLabelText(/Remove section/i);
    fireEvent.click(removeBtn);

    expect(screen.queryByPlaceholderText(/Section mood/i)).not.toBeInTheDocument();
  });
});
