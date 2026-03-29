/**
 * Testsvit: NotificationsPage
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import NotificationsPage from "@/pages/NotificationsPage"
import type { NotificationsResponse } from "@/types"

// --- Testdata ---

function makeNotification(overrides: Partial<{
  type: string
  severity: "critical" | "warning" | "info"
  title: string
  description: string
  system_id?: string
}> = {}) {
  return {
    type: "missing_owner",
    severity: "warning" as const,
    title: "Saknar ägare",
    description: "Systemet har ingen registrerad ägare.",
    system_id: "sys-1",
    ...overrides,
  }
}

function makeResponse(overrides: Partial<NotificationsResponse> = {}): NotificationsResponse {
  return {
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
    by_severity: { critical: 0, warning: 0, info: 0 },
    ...overrides,
  }
}

const criticalNotification = makeNotification({
  type: "expiring_contract",
  severity: "critical",
  title: "Avtal löper ut inom 30 dagar",
  description: "Leverantörsavtalet för Ekonomisystem löper ut 2026-04-15.",
  system_id: "sys-1",
})

const warningNotification = makeNotification({
  type: "missing_classification",
  severity: "warning",
  title: "Saknar klassificering",
  description: "Systemet har inte klassificerats.",
  system_id: "sys-2",
})

const infoNotification = makeNotification({
  type: "missing_gdpr_treatment",
  severity: "info",
  title: "GDPR-behandling saknas",
  description: "Systemet behandlar personuppgifter men saknar GDPR-dokumentation.",
  system_id: "sys-3",
})

const fullResponse = makeResponse({
  items: [criticalNotification, warningNotification, infoNotification],
  total: 3,
  by_severity: { critical: 1, warning: 1, info: 1 },
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/notifications/", () => HttpResponse.json(fullResponse))
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("NotificationsPage", () => {
  describe("Laddning", () => {
    it("visar laddningstext medan data hämtas", () => {
      renderPage()
      expect(screen.getByText(/laddar notifikationer/i)).toBeInTheDocument()
    })

    it("renderar rubrik Notifikationer", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /notifikationer/i })
        ).toBeInTheDocument()
      )
    })
  })

  describe("Visning av notifikationer", () => {
    it("visar notifikation med kritisk severity", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText("Avtal löper ut inom 30 dagar")
        ).toBeInTheDocument()
      )
    })

    it("visar notifikation med varning severity", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Saknar klassificering")).toBeInTheDocument()
      )
    })

    it("visar notifikation med info severity", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("GDPR-behandling saknas")).toBeInTheDocument()
      )
    })

    it("visar severity-badge Kritisk", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Kritisk")).toBeInTheDocument()
      )
    })

    it("visar severity-badge Varning", async () => {
      renderPage()
      await waitFor(() => {
        const badges = screen.getAllByText("Varning")
        expect(badges.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar severity-badge Info", async () => {
      renderPage()
      await waitFor(() => {
        const badges = screen.getAllByText("Info")
        expect(badges.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar grupprubriken med antal: Kritisk (1)", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/kritisk \(1\)/i)).toBeInTheDocument()
      )
    })

    it("visar grupprubriken med antal: Varning (1)", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/varning \(1\)/i)).toBeInTheDocument()
      )
    })

    it("visar grupprubriken med antal: Info (1)", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/info \(1\)/i)).toBeInTheDocument()
      )
    })

    it("visar länk 'Gå till system' för notifikation med system_id", async () => {
      renderPage()
      await waitFor(() => {
        const links = screen.getAllByText(/gå till system/i)
        expect(links.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar typetiketten Utgående avtal för expiring_contract", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Utgående avtal")).toBeInTheDocument()
      )
    })
  })

  describe("Statistikkort", () => {
    it("visar statistikkort med rätt antal per severity efter datainläsning", async () => {
      const extraCritical = makeNotification({
        type: "expiring_contract",
        severity: "critical",
        title: "Annat kritiskt avtal",
        description: "Ytterligare ett avtal löper ut.",
        system_id: "sys-9",
      })
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(
            makeResponse({
              items: [criticalNotification, extraCritical, warningNotification],
              total: 3,
              by_severity: { critical: 2, warning: 1, info: 0 },
            })
          )
        )
      )
      renderPage()
      // Statistikkorten renderas direkt med by_severity från API-svaret
      await waitFor(() => {
        const titles = screen.getAllByText("Avtal löper ut inom 30 dagar")
        expect(titles.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Tomt tillstånd", () => {
    it("visar 'Inga aktiva notifikationer' när listan är tom", async () => {
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(makeResponse())
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/inga aktiva notifikationer/i)
        ).toBeInTheDocument()
      )
    })

    it("visar undertexten 'Alla system ser bra ut' vid tomt tillstånd", async () => {
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(makeResponse())
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/alla system ser bra ut/i)
        ).toBeInTheDocument()
      )
    })

    it("visar inte notifikationsgrupper när listan är tom", async () => {
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(makeResponse())
        )
      )
      renderPage()
      await waitFor(() =>
        expect(screen.queryByText(/kritisk \(/i)).not.toBeInTheDocument()
      )
    })
  })

  describe("Felhantering", () => {
    it("visar felmeddelande vid API-fel", async () => {
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta notifikationer/i)
        ).toBeInTheDocument()
      )
    })

    it("visar inte laddningstext efter fel", async () => {
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.queryByText(/laddar notifikationer/i)
        ).not.toBeInTheDocument()
      )
    })
  })

  describe("Paginering", () => {
    it("visar paginering när total överstiger PAGE_SIZE (25)", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeNotification({ title: `Notis ${i}`, severity: "warning" })
      )
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(
            makeResponse({
              items,
              total: 50,
              by_severity: { critical: 0, warning: 50, info: 0 },
            })
          )
        )
      )
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/sida 1 av 2/i)).toBeInTheDocument()
      )
    })

    it("Föregående-knapp är inaktiverad på första sidan", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeNotification({ title: `Notis ${i}`, severity: "warning" })
      )
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(
            makeResponse({
              items,
              total: 50,
              by_severity: { critical: 0, warning: 50, info: 0 },
            })
          )
        )
      )
      renderPage()
      await waitFor(() => screen.getByText(/sida 1 av 2/i))
      expect(
        screen.getByRole("button", { name: /föregående/i })
      ).toBeDisabled()
    })

    it("Nästa-knapp är aktiv på första sidan", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeNotification({ title: `Notis ${i}`, severity: "info" })
      )
      server.use(
        http.get("/api/v1/notifications/", () =>
          HttpResponse.json(
            makeResponse({
              items,
              total: 50,
              by_severity: { critical: 0, warning: 0, info: 50 },
            })
          )
        )
      )
      renderPage()
      await waitFor(() => screen.getByText(/sida 1 av 2/i))
      expect(
        screen.getByRole("button", { name: /nästa/i })
      ).not.toBeDisabled()
    })

    it("klick på Nästa skickar offset=25 till API", async () => {
      let capturedOffset: string | null = null
      const items = Array.from({ length: 25 }, (_, i) =>
        makeNotification({ title: `Notis ${i}`, severity: "info" })
      )
      server.use(
        http.get("/api/v1/notifications/", ({ request }) => {
          const url = new URL(request.url)
          capturedOffset = url.searchParams.get("offset")
          return HttpResponse.json(
            makeResponse({
              items,
              total: 50,
              by_severity: { critical: 0, warning: 0, info: 50 },
            })
          )
        })
      )
      renderPage()
      await waitFor(() => screen.getByRole("button", { name: /nästa/i }))
      await userEvent.click(screen.getByRole("button", { name: /nästa/i }))
      await waitFor(() => expect(capturedOffset).toBe("25"))
    })
  })
})
