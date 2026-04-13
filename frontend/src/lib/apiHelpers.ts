import axios from "axios"

/**
 * Parse axios error till ett användarvänligt svenskt meddelande.
 * Hanterar Pydantic validation detail-arrayer + vanliga fel.
 */
export function parseApiError(err: unknown, fallback = "Ett oväntat fel uppstod"): string {
  if (!axios.isAxiosError(err)) return fallback

  const status = err.response?.status
  const detail = err.response?.data?.detail

  // Pydantic validation errors — array av {loc, msg, type}
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (typeof first === "object" && "msg" in first) {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : ""
      return field ? `${field}: ${first.msg}` : String(first.msg)
    }
  }

  if (typeof detail === "string") return detail

  // HTTP status-baserade fallbacks
  switch (status) {
    case 400: return "Ogiltig förfrågan"
    case 401: return "Autentisering krävs"
    case 403: return "Du saknar behörighet"
    case 404: return "Resursen hittades inte"
    case 409: return "Konflikt \u2014 resursen är redan i det tillståndet"
    case 422: return "Valideringsfel i indata"
    case 429: return "För många förfrågningar \u2014 vänta en stund"
    case 500: return "Internt serverfel \u2014 försök igen senare"
    case 502:
    case 503:
    case 504:
      return "Tjänsten är tillfälligt otillgänglig"
    default: return fallback
  }
}
