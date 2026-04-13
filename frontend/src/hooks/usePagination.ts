import { useState, useMemo } from "react"

export function usePagination(pageSize = 50) {
  const [offset, setOffset] = useState(0)

  const helpers = useMemo(() => ({
    pageSize,
    currentPage: Math.floor(offset / pageSize) + 1,
    next: () => setOffset((o) => o + pageSize),
    prev: () => setOffset((o) => Math.max(0, o - pageSize)),
    reset: () => setOffset(0),
    setPage: (p: number) => setOffset((p - 1) * pageSize),
  }), [offset, pageSize])

  function totalPages(total: number) {
    return Math.max(1, Math.ceil(total / pageSize))
  }

  return { offset, setOffset, ...helpers, totalPages }
}
