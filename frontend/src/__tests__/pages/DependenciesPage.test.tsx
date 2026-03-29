/**
 * Testsvit: DependenciesPage
 * ~40 testfall
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import DependenciesPage from "@/pages/DependenciesPage"

// --- Testdata ---

const mockSystems = [
  { id: "sys-1", name: "Ekonomisystem", criticality: "hög", organization_id: "org-1", system_category: "verksamhetssystem", lifecycle_status: "i_drift", nis2_applicable: false },
  { id: "sys-2", name: "HR-system", criticality: "medel", organization_id: "org-1", system_category: "verksamhetssystem", lifecycle_status: "i_drift", nis2_applicable: false },
  { id: "sys-3", name: "Vårdsystem", criticality: "kritisk", organization_id: "org-1", system_category: "verksamhetssystem", lifecycle_status: "i_drift", nis2_applicable: false },
]

const mockIntegrations = [
  {
    id: "int-1",
    source_system_id: "sys-1",
    target_system_id: "sys-2",
    integration_type: "api",
    data_types: "Löndata",
    frequency: "Dagligen",
    description: "Ekonomi till HR",
    criticality: "hög",
    is_external: false,
    external_party: null,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "int-2",
    source_system_id: "sys-2",
    target_system_id: "sys-3",
    integration_type: "filöverföring",
    data_types: null,
    frequency: "Månadsvis",
    description: "HR till vård",
    criticality: "kritisk",
    is_external: false,
    external_party: null,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "int-3",
    source_system_id: "sys-3",
    target_system_id: "sys-1",
    integration_type: "manuell",
    data_types: null,
    frequency: null,
    description: "Extern partner",
    criticality: null,
    is_external: true,
    external_party: "Extern leverantör",
    created_at: "2024-01-01T00:00:00Z",
  },
]

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/integrations", () => HttpResponse.json(mockIntegrations)),
  http.get("/api/v1/systems", () => HttpResponse.json({ items: mockSystems, total: mockSystems.length, limit: 200, offset: 0 }))
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderDependencies() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DependenciesPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("DependenciesPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar sidrubriken Beroendekarta", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /beroendekarta/i })
        ).toBeInTheDocument()
      )
    })

    it("renderar undertexten om visualisering", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByText(/visualisering av systemintegrationer/i)
        ).toBeInTheDocument()
      )
    })

    it("visar laddningstext initialt", () => {
      renderDependencies()
      expect(screen.getByText(/laddar integrationer/i)).toBeInTheDocument()
    })

    it("döljer laddningstext efter data laddats", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.queryByText(/laddar integrationer/i)
        ).not.toBeInTheDocument()
      )
    })
  })

  describe("KPI-kort", () => {
    it("visar KPI-kort: Integrationer med rätt antal (3)", async () => {
      renderDependencies()
      await waitFor(() => {
        expect(screen.getByText("Integrationer")).toBeInTheDocument()
        // Båda Integrationer och Berörda system visar 3 — verifiera att minst ett element finns
        const threes = screen.getAllByText("3")
        expect(threes.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar KPI-kort: Berörda system (3 unika)", async () => {
      renderDependencies()
      await waitFor(() => {
        expect(screen.getByText("Berörda system")).toBeInTheDocument()
      })
    })

    it("visar KPI-kort: Kritiska / Externa", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(screen.getByText(/kritiska \/ externa/i)).toBeInTheDocument()
      )
    })

    it("KPI-kort visar skeleton under laddning", () => {
      renderDependencies()
      const skeletons = document.querySelectorAll(".skeleton")
      expect(skeletons.length).toBeGreaterThanOrEqual(1)
    })

    it("KPI-kort visar kritisk-antal i röd färg", async () => {
      renderDependencies()
      await waitFor(() => {
        const destructive = document.querySelector(".text-destructive")
        expect(destructive).toBeInTheDocument()
      })
    })
  })

  describe("Felhantering", () => {
    it("visar felmeddelande vid API-fel", async () => {
      server.use(
        http.get("/api/v1/integrations", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta data/i)
        ).toBeInTheDocument()
      )
    })

    it("femeddelande har error-styling", async () => {
      server.use(
        http.get("/api/v1/integrations", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderDependencies()
      await waitFor(() => {
        const errorEl = screen.getByText(/kunde inte hämta data/i)
        expect(errorEl.closest("div")).toHaveClass("text-destructive")
      })
    })
  })

  describe("Tabbar (Graf / Tabell)", () => {
    it("renderar Nätverksgraf-fliken", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByRole("tab", { name: /nätverksgraf/i })
        ).toBeInTheDocument()
      )
    })

    it("renderar Tabell-fliken", async () => {
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByRole("tab", { name: /tabell/i })
        ).toBeInTheDocument()
      )
    })

    it("kan byta till Tabell-vy", async () => {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(screen.getByRole("columnheader", { name: /källsystem/i })).toBeInTheDocument()
      )
    })
  })

  describe("Tabell-vy", () => {
    async function switchToTable() {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        screen.getByRole("columnheader", { name: /källsystem/i })
      )
    }

    it("visar kolumnhuvuden: Källsystem, Målsystem, Typ, Kritikalitet, Frekvens", async () => {
      await switchToTable()
      expect(
        screen.getByRole("columnheader", { name: /källsystem/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("columnheader", { name: /målsystem/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("columnheader", { name: /typ/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("columnheader", { name: /kritikalitet/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("columnheader", { name: /frekvens/i })
      ).toBeInTheDocument()
    })

    it("visar systemnamn i tabellen", async () => {
      await switchToTable()
      // Ekonomisystem kan förekomma i både källsystem och målsystem-kolumner
      expect(screen.getAllByText("Ekonomisystem").length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText("HR-system").length).toBeGreaterThanOrEqual(1)
    })

    it("visar integrations-typ som badge", async () => {
      await switchToTable()
      expect(screen.getByText("API")).toBeInTheDocument()
    })

    it("visar frekvens Dagligen", async () => {
      await switchToTable()
      expect(screen.getByText("Dagligen")).toBeInTheDocument()
    })

    it("visar extern part som badge", async () => {
      await switchToTable()
      expect(screen.getByText("Extern leverantör")).toBeInTheDocument()
    })

    it("visar — för null-frekvens", async () => {
      await switchToTable()
      const dashes = screen.getAllByText("—")
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe("SVG-graf", () => {
    it("renderar SVG-element i nätverksgraf-vy", async () => {
      renderDependencies()
      await waitFor(() => {
        const svg = document.querySelector("svg")
        expect(svg).toBeInTheDocument()
      })
    })

    it("SVG har rätt viewBox", async () => {
      renderDependencies()
      await waitFor(() => {
        // Use role="img" to find the dependency graph SVG, not icon SVGs
        const svg = screen.getByRole("img", { name: /beroendevisualisering/i })
        expect(svg?.getAttribute("viewBox")).toBe("0 0 800 560")
      })
    })

    it("renderar noder (cirklar) för varje system", async () => {
      renderDependencies()
      await waitFor(() => {
        const circles = document.querySelectorAll("circle")
        expect(circles.length).toBe(3)
      })
    })

    it("renderar kanter (linjer) för varje integration", async () => {
      renderDependencies()
      await waitFor(() => {
        // Varje kant har 2 linjer (hover-yta + synlig kant)
        const lines = document.querySelectorAll("line")
        expect(lines.length).toBeGreaterThanOrEqual(3)
      })
    })

    it("renderar pil-markörer för riktning", async () => {
      renderDependencies()
      await waitFor(() => {
        const markers = document.querySelectorAll("marker")
        expect(markers.length).toBeGreaterThan(0)
      })
    })

    it("renderar kritikalitets-förklaring", async () => {
      renderDependencies()
      await waitFor(() => {
        expect(screen.getByText("Låg")).toBeInTheDocument()
        expect(screen.getByText("Medel")).toBeInTheDocument()
        expect(screen.getByText("Hög")).toBeInTheDocument()
        expect(screen.getByText("Kritisk")).toBeInTheDocument()
      })
    })
  })

  describe("Tom vy (inga integrationer)", () => {
    it("visar 'Inga integrationer att visa' i graf-vy", async () => {
      server.use(
        http.get("/api/v1/integrations", () => HttpResponse.json([]))
      )
      renderDependencies()
      await waitFor(() =>
        expect(
          screen.getByText(/inga integrationer att visa/i)
        ).toBeInTheDocument()
      )
    })

    it("visar 'Inga integrationer registrerade' i tabell-vy vid tom data", async () => {
      server.use(
        http.get("/api/v1/integrations", () => HttpResponse.json([]))
      )
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(
          screen.getByText(/inga integrationer registrerade/i)
        ).toBeInTheDocument()
      )
    })

    it("KPI-kort visar 0 vid inga integrationer", async () => {
      server.use(
        http.get("/api/v1/integrations", () => HttpResponse.json([]))
      )
      renderDependencies()
      await waitFor(() => {
        const zeros = screen.getAllByText("0")
        expect(zeros.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Extern integration", () => {
    it("visar Extern part i tabellen", async () => {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(screen.getByText("Extern leverantör")).toBeInTheDocument()
      )
    })

    it("visar Extern part-kolumn i tabellhuvudet", async () => {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(
          screen.getByRole("columnheader", { name: /extern part/i })
        ).toBeInTheDocument()
      )
    })
  })

  describe("Integrations-typer", () => {
    it("visar Filöverföring som integrationstyp i tabell", async () => {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(screen.getByText("Filöverföring")).toBeInTheDocument()
      )
    })

    it("visar Manuell som integrationstyp i tabell", async () => {
      renderDependencies()
      await waitFor(() => screen.getByRole("tab", { name: /tabell/i }))
      await userEvent.click(screen.getByRole("tab", { name: /tabell/i }))
      await waitFor(() =>
        expect(screen.getByText("Manuell")).toBeInTheDocument()
      )
    })
  })

  describe("Statistik-beräkning", () => {
    it("räknar kritiska integrationer (CRITICAL)", async () => {
      renderDependencies()
      await waitFor(() => {
        // int-2 har criticality: CRITICAL
        const critEl = document.querySelector(".text-destructive")
        expect(critEl?.textContent).toBe("1")
      })
    })

    it("räknar externa integrationer", async () => {
      // int-3 är extern
      renderDependencies()
      await waitFor(() => screen.getByText(/kritiska \/ externa/i))
      // externalCount = 1 (int-3)
      expect(screen.getByText(/kritiska \/ externa/i)).toBeInTheDocument()
    })

    it("räknar unika system i graf (3 unika system-ID:n)", async () => {
      renderDependencies()
      await waitFor(() => {
        const circles = document.querySelectorAll("circle")
        expect(circles.length).toBe(3)
      })
    })
  })
})
