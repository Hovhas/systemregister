import { ChevronUpIcon, ChevronDownIcon } from "lucide-react"
import { TableHead } from "@/components/ui/table"

interface SortHeaderProps {
  field: string
  label: string
  activeField: string
  activeDir: "asc" | "desc"
  onChange: (field: string, dir: "asc" | "desc") => void
}

export function SortHeader({ field, label, activeField, activeDir, onChange }: SortHeaderProps) {
  const active = activeField === field
  const ariaSort = active ? (activeDir === "asc" ? "ascending" : "descending") : "none"

  function toggle() {
    if (active) onChange(field, activeDir === "asc" ? "desc" : "asc")
    else onChange(field, "asc")
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      toggle()
    }
  }

  return (
    <TableHead
      className="cursor-pointer select-none hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded"
      onClick={toggle}
      role="columnheader"
      aria-sort={ariaSort as "ascending" | "descending" | "none"}
      aria-label={`Sortera efter ${label}`}
      tabIndex={0}
      onKeyDown={handleKey}
    >
      <span className="flex items-center gap-1">
        {label}
        {active && (activeDir === "asc" ? <ChevronUpIcon className="size-3" /> : <ChevronDownIcon className="size-3" />)}
      </span>
    </TableHead>
  )
}
