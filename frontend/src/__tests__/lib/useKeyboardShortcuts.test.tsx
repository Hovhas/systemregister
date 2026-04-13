/**
 * Testsvit: useKeyboardShortcuts hook
 */

import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import type { ReactNode } from "react"
import { useKeyboardShortcuts } from "@/lib/useKeyboardShortcuts"

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function wrapper({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

describe("useKeyboardShortcuts", () => {
  afterEach(() => {
    mockNavigate.mockClear()
  })

  it("Ctrl+K fokuserar sökfältet", () => {
    const mockFocus = vi.fn()
    const mockInput = document.createElement("input")
    mockInput.setAttribute("data-shortcut", "search")
    mockInput.focus = mockFocus
    document.body.appendChild(mockInput)

    renderHook(() => useKeyboardShortcuts(), { wrapper })

    window.dispatchEvent(
      new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }),
    )
    expect(mockFocus).toHaveBeenCalled()

    document.body.removeChild(mockInput)
  })

  it("Ctrl+N navigerar till /systems/new", () => {
    renderHook(() => useKeyboardShortcuts(), { wrapper })

    window.dispatchEvent(
      new KeyboardEvent("keydown", { key: "n", ctrlKey: true, bubbles: true }),
    )
    expect(mockNavigate).toHaveBeenCalledWith("/systems/new")
  })

  it("Ctrl+H navigerar till /dashboard", () => {
    renderHook(() => useKeyboardShortcuts(), { wrapper })

    window.dispatchEvent(
      new KeyboardEvent("keydown", { key: "h", ctrlKey: true, bubbles: true }),
    )
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard")
  })

  it("Ctrl+N i input-fält triggar inte navigation", () => {
    renderHook(() => useKeyboardShortcuts(), { wrapper })

    const input = document.createElement("input")
    document.body.appendChild(input)
    input.focus()

    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "n", ctrlKey: true, bubbles: true }),
    )
    expect(mockNavigate).not.toHaveBeenCalledWith("/systems/new")

    document.body.removeChild(input)
  })
})
