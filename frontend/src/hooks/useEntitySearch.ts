import { useState, useEffect, useRef } from "react"

export function useEntitySearch(delayMs = 300) {
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setDebouncedSearch(searchInput), delayMs)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [searchInput, delayMs])

  const isSearching = searchInput !== debouncedSearch

  return {
    searchInput,
    debouncedSearch,
    isSearching,
    setSearchInput,
    clearSearch: () => { setSearchInput(""); setDebouncedSearch("") },
  }
}
