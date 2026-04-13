import { useEffect, useState } from "react"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"

interface Shortcut {
  keys: string
  description: string
}

const shortcuts: Shortcut[] = [
  { keys: "Ctrl+K / \u2318K", description: "Fokusera sökfält" },
  { keys: "Ctrl+N / \u2318N", description: "Nytt system" },
  { keys: "Ctrl+H / \u2318H", description: "Gå till dashboard" },
  { keys: "?", description: "Visa denna hjälp" },
  { keys: "Esc", description: "Stäng dialog" },
]

export function KeyboardHelpModal() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable
      if (!isInput && e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tangentbordsgenvägar</DialogTitle>
        </DialogHeader>
        <div className="space-y-1 text-sm">
          {shortcuts.map((s) => (
            <div key={s.keys} className="flex justify-between items-center py-1.5 border-b last:border-b-0">
              <span>{s.description}</span>
              <kbd className="inline-flex h-6 items-center gap-1 rounded border bg-muted px-2 text-xs font-mono">
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
