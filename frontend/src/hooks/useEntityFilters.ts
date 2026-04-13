import { useState, useMemo, useCallback } from "react"

export function useEntityFilters<T extends Record<string, string | boolean | undefined>>(initial: T) {
  const [filters, setFilters] = useState<T>(initial)

  const hasFilters = useMemo(
    () => Object.entries(filters).some(([k, v]) => v !== initial[k] && v !== "" && v !== undefined),
    [filters, initial]
  )

  const setFilter = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  const clearFilters = useCallback(() => setFilters(initial), [initial])

  return { filters, setFilter, setFilters, clearFilters, hasFilters }
}
