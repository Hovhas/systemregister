/**
 * Testsvit: useUndoStack hook
 */

import { describe, it, expect, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useUndoStack } from "@/lib/useUndoStack"

// Mock toast
vi.mock("sonner", () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() },
}))

describe("useUndoStack", () => {
  it("startvärde sätts korrekt", () => {
    const { result } = renderHook(() => useUndoStack("initial"))
    expect(result.current.value).toBe("initial")
  })

  it("setValue uppdaterar värdet", () => {
    const { result } = renderHook(() => useUndoStack("A"))
    act(() => result.current.setValue("B"))
    expect(result.current.value).toBe("B")
  })

  it("undo återställer till föregående värde", () => {
    const { result } = renderHook(() => useUndoStack("A"))
    act(() => result.current.setValue("B"))
    act(() => result.current.setValue("C"))
    act(() => result.current.undo())
    expect(result.current.value).toBe("B")
  })

  it("canUndo är false initialt och true efter setValue", () => {
    const { result } = renderHook(() => useUndoStack("A"))
    // canUndo is a getter on the ref, so we read it within the same render
    expect(result.current.canUndo).toBe(false)
    act(() => result.current.setValue("B"))
    expect(result.current.canUndo).toBe(true)
  })

  it("behåller max 20 historik-poster", () => {
    const { result } = renderHook(() => useUndoStack(0))
    // Pusha 25 värden
    for (let i = 1; i <= 25; i++) {
      act(() => result.current.setValue(i))
    }
    expect(result.current.value).toBe(25)
    // Undo 20 gånger borde fungera
    for (let i = 0; i < 20; i++) {
      act(() => result.current.undo())
    }
    // Ytterligare undo bör inte ändra värdet (historia tom)
    const valAfter20 = result.current.value
    act(() => result.current.undo())
    expect(result.current.value).toBe(valAfter20)
  })
})
