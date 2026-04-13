/**
 * Testsvit: useEntitySearch hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useEntitySearch } from "@/hooks/useEntitySearch"

describe("useEntitySearch", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("initial tom sökning", () => {
    const { result } = renderHook(() => useEntitySearch())
    expect(result.current.searchInput).toBe("")
    expect(result.current.debouncedSearch).toBe("")
  })

  it("setSearchInput uppdaterar direkt", () => {
    const { result } = renderHook(() => useEntitySearch())
    act(() => result.current.setSearchInput("test"))
    expect(result.current.searchInput).toBe("test")
  })

  it("debouncedSearch uppdateras efter fördröjning", () => {
    const { result } = renderHook(() => useEntitySearch(300))
    act(() => result.current.setSearchInput("hello"))
    // Innan timeout
    expect(result.current.debouncedSearch).toBe("")
    // Avancera timer
    act(() => vi.advanceTimersByTime(300))
    expect(result.current.debouncedSearch).toBe("hello")
  })

  it("isSearching reflekterar väntande debounce", () => {
    const { result } = renderHook(() => useEntitySearch(300))
    act(() => result.current.setSearchInput("q"))
    expect(result.current.isSearching).toBe(true)
    act(() => vi.advanceTimersByTime(300))
    expect(result.current.isSearching).toBe(false)
  })

  it("clearSearch nollställer båda", () => {
    const { result } = renderHook(() => useEntitySearch(300))
    act(() => result.current.setSearchInput("test"))
    act(() => vi.advanceTimersByTime(300))
    expect(result.current.debouncedSearch).toBe("test")
    act(() => result.current.clearSearch())
    expect(result.current.searchInput).toBe("")
    expect(result.current.debouncedSearch).toBe("")
  })
})
