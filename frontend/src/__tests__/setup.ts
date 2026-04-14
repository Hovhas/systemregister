/**
 * Testsetup: vitest + @testing-library/react + MSW (mock service worker)
 *
 * Installerade paket som krävs (läggs till package.json separat):
 *   vitest @vitest/coverage-v8 jsdom
 *   @testing-library/react @testing-library/jest-dom @testing-library/user-event
 *   msw
 */

import "@testing-library/jest-dom"
import { cleanup } from "@testing-library/react"
import { afterEach, vi } from "vitest"
import { setupServer } from "msw/node"

// Starta MSW-server om den är definierad globalt
// Varje testfil skapar sin egen server via createTestServer()
afterEach(() => {
  cleanup()
})

// Polyfill för ResizeObserver (används av Radix UI-komponenter)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Polyfill för window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Polyfill för window.open (används av ReportsPage)
Object.defineProperty(window, "open", {
  writable: true,
  value: vi.fn(),
})

// Polyfill för scrollIntoView (används av Select-komponenter)
Element.prototype.scrollIntoView = vi.fn()

// Polyfill för hasPointerCapture (används av Radix Slider)
Element.prototype.hasPointerCapture = vi.fn()

// Exportera hjälpfunktion för att skapa MSW-server per testfil
export { setupServer }
export { http, HttpResponse } from "msw"
export type { RequestHandler } from "msw"
