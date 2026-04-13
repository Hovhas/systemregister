import { useEffect } from "react"

export function useAutoSave<T>(key: string, value: T, delayMs = 1000) {
  useEffect(() => {
    const t = setTimeout(() => {
      try { localStorage.setItem(key, JSON.stringify(value)) } catch {}
    }, delayMs)
    return () => clearTimeout(t)
  }, [key, value, delayMs])
}

export function loadAutoSaved<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function clearAutoSaved(key: string) {
  try { localStorage.removeItem(key) } catch {}
}
