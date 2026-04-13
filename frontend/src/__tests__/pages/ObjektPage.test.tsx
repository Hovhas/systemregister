/**
 * Testsvit: ObjektPage
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import ObjektPage from "@/pages/ObjektPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockObjekt = [
  {
    id: "obj-1",
    organization_id: "org-1",
    name: "Ekonomiobjekt",
    description: "Hanterar ekonomi",
    object_owner: "Anna Svensson",
    object_leader: "Bo Karlsson",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "obj-2",
    organization_id: "org-1",
    name: "HR-objekt",
    description: "Personalhantering",
    object_owner: "Clara Eriksson",
    object_leader: null,
    created_at: "2025-02-01T00:00:00Z",
    updated_at: "2025-02-01T00:00:00Z",
  },
]

const paginatedResponse = (items = mockObjekt, total = 2) => ({
  items,
  total,
  limit: 50,
  offset: 0,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/objekt", () => HttpResponse.json(paginatedResponse())),
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderObjektPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ObjektPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// --- Tester ---

describe("ObjektPage", () => {
  it("renderar sidan med rubrik Objekt", async () => {
    renderObjektPage()
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /^objekt$/i })).toBeInTheDocument(),
    )
  })

  it("visar tom-text när inga objekt finns", async () => {
    server.use(
      http.get("/api/v1/objekt", () =>
        HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 }),
      ),
    )
    renderObjektPage()
    await waitFor(() =>
      expect(screen.getByText(/inga objekt matchar sökningen/i)).toBeInTheDocument(),
    )
  })

  it("visar objektnamnen i tabellen", async () => {
    renderObjektPage()
    await waitFor(() => {
      expect(screen.getByText("Ekonomiobjekt")).toBeInTheDocument()
      expect(screen.getByText("HR-objekt")).toBeInTheDocument()
    })
  })

  it("visar organisations-namn i tabellen", async () => {
    renderObjektPage()
    await waitFor(() => {
      const kommunen = screen.getAllByText("Kommunen")
      expect(kommunen.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("sökinput uppdateras vid skrivning", async () => {
    renderObjektPage()
    await waitFor(() => screen.getByPlaceholderText(/sök objekt/i))
    const input = screen.getByPlaceholderText(/sök objekt/i)
    await userEvent.type(input, "HR")
    expect(input).toHaveValue("HR")
  })

  it("klick på Nytt objekt öppnar dialog", async () => {
    renderObjektPage()
    await waitFor(() => screen.getByRole("button", { name: /nytt objekt/i }))
    await userEvent.click(screen.getByRole("button", { name: /nytt objekt/i }))
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument(),
    )
  })

  it("submit anropar POST-mock", async () => {
    let postCalled = false
    server.use(
      http.post("/api/v1/objekt", () => {
        postCalled = true
        return HttpResponse.json({ id: "obj-new", name: "TestObj", organization_id: "org-1", created_at: "2025-03-01T00:00:00Z", updated_at: "2025-03-01T00:00:00Z" })
      }),
    )
    renderObjektPage()
    await waitFor(() => screen.getByRole("button", { name: /nytt objekt/i }))
    await userEvent.click(screen.getByRole("button", { name: /nytt objekt/i }))
    await waitFor(() => screen.getByRole("dialog"))

    // Fyll i formulär
    await userEvent.type(screen.getByPlaceholderText("Objektnamn"), "TestObj")
    // Välj organisation i dialog
    const selects = screen.getAllByRole("combobox")
    const orgSelect = selects[selects.length - 1] // Sista comboboxen i dialogen
    await userEvent.click(orgSelect)
    await waitFor(() => screen.getByRole("option", { name: "Kommunen" }))
    await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))

    await userEvent.click(screen.getByRole("button", { name: /^skapa$/i }))
    await waitFor(() => expect(postCalled).toBe(true), { timeout: 2000 })
  })
})
