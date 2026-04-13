/**
 * Testsvit: usePagination hook
 */

import { describe, it, expect } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { usePagination } from "@/hooks/usePagination"

describe("usePagination", () => {
  it("initial offset är 0", () => {
    const { result } = renderHook(() => usePagination(25))
    expect(result.current.offset).toBe(0)
  })

  it("initial currentPage är 1", () => {
    const { result } = renderHook(() => usePagination(25))
    expect(result.current.currentPage).toBe(1)
  })

  it("next() ökar offset med pageSize", () => {
    const { result } = renderHook(() => usePagination(25))
    act(() => result.current.next())
    expect(result.current.offset).toBe(25)
    expect(result.current.currentPage).toBe(2)
  })

  it("prev() minskar offset (min 0)", () => {
    const { result } = renderHook(() => usePagination(25))
    act(() => result.current.next())
    act(() => result.current.next())
    expect(result.current.offset).toBe(50)
    act(() => result.current.prev())
    expect(result.current.offset).toBe(25)
    // Prev vid 0 stannar vid 0
    act(() => result.current.prev())
    act(() => result.current.prev())
    expect(result.current.offset).toBe(0)
  })

  it("reset() återställer till 0", () => {
    const { result } = renderHook(() => usePagination(25))
    act(() => result.current.next())
    act(() => result.current.next())
    act(() => result.current.reset())
    expect(result.current.offset).toBe(0)
    expect(result.current.currentPage).toBe(1)
  })

  it("totalPages beräknas korrekt", () => {
    const { result } = renderHook(() => usePagination(25))
    expect(result.current.totalPages(100)).toBe(4)
    expect(result.current.totalPages(101)).toBe(5)
    expect(result.current.totalPages(0)).toBe(1)
    expect(result.current.totalPages(25)).toBe(1)
  })
})
