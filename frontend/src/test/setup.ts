import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Lightweight Canvas 2D context mock for headless JSDOM test environments
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = function (contextType: string) {
    if (contextType === '2d') {
      return {
        clearRect: vi.fn(),
        fillRect: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        roundRect: vi.fn(),
        rect: vi.fn(),
        stroke: vi.fn(),
        fill: vi.fn(),
        arc: vi.fn(),
        createLinearGradient: vi.fn(() => ({
          addColorStop: vi.fn(),
        })),
        measureText: vi.fn(() => ({ width: 0 })),
      } as unknown as CanvasRenderingContext2D;

    }
    return null;
  } as any;
}
