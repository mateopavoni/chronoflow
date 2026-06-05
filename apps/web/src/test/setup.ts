import '@testing-library/jest-dom'

// Mock ResizeObserver — not available in jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock crypto.randomUUID
Object.defineProperty(globalThis, 'crypto', {
  value: {
    randomUUID: () => `${Math.random().toString(36).slice(2)}-${Date.now()}`,
  },
})
