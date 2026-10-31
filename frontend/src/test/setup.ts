import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock canvas-confetti for headless test runner
vi.mock('canvas-confetti', () => ({
  default: vi.fn(),
}));

// Mock HTMLCanvasElement getContext
HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation(() => ({
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  ellipse: vi.fn(),
  createRadialGradient: vi.fn().mockReturnValue({
    addColorStop: vi.fn(),
  }),
  save: vi.fn(),
  restore: vi.fn(),
  fillText: vi.fn(),
  setLineDash: vi.fn(),
  scale: vi.fn(),
}));

HTMLCanvasElement.prototype.getBoundingClientRect = vi.fn().mockReturnValue({
  width: 500,
  height: 500,
  top: 0,
  left: 0,
  bottom: 500,
  right: 500,
});

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverMock;

// Mock IntersectionObserver for ScrollReveal & Landing components
class IntersectionObserverMock {
  callback: any;
  constructor(callback: any) {
    this.callback = callback;
  }
  observe(target: any) {
    if (this.callback) {
      this.callback([{ isIntersecting: true, target }]);
    }
  }
  unobserve() {}
  disconnect() {}
}
window.IntersectionObserver = IntersectionObserverMock as any;

// Mock matchMedia for dark mode and motion preference
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
