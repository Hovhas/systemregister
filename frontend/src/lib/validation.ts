const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const URL_RE = /^https?:\/\/[^\s]+$/
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const ORG_NUMBER_RE = /^\d{6}-\d{4}$/  // Swedish org number: 556123-4567

export function isEmail(v: string): boolean { return EMAIL_RE.test(v) }
export function isUrl(v: string): boolean { return URL_RE.test(v) }
export function isUuid(v: string): boolean { return UUID_RE.test(v) }
export function isOrgNumber(v: string): boolean { return ORG_NUMBER_RE.test(v) }

export function validateRequired(v: string | null | undefined, label: string): string | undefined {
  if (!v || !v.trim()) return `${label} är obligatoriskt`
  return undefined
}

export function validateEmail(v: string | null | undefined): string | undefined {
  if (!v) return undefined
  if (!isEmail(v)) return "Ogiltig e-postadress"
  return undefined
}

export function validateUrl(v: string | null | undefined): string | undefined {
  if (!v) return undefined
  if (!isUrl(v)) return "Ogiltig URL (måste börja med http:// eller https://)"
  return undefined
}
