export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "\u2014"
  try {
    return new Date(iso).toLocaleDateString("sv-SE")
  } catch {
    return iso
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "\u2014"
  try {
    return new Date(iso).toLocaleString("sv-SE")
  } catch {
    return iso
  }
}

export function formatRelativeDate(iso: string | null | undefined): string {
  if (!iso) return "\u2014"
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return "Idag"
    if (diffDays === 1) return "Igår"
    if (diffDays < 7) return `${diffDays} dagar sedan`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} veckor sedan`
    return formatDate(iso)
  } catch {
    return iso
  }
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "\u2014"
  return new Intl.NumberFormat("sv-SE", {
    style: "currency",
    currency: "SEK",
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "\u2014"
  return new Intl.NumberFormat("sv-SE").format(value)
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? `1 ${singular}` : `${count} ${plural}`
}
