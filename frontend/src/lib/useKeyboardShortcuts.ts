import { useEffect } from "react"
import { useNavigate } from "react-router-dom"

/**
 * Global keyboard shortcuts (H7 — Flexibilitet och effektivitet).
 *
 * Ctrl+K / Cmd+K  — Fokusera sökfält (om det finns)
 * Ctrl+N / Cmd+N  — Nytt system
 * Ctrl+H / Cmd+H  — Gå till dashboard
 * Escape           — Stäng dialog / gå tillbaka
 */
export function useKeyboardShortcuts() {
  const navigate = useNavigate()

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey
      const target = e.target as HTMLElement
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable

      if (meta && e.key === "k") {
        e.preventDefault()
        const searchInput = document.querySelector<HTMLInputElement>(
          '[data-shortcut="search"]'
        )
        searchInput?.focus()
      }

      if (meta && e.key === "n" && !isInput) {
        e.preventDefault()
        navigate("/systems/new")
      }

      if (meta && e.key === "h" && !isInput) {
        e.preventDefault()
        navigate("/dashboard")
      }
    }

    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [navigate])
}
