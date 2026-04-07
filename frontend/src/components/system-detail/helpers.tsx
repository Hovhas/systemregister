import type React from "react"

export function InfoRow({
  label,
  value,
}: {
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5 py-2 border-b last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value ?? "—"}</span>
    </div>
  )
}

export function CiaBar({ label, title, value }: { label: string; title?: string; value: number }) {
  const pct = (value / 4) * 100
  const color =
    value >= 3
      ? "bg-red-500"
      : value === 2
      ? "bg-yellow-500"
      : "bg-green-500"

  return (
    <div className="flex items-center gap-3">
      <span className="w-4 shrink-0 text-xs font-semibold text-muted-foreground" title={title}>
        {label}
      </span>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-4 text-right text-xs tabular-nums">{value}</span>
    </div>
  )
}
