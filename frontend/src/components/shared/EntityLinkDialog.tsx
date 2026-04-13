import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { SearchIcon, CheckIcon } from "lucide-react"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface EntityLinkDialogProps<T extends { id: string }> {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  queryKey: unknown[]
  queryFn: () => Promise<T[] | { items: T[] }>
  renderOption: (item: T) => React.ReactNode
  excludeIds?: string[]
  onSelect: (ids: string[]) => Promise<void> | void
  submitLabel?: string
}

export function EntityLinkDialog<T extends { id: string }>({
  open, onOpenChange, title, description,
  queryKey, queryFn, renderOption, excludeIds = [], onSelect,
  submitLabel = "Länka",
}: EntityLinkDialogProps<T>) {
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [submitting, setSubmitting] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn,
    enabled: open,
  })

  const items = useMemo(() => {
    const list = Array.isArray(data) ? data : data?.items ?? []
    return list.filter((item) => !excludeIds.includes(item.id))
  }, [data, excludeIds])

  const filtered = useMemo(() => {
    if (!search.trim()) return items
    const q = search.toLowerCase()
    return items.filter((item) => {
      const txt = String((item as Record<string, unknown>).name ?? "").toLowerCase()
      return txt.includes(q)
    })
  }, [items, search])

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSubmit() {
    if (selected.size === 0) return
    setSubmitting(true)
    try {
      await onSelect(Array.from(selected))
      setSelected(new Set())
      setSearch("")
      onOpenChange(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </DialogHeader>

        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Sök..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            autoFocus
          />
        </div>

        <div className="max-h-64 overflow-auto rounded-md border">
          {isLoading ? (
            <div className="p-4 text-sm text-muted-foreground">Laddar...</div>
          ) : filtered.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground">Inga resultat</div>
          ) : (
            filtered.map((item) => {
              const isSelected = selected.has(item.id)
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => toggle(item.id)}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/50 transition-colors ${
                    isSelected ? "bg-primary/5" : ""
                  }`}
                >
                  <div className={`flex size-4 items-center justify-center rounded border ${
                    isSelected ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground/30"
                  }`}>
                    {isSelected && <CheckIcon className="size-3" />}
                  </div>
                  <span className="flex-1">{renderOption(item)}</span>
                </button>
              )
            })
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Avbryt
          </Button>
          <Button onClick={handleSubmit} disabled={selected.size === 0 || submitting}>
            {submitting ? "Länkar..." : `${submitLabel} (${selected.size})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
