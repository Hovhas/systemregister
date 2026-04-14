import { useState, useCallback, useRef } from "react"
import { toast } from "sonner"

/**
 * Undo-stack for formulaeraendringar (H3 -- Anvandarkontroll och frihet).
 *
 * Usage:
 *   const { value, setValue, undo, canUndo } = useUndoStack(initialValue)
 */
export function useUndoStack<T>(initial: T) {
  const [value, setValueInternal] = useState<T>(initial)
  const [canUndo, setCanUndo] = useState(false)
  const history = useRef<T[]>([])

  const setValue = useCallback((next: T | ((prev: T) => T)) => {
    setValueInternal((prev) => {
      history.current.push(prev)
      // Keep max 20 entries
      if (history.current.length > 20) {
        history.current.shift()
      }
      setCanUndo(true)
      return typeof next === "function" ? (next as (prev: T) => T)(prev) : next
    })
  }, [])

  const undo = useCallback(() => {
    if (history.current.length === 0) return
    const prev = history.current.pop()!
    setValueInternal(prev)
    setCanUndo(history.current.length > 0)
    toast.info("Ångrade senaste ändringen")
  }, [])

  return { value, setValue, undo, canUndo }
}
