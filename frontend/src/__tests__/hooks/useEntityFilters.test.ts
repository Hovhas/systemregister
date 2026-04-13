/**
 * Testsvit: useEntityFilters hook
 */

import { describe, it, expect } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useEntityFilters } from "@/hooks/useEntityFilters"

const initial = {
  organization: "" as string,
  category: "" as string,
  active: undefined as boolean | undefined,
}

describe("useEntityFilters", () => {
  it("initiala filter matchar input", () => {
    const { result } = renderHook(() => useEntityFilters(initial))
    expect(result.current.filters).toEqual(initial)
  })

  it("setFilter uppdaterar ett fält", () => {
    const { result } = renderHook(() => useEntityFilters(initial))
    act(() => result.current.setFilter("organization", "org-1"))
    expect(result.current.filters.organization).toBe("org-1")
    expect(result.current.filters.category).toBe("")
  })

  it("hasFilters är true när ett filter ändrats", () => {
    const { result } = renderHook(() => useEntityFilters(initial))
    expect(result.current.hasFilters).toBe(false)
    act(() => result.current.setFilter("category", "infrastruktur"))
    expect(result.current.hasFilters).toBe(true)
  })

  it("clearFilters nollställer alla filter", () => {
    const { result } = renderHook(() => useEntityFilters(initial))
    act(() => result.current.setFilter("organization", "org-1"))
    act(() => result.current.setFilter("category", "plattform"))
    expect(result.current.hasFilters).toBe(true)
    act(() => result.current.clearFilters())
    expect(result.current.filters).toEqual(initial)
    expect(result.current.hasFilters).toBe(false)
  })

  it("hasFilters ignorerar tomma strängar", () => {
    const { result } = renderHook(() => useEntityFilters(initial))
    act(() => result.current.setFilter("organization", ""))
    expect(result.current.hasFilters).toBe(false)
  })
})
