/**
 * Testsvit: InformationAssetsPage
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import InformationAssetsPage from "@/pages/InformationAssetsPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockAssets = [
  {
    id: "ia-1",
    organization_id: "org-1",
    name: "Befolkningsdata",
    description: "Befolkningsregister",
    information_owner: "Eva Nilsson",
    confidentiality: 3,
    integrity: 2,
    availability: 2,
    traceability: null,
    contains_personal_data: true,
    personal_data_type: "personnummer",
    contains_public_records: true,
    ropa_reference_id: null,
    ihp_reference: null,
    preservation_class: null,
    retention_period: null,
    archive_responsible: null,
    e_archive_delivery: null,
    long_term_format: null,
    last_ihp_review: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "ia-2",
    organization_id: "org-1",
    name: "Fastighetsdata",
    description: "Fastighetsregister",
    information_owner: "Karl Berg",
    confidentiality: 1,
    integrity: 3,
    availability: 1,
    traceability: null,
    contains_personal_data: false,
    personal_data_type: null,
    contains_public_records: false,
    ropa_reference_id: null,
    ihp_reference: null,
    preservation_class: null,
    retention_period: null,
    archive_responsible: null,
    e_archive_delivery: null,
    long_term_format: null,
    last_ihp_review: null,
    created_at: "2025-02-01T00:00:00Z",
    updated_at: "2025-02-01T00:00:00Z",
  },
]

const paginatedResponse = (items = mockAssets, total = 2) => ({
  items,
  total,
  limit: 50,
  offset: 0,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/information-assets", () => HttpResponse.json(paginatedResponse())),
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderAssets() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <InformationAssetsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// --- Tester ---

describe("InformationAssetsPage", () => {
  it("renderar sidan med rubrik Informationsmängder", async () => {
    renderAssets()
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /informationsmängder/i })).toBeInTheDocument(),
    )
  })

  it("visar K/R/T-värden i tabellen", async () => {
    renderAssets()
    await waitFor(() => {
      // Befolkningsdata: K=3, R=2, T=2
      expect(screen.getByText("Befolkningsdata")).toBeInTheDocument()
      const cells3 = screen.getAllByText("3")
      expect(cells3.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("visar personuppgifter Ja-badge", async () => {
    renderAssets()
    await waitFor(() => {
      const jaBadges = screen.getAllByText("Ja")
      expect(jaBadges.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("visar personuppgifter Nej-badge", async () => {
    renderAssets()
    await waitFor(() => {
      const nejBadges = screen.getAllByText("Nej")
      expect(nejBadges.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("personuppgifter-filter skickar contains_personal_data till API", async () => {
    let capturedParam: string | null = null
    server.use(
      http.get("/api/v1/information-assets", ({ request }) => {
        const url = new URL(request.url)
        capturedParam = url.searchParams.get("contains_personal_data")
        return HttpResponse.json(paginatedResponse())
      }),
    )
    renderAssets()
    await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(2))

    // Personuppgifter-filter är den andra comboboxen (efter organisation)
    const selects = screen.getAllByRole("combobox")
    const personalDataSelect = selects[1]
    await userEvent.click(personalDataSelect)
    await waitFor(() => screen.getByRole("option", { name: /innehåller personuppgifter/i }))
    await userEvent.click(screen.getByRole("option", { name: /innehåller personuppgifter/i }))

    await waitFor(() => expect(capturedParam).toBe("true"))
  })
})
