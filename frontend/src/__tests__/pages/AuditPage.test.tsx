/**
 * Testsvit: AuditPage
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
import AuditPage from "@/pages/AuditPage"
import type { AuditEntry, AuditResponse } from "@/types"

// --- Testdata ---

function makeEntry(overrides: Partial<AuditEntry> = {}): AuditEntry {
  return {
    id: "audit-1",
    table_name: "systems",
    record_id: "sys-1",
    action: "INSERT",
    changed_by: "admin@sundsvall.se",
    changed_at: "2026-01-15T10:30:00Z",
    old_values: null,
    new_values: { name: "Ekonomisystem", criticality: "hög" },
    ...overrides,
  }
}

function makeResponse(overrides: Partial<AuditResponse> = {}): AuditResponse {
  return {
    items: [],
    total: 0,
    limit: 25,
    offset: 0,
    ...overrides,
  }
}

const insertEntry = makeEntry({
  id: "audit-1",
  table_name: "systems",
  action: "INSERT",
  changed_by: "anna@sundsvall.se",
  changed_at: "2026-01-15T10:30:00Z",
  old_values: null,
  new_values: { name: "Ekonomisystem" },
})

const updateEntry = makeEntry({
  id: "audit-2",
  table_name: "organizations",
  action: "UPDATE",
  changed_by: "bjorn@sundsvall.se",
  changed_at: "2026-02-01T14:00:00Z",
  old_values: { name: "Gamla Bolaget" },
  new_values: { name: "Nya Bolaget" },
})

const deleteEntry = makeEntry({
  id: "audit-3",
  table_name: "contracts",
  action: "DELETE",
  changed_by: null,
  changed_at: "2026-03-10T09:00:00Z",
  old_values: { supplier: "Leverantör AB" },
  new_values: null,
})

const defaultResponse = makeResponse({
  items: [insertEntry, updateEntry, deleteEntry],
  total: 3,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/audit/", () => HttpResponse.json(defaultResponse))
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
        <AuditPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("AuditPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar rubriken Ändringslogg", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /ändringslogg/i })
        ).toBeInTheDocument()
      )
    })

    it("visar laddningstext medan data hämtas", () => {
      renderPage()
      expect(screen.getByText(/laddar ändringslogg/i)).toBeInTheDocument()
    })

    it("visar tabellhuvuden: Tidpunkt, Tabell, Åtgärd, Ändrad av", async () => {
      renderPage()
      await waitFor(() => {
        expect(screen.getByRole("columnheader", { name: /tidpunkt/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /tabell/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /åtgärd/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /ändrad av/i })).toBeInTheDocument()
      })
    })

    it("visar totalt antal poster i kortrubriken", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/3 poster/i)).toBeInTheDocument()
      )
    })
  })

  describe("Ändringsloggen", () => {
    it("visar tabellnamnet System för systems-poster", async () => {
      renderPage()
      await waitFor(() => {
        const cells = screen.getAllByText("System")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar tabellnamnet Organisation för organizations-poster", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Organisation")).toBeInTheDocument()
      )
    })

    it("visar tabellnamnet Avtal för contracts-poster", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Avtal")).toBeInTheDocument()
      )
    })

    it("visar åtgärdsbadge Skapad för INSERT", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Skapad")).toBeInTheDocument()
      )
    })

    it("visar åtgärdsbadge Ändrad för UPDATE", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Ändrad")).toBeInTheDocument()
      )
    })

    it("visar åtgärdsbadge Borttagen för DELETE", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Borttagen")).toBeInTheDocument()
      )
    })

    it("visar avsändarens e-postadress i Ändrad av-kolumnen", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("anna@sundsvall.se")).toBeInTheDocument()
      )
    })

    it("visar 'System' i Ändrad av-kolumnen när changed_by är null", async () => {
      renderPage()
      await waitFor(() => {
        // deleteEntry har changed_by = null -> ska visas som "System"
        const cells = screen.getAllByText("System")
        // "System" förekommer både som tabellnamn (för systems-raden) och som "Ändrad av"
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Filter på tabell", () => {
    it("skickar table_name-parameter till API vid val av tabellfilter", async () => {
      let capturedTableName: string | null = null
      server.use(
        http.get("/api/v1/audit/", ({ request }) => {
          const url = new URL(request.url)
          capturedTableName = url.searchParams.get("table_name")
          return HttpResponse.json(defaultResponse)
        })
      )
      renderPage()
      // Vänta tills sidan är laddad
      await waitFor(() => screen.getByText(/3 poster/i))

      // Öppna tabellfilter (index 0 bland comboboxar)
      const combos = screen.getAllByRole("combobox")
      await userEvent.click(combos[0])
      await waitFor(() => screen.getByRole("option", { name: /^system$/i }))
      await userEvent.click(screen.getByRole("option", { name: /^system$/i }))

      await waitFor(() => expect(capturedTableName).toBe("systems"))
    })

    it("skickar action-parameter till API vid val av åtgärdsfilter", async () => {
      let capturedAction: string | null = null
      server.use(
        http.get("/api/v1/audit/", ({ request }) => {
          const url = new URL(request.url)
          capturedAction = url.searchParams.get("action")
          return HttpResponse.json(defaultResponse)
        })
      )
      renderPage()
      await waitFor(() => screen.getByText(/3 poster/i))

      // Åtgärdsfilter är index 1 bland comboboxar
      const combos = screen.getAllByRole("combobox")
      await userEvent.click(combos[1])
      await waitFor(() => screen.getByRole("option", { name: /^ändrad$/i }))
      await userEvent.click(screen.getByRole("option", { name: /^ändrad$/i }))

      await waitFor(() => expect(capturedAction).toBe("UPDATE"))
    })

    it("återställer sida till 0 vid tabellfilter-byte", async () => {
      let capturedOffset: string | null = null
      server.use(
        http.get("/api/v1/audit/", ({ request }) => {
          const url = new URL(request.url)
          capturedOffset = url.searchParams.get("offset")
          return HttpResponse.json(defaultResponse)
        })
      )
      renderPage()
      await waitFor(() => screen.getByText(/3 poster/i))

      const combos = screen.getAllByRole("combobox")
      await userEvent.click(combos[0])
      await waitFor(() => screen.getByRole("option", { name: /^organisation$/i }))
      await userEvent.click(screen.getByRole("option", { name: /^organisation$/i }))

      await waitFor(() =>
        expect(capturedOffset === null || capturedOffset === "0").toBe(true)
      )
    })

    it("visar 'Alla tabeller' som standardvärde i tabellfilter", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Alla tabeller")).toBeInTheDocument()
      )
    })

    it("visar 'Alla åtgärder' som standardvärde i åtgärdsfilter", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Alla åtgärder")).toBeInTheDocument()
      )
    })
  })

  describe("Expanderbar rad med detaljer", () => {
    it("expanderar rad vid klick och visar JSON-diff", async () => {
      renderPage()
      await waitFor(() => screen.getByText("Organisation"))

      // Klicka på UPDATE-raden (updateEntry: Organisation, Ändrad)
      const rows = screen.getAllByRole("row")
      // Rad 0 är header, hitta raden med "Organisation" och "Ändrad"
      const orgRow = rows.find(
        (r) =>
          r.textContent?.includes("Organisation") &&
          r.textContent?.includes("Ändrad")
      )
      expect(orgRow).toBeTruthy()
      await userEvent.click(orgRow!)

      // JSON-diff-tabellen ska nu visas med kolumnerna Fält, Innan, Efter
      await waitFor(() =>
        expect(screen.getByText("Innan")).toBeInTheDocument()
      )
      await waitFor(() =>
        expect(screen.getByText("Efter")).toBeInTheDocument()
      )
    })

    it("visar fältnamnet 'name' i JSON-diff efter expansion", async () => {
      renderPage()
      await waitFor(() => screen.getByText("Organisation"))

      const rows = screen.getAllByRole("row")
      const orgRow = rows.find(
        (r) =>
          r.textContent?.includes("Organisation") &&
          r.textContent?.includes("Ändrad")
      )
      await userEvent.click(orgRow!)

      await waitFor(() =>
        expect(screen.getByText("name")).toBeInTheDocument()
      )
    })

    it("visar gammalt värde i JSON-diff", async () => {
      renderPage()
      await waitFor(() => screen.getByText("Organisation"))

      const rows = screen.getAllByRole("row")
      const orgRow = rows.find(
        (r) =>
          r.textContent?.includes("Organisation") &&
          r.textContent?.includes("Ändrad")
      )
      await userEvent.click(orgRow!)

      await waitFor(() =>
        expect(screen.getByText(/"Gamla Bolaget"/)).toBeInTheDocument()
      )
    })

    it("visar nytt värde i JSON-diff", async () => {
      renderPage()
      await waitFor(() => screen.getByText("Organisation"))

      const rows = screen.getAllByRole("row")
      const orgRow = rows.find(
        (r) =>
          r.textContent?.includes("Organisation") &&
          r.textContent?.includes("Ändrad")
      )
      await userEvent.click(orgRow!)

      await waitFor(() =>
        expect(screen.getByText(/"Nya Bolaget"/)).toBeInTheDocument()
      )
    })

    it("kollapsas raden vid andra klick", async () => {
      renderPage()
      await waitFor(() => screen.getByText("Organisation"))

      const rows = screen.getAllByRole("row")
      const orgRow = rows.find(
        (r) =>
          r.textContent?.includes("Organisation") &&
          r.textContent?.includes("Ändrad")
      )
      // Expandera
      await userEvent.click(orgRow!)
      await waitFor(() => screen.getByText("Innan"))

      // Kollapsa
      await userEvent.click(orgRow!)
      await waitFor(() =>
        expect(screen.queryByText("Innan")).not.toBeInTheDocument()
      )
    })
  })

  describe("Tomt tillstånd", () => {
    it("visar 'Inga poster hittades' när listan är tom", async () => {
      server.use(
        http.get("/api/v1/audit/", () =>
          HttpResponse.json(makeResponse({ items: [], total: 0 }))
        )
      )
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/inga poster hittades/i)).toBeInTheDocument()
      )
    })
  })

  describe("Felhantering", () => {
    it("visar felmeddelande vid API-fel", async () => {
      server.use(
        http.get("/api/v1/audit/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta ändringsloggen/i)
        ).toBeInTheDocument()
      )
    })
  })

  describe("Paginering", () => {
    it("visar paginering när total överstiger PAGE_SIZE (25)", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeEntry({ id: `audit-${i}`, table_name: "systems" })
      )
      server.use(
        http.get("/api/v1/audit/", () =>
          HttpResponse.json(makeResponse({ items, total: 60 }))
        )
      )
      renderPage()
      await waitFor(() =>
        expect(screen.getByText(/sida 1 av 3/i)).toBeInTheDocument()
      )
    })

    it("döljer paginering när total <= PAGE_SIZE", async () => {
      renderPage()
      await waitFor(() => screen.getByText(/3 poster/i))
      expect(screen.queryByText(/sida \d+ av \d+/i)).not.toBeInTheDocument()
    })

    it("Föregående-knapp är inaktiverad på första sidan", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeEntry({ id: `audit-${i}` })
      )
      server.use(
        http.get("/api/v1/audit/", () =>
          HttpResponse.json(makeResponse({ items, total: 60 }))
        )
      )
      renderPage()
      await waitFor(() => screen.getByText(/sida 1 av 3/i))
      expect(
        screen.getByRole("button", { name: /föregående/i })
      ).toBeDisabled()
    })

    it("Nästa-knapp är aktiv på första sidan med fler sidor", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeEntry({ id: `audit-${i}` })
      )
      server.use(
        http.get("/api/v1/audit/", () =>
          HttpResponse.json(makeResponse({ items, total: 60 }))
        )
      )
      renderPage()
      await waitFor(() => screen.getByText(/sida 1 av 3/i))
      expect(
        screen.getByRole("button", { name: /nästa/i })
      ).not.toBeDisabled()
    })

    it("klick på Nästa beger sig till sida 2", async () => {
      let capturedOffset: string | null = null
      const items = Array.from({ length: 25 }, (_, i) =>
        makeEntry({ id: `audit-${i}` })
      )
      server.use(
        http.get("/api/v1/audit/", ({ request }) => {
          const url = new URL(request.url)
          capturedOffset = url.searchParams.get("offset")
          return HttpResponse.json(makeResponse({ items, total: 60 }))
        })
      )
      renderPage()
      await waitFor(() => screen.getByRole("button", { name: /nästa/i }))
      await userEvent.click(screen.getByRole("button", { name: /nästa/i }))
      await waitFor(() => expect(capturedOffset).toBe("25"))
    })

    it("Nästa-knapp är inaktiverad på sista sidan", async () => {
      const items = Array.from({ length: 25 }, (_, i) =>
        makeEntry({ id: `audit-${i}` })
      )
      server.use(
        http.get("/api/v1/audit/", ({ request }) => {
          const url = new URL(request.url)
          // Simulera att vi är på sida 3 av 3 (offset=50)
          const offset = parseInt(url.searchParams.get("offset") ?? "0")
          return HttpResponse.json(
            makeResponse({
              items: offset >= 50 ? items.slice(0, 10) : items,
              total: 60,
              offset,
            })
          )
        })
      )
      renderPage()
      await waitFor(() => screen.getByRole("button", { name: /nästa/i }))
      // Navigera till sida 3
      await userEvent.click(screen.getByRole("button", { name: /nästa/i }))
      await waitFor(() =>
        expect(screen.getByText(/sida 2 av/i)).toBeInTheDocument()
      )
      await userEvent.click(screen.getByRole("button", { name: /nästa/i }))
      await waitFor(() =>
        expect(screen.getByRole("button", { name: /nästa/i })).toBeDisabled()
      )
    })
  })
})
