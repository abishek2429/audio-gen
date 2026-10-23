import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AudioWaveform } from '../components/AudioWaveform';

describe('AudioWaveform', () => {
  it('renders track title, subtitle, and badge', () => {
    render(
      <AudioWaveform
        title="Drums Stem"
        subtitle="Transient rhythm track"
        badge="48kHz WAV"
        color="#f97316"
        audioUrl="/api/v1/storage/job_1/stems/drums.wav"
        downloadFilename="drums.wav"
      />
    );

    expect(screen.getByText('Drums Stem')).toBeInTheDocument();
    expect(screen.getByText('Transient rhythm track')).toBeInTheDocument();
    expect(screen.getByText('48kHz WAV')).toBeInTheDocument();
    expect(screen.getByLabelText(/Play/i)).toBeInTheDocument();
  });
});
