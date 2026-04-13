/**
 * Testsvit: ComponentsPage
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import ComponentsPage from "@/pages/ComponentsPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockSystems = {
  items: [
    { id: "sys-1", name: "Ekonomisystem", organization_id: "org-1" },
    { id: "sys-2", name: "HR-system", organization_id: "org-1" },
  ],
  total: 2,
  limit: 200,
  offset: 0,
}

const mockComponents = [
  {
    id: "comp-1",
    system_id: "sys-1",
    organization_id: "org-1",
    name: "Fakturemodul",
    description: "Hanterar fakturor",
    component_type: "modul",
    url: "https://faktura.example.com",
    business_area: "Ekonomi",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "comp-2",
    system_id: "sys-2",
    organization_id: "org-1",
    name: "Löneberäkning",
    description: "Beräknar löner",
    component_type: "tjänst",
    url: null,
    business_area: "HR",
    created_at: "2025-02-01T00:00:00Z",
    updated_at: "2025-02-01T00:00:00Z",
  },
]

const paginatedResponse = (items = mockComponents, total = 2) => ({
  items,
  total,
  limit: 50,
  offset: 0,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems", () => HttpResponse.json(mockSystems)),
  http.get("/api/v1/components", () => HttpResponse.json(paginatedResponse())),
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderComponents() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ComponentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// --- Tester ---

describe("ComponentsPage", () => {
  it("renderar sidan med rubrik Komponenter", async () => {
    renderComponents()
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /komponenter/i })).toBeInTheDocument(),
    )
  })

  it("visar komponentnamnen i tabellen", async () => {
    renderComponents()
    await waitFor(() => {
      expect(screen.getByText("Fakturemodul")).toBeInTheDocument()
      expect(screen.getByText("Löneberäkning")).toBeInTheDocument()
    })
  })

  it("visar systemnamn i tabellen via map", async () => {
    renderComponents()
    await waitFor(() => {
      expect(screen.getByText("Ekonomisystem")).toBeInTheDocument()
    })
  })

  it("system-filter skickar system_id till API", async () => {
    let capturedSystemId: string | null = null
    server.use(
      http.get("/api/v1/components", ({ request }) => {
        const url = new URL(request.url)
        capturedSystemId = url.searchParams.get("system_id")
        return HttpResponse.json(paginatedResponse())
      }),
    )
    renderComponents()
    await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(2))

    // System-filter är den andra comboboxen (efter organisation)
    const selects = screen.getAllByRole("combobox")
    const systemSelect = selects[1]
    await userEvent.click(systemSelect)
    await waitFor(() => screen.getByRole("option", { name: "Ekonomisystem" }))
    await userEvent.click(screen.getByRole("option", { name: "Ekonomisystem" }))

    await waitFor(() => expect(capturedSystemId).toBe("sys-1"))
  })

  it("visar URL-länk för komponent med URL", async () => {
    renderComponents()
    await waitFor(() => {
      const links = screen.getAllByText("Länk")
      expect(links.length).toBeGreaterThanOrEqual(1)
    })
  })
})
