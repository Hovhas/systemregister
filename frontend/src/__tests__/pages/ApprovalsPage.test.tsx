/**
 * Testsvit: ApprovalsPage
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import ApprovalsPage from "@/pages/ApprovalsPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockApprovals = [
  {
    id: "appr-1",
    organization_id: "org-1",
    approval_type: "systemregistrering",
    status: "väntande",
    title: "Registrering av nytt system",
    description: "Nytt ekonomisystem",
    target_table: null,
    target_record_id: null,
    proposed_changes: null,
    requested_by: "Anna Svensson",
    reviewed_by: null,
    review_comment: null,
    created_at: "2025-01-15T00:00:00Z",
    updated_at: "2025-01-15T00:00:00Z",
    reviewed_at: null,
  },
  {
    id: "appr-2",
    organization_id: "org-1",
    approval_type: "avveckling",
    status: "godkänd",
    title: "Avveckling av gammalt system",
    description: "HR-legacy",
    target_table: null,
    target_record_id: null,
    proposed_changes: null,
    requested_by: "Bo Karlsson",
    reviewed_by: "Clara Eriksson",
    review_comment: "Godkänt att avveckla",
    created_at: "2025-01-10T00:00:00Z",
    updated_at: "2025-01-12T00:00:00Z",
    reviewed_at: "2025-01-12T00:00:00Z",
  },
  {
    id: "appr-3",
    organization_id: "org-1",
    approval_type: "klassningsändring",
    status: "avvisad",
    title: "Ändra klassning för vårdsystem",
    description: null,
    target_table: null,
    target_record_id: null,
    proposed_changes: null,
    requested_by: "David Lund",
    reviewed_by: "Eva Nilsson",
    review_comment: "Otillräckligt underlag",
    created_at: "2025-01-05T00:00:00Z",
    updated_at: "2025-01-08T00:00:00Z",
    reviewed_at: "2025-01-08T00:00:00Z",
  },
]

const paginatedResponse = (items = mockApprovals, total = 3) => ({
  items,
  total,
  limit: 50,
  offset: 0,
})

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/approvals", () => HttpResponse.json(paginatedResponse())),
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderApprovals() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ApprovalsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// --- Tester ---

describe("ApprovalsPage", () => {
  it("renderar sidan med rubrik Godkännanden", async () => {
    renderApprovals()
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /godkännanden/i })).toBeInTheDocument(),
    )
  })

  it("visar status-badges", async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByText("Väntande")).toBeInTheDocument()
      expect(screen.getByText("Godkänd")).toBeInTheDocument()
      expect(screen.getByText("Avvisad")).toBeInTheDocument()
    })
  })

  it("status-filter skickar status till API", async () => {
    let capturedStatus: string | null = null
    server.use(
      http.get("/api/v1/approvals", ({ request }) => {
        const url = new URL(request.url)
        capturedStatus = url.searchParams.get("status")
        return HttpResponse.json(paginatedResponse())
      }),
    )
    renderApprovals()
    await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(2))

    // Status-filter är den andra comboboxen
    const selects = screen.getAllByRole("combobox")
    const statusSelect = selects[1]
    await userEvent.click(statusSelect)
    await waitFor(() => screen.getByRole("option", { name: /väntande/i }))
    await userEvent.click(screen.getByRole("option", { name: /väntande/i }))

    await waitFor(() => expect(capturedStatus).toBe("väntande"))
  })

  it("väntande godkännande visar Godkänn/Avvisa-knappar", async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /godkänn/i })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: /avvisa/i })).toBeInTheDocument()
    })
  })

  it("icke-väntande godkännanden visar inte Godkänn-knapp", async () => {
    // Visa bara godkända
    server.use(
      http.get("/api/v1/approvals", () =>
        HttpResponse.json(paginatedResponse([mockApprovals[1]], 1)),
      ),
    )
    renderApprovals()
    await waitFor(() => screen.getByText("Avveckling av gammalt system"))
    expect(screen.queryByRole("button", { name: /^godkänn$/i })).not.toBeInTheDocument()
  })

  it("klick på Godkänn öppnar granskningsdialog", async () => {
    renderApprovals()
    await waitFor(() => screen.getByRole("button", { name: /godkänn/i }))
    await userEvent.click(screen.getByRole("button", { name: /godkänn/i }))
    await waitFor(() =>
      expect(screen.getByText(/ange ditt namn/i)).toBeInTheDocument(),
    )
  })
})
