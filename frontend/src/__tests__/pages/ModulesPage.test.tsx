/**
 * Testsvit: ModulesPage
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import ModulesPage from "@/pages/ModulesPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockModules = [
  {
    id: "mod-1",
    organization_id: "org-1",
    name: "Analysmodul",
    description: "AI-driven analys",
    lifecycle_status: "i_drift",
    hosting_model: null,
    product_name: "AnalysPro",
    product_version: "2.0",
    uses_ai: true,
    ai_risk_class: "hög_risk",
    ai_usage_description: "Automatiserad riskbedömning",
    license_id: null,
    cpe: null,
    purl: null,
    supplier: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "mod-2",
    organization_id: "org-1",
    name: "Rapportmodul",
    description: "Rapportering",
    lifecycle_status: "planerad",
    hosting_model: null,
    product_name: null,
    product_version: null,
    uses_ai: false,
    ai_risk_class: null,
    ai_usage_description: null,
    license_id: null,
    cpe: null,
    purl: null,
    supplier: null,
    created_at: "2025-02-01T00:00:00Z",
    updated_at: "2025-02-01T00:00:00Z",
  },
]

const paginatedResponse = (items = mockModules, total = 2) => ({
  items,
  total,
  limit: 50,
  offset: 0,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/modules", () => HttpResponse.json(paginatedResponse())),
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderModules() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ModulesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// --- Tester ---

describe("ModulesPage", () => {
  it("renderar sidan med rubrik Moduler", async () => {
    renderModules()
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /moduler/i })).toBeInTheDocument(),
    )
  })

  it("visar modulnamnen i tabellen", async () => {
    renderModules()
    await waitFor(() => {
      expect(screen.getByText("Analysmodul")).toBeInTheDocument()
      expect(screen.getByText("Rapportmodul")).toBeInTheDocument()
    })
  })

  it("visar AI Ja-badge för modul med uses_ai=true", async () => {
    renderModules()
    await waitFor(() => {
      const jaBadges = screen.getAllByText("Ja")
      expect(jaBadges.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("visar AI Nej-badge för modul med uses_ai=false", async () => {
    renderModules()
    await waitFor(() => {
      const nejBadges = screen.getAllByText("Nej")
      expect(nejBadges.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("visar AI-riskklass-badge med text", async () => {
    renderModules()
    await waitFor(() => {
      expect(screen.getByText("Hög risk")).toBeInTheDocument()
    })
  })

  it("AI-riskklass-badge har orange CSS-klass för hög_risk", async () => {
    renderModules()
    await waitFor(() => screen.getByText("Hög risk"))
    const badge = screen.getByText("Hög risk")
    expect(badge.className).toMatch(/orange/)
  })

  it("create-dialog visar AI-riskklass-select när uses_ai är ikryssad", async () => {
    renderModules()
    await waitFor(() => screen.getByRole("button", { name: /ny modul/i }))
    await userEvent.click(screen.getByRole("button", { name: /ny modul/i }))
    await waitFor(() => screen.getByRole("dialog"))

    const dialog = screen.getByRole("dialog")

    // "Välj riskklass"-placeholder bör inte finnas innan AI kryssas i
    expect(within(dialog).queryByText(/välj riskklass/i)).not.toBeInTheDocument()

    // Kryssa i "Använder AI"
    const aiCheckbox = screen.getByLabelText(/använder ai/i)
    await userEvent.click(aiCheckbox)

    // Nu bör AI-riskklass-select visas i dialogen
    await waitFor(() =>
      expect(within(dialog).getByText(/välj riskklass/i)).toBeInTheDocument(),
    )
  })
})
