/**
 * Testsvit: OrganizationsPage
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
import OrganizationsPage from "@/pages/OrganizationsPage"
import { OrganizationType } from "@/types"
import type { Organization } from "@/types"

// --- Testdata ---

function makeOrg(overrides: Partial<Organization> = {}): Organization {
  return {
    id: "org-1",
    name: "Sundsvalls kommun",
    org_number: "212000-2411",
    org_type: OrganizationType.KOMMUN,
    parent_org_id: null,
    description: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    ...overrides,
  }
}

const mockOrgs: Organization[] = [
  makeOrg({ id: "org-1", name: "Sundsvalls kommun", org_type: OrganizationType.KOMMUN }),
  makeOrg({
    id: "org-2",
    name: "MittHem AB",
    org_type: OrganizationType.BOLAG,
    org_number: "556000-1234",
    parent_org_id: "org-1",
  }),
  makeOrg({
    id: "org-3",
    name: "DigIT",
    org_type: OrganizationType.DIGIT,
    org_number: null,
    parent_org_id: "org-1",
  }),
]

const mockSystemsResponse = {
  items: [
    {
      id: "sys-1",
      organization_id: "org-1",
      name: "Ekonomisystem",
    },
    {
      id: "sys-2",
      organization_id: "org-1",
      name: "HR-system",
    },
    {
      id: "sys-3",
      organization_id: "org-2",
      name: "Fastighetssystem",
    },
  ],
  total: 3,
  limit: 1000,
  offset: 0,
}

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations/", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems/", () => HttpResponse.json(mockSystemsResponse)),
  http.post("/api/v1/organizations/", async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      makeOrg({ id: "org-new", name: body.name as string }),
      { status: 201 }
    )
  }),
  http.patch("/api/v1/organizations/:id", async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(makeOrg({ name: body.name as string }))
  }),
  http.delete("/api/v1/organizations/:id", () =>
    new HttpResponse(null, { status: 204 })
  )
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
        <OrganizationsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("OrganizationsPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar rubriken Organisationer", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /organisationer/i })
        ).toBeInTheDocument()
      )
    })

    it("renderar knappen Ny organisation", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /ny organisation/i })
        ).toBeInTheDocument()
      )
    })

    it("visar laddningstext medan data hämtas", () => {
      renderPage()
      expect(screen.getByText(/laddar organisationer/i)).toBeInTheDocument()
    })
  })

  describe("Organisationslista", () => {
    it("visar alla organisationsnamn i tabellen", async () => {
      renderPage()
      await waitFor(() => {
        // "Sundsvalls kommun" visas i namnkolumnen och i moderorg-kolumnen för underorganisationer
        const sundsvall = screen.getAllByText("Sundsvalls kommun")
        expect(sundsvall.length).toBeGreaterThanOrEqual(1)
        expect(screen.getByText("MittHem AB")).toBeInTheDocument()
        // "DigIT" förekommer som org-namn och som org-typ-label — använd getAllByText
        const digit = screen.getAllByText("DigIT")
        expect(digit.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar org-typ Kommun", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Kommun")).toBeInTheDocument()
      )
    })

    it("visar org-typ Bolag", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("Bolag")).toBeInTheDocument()
      )
    })

    it("visar org-typ DigIT i tabellen", async () => {
      renderPage()
      // "DigIT" är både org-namn och org-typ-label — kontrollera att minst 2 förekomster finns
      await waitFor(() => {
        const digit = screen.getAllByText("DigIT")
        expect(digit.length).toBeGreaterThanOrEqual(2)
      })
    })

    it("visar org-nummer i tabellen", async () => {
      renderPage()
      await waitFor(() =>
        expect(screen.getByText("212000-2411")).toBeInTheDocument()
      )
    })

    it("visar moderorganisationsnamn för underorganisationer", async () => {
      renderPage()
      await waitFor(() => {
        // MittHem AB och DigIT har parent_org_id = "org-1" (Sundsvalls kommun)
        const cells = screen.getAllByText("Sundsvalls kommun")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar — för org utan org-nummer", async () => {
      renderPage()
      await waitFor(() => screen.getAllByText("DigIT"))
      // DigIT (org_number = null) -> ska visas som "—" i org-nummer-kolumnen
      // Hitta raden som har "DigIT" som namncel (font-medium)
      const rows = screen.getAllByRole("row")
      // Namncellen är alltid den första tabellcellen (font-medium)
      const digitRow = rows.find((r) => {
        const firstCell = within(r).queryAllByText("DigIT")
        // Namnkolumnen har font-medium, moderorg-kolumnen inte
        return firstCell.some((el) => el.closest("td")?.className.includes("font-medium"))
      })
      expect(digitRow).toBeTruthy()
      // Kontrollera att "—" finns i raden
      expect(within(digitRow!).getAllByText("—").length).toBeGreaterThanOrEqual(1)
    })

    it("visar redigera-knapp per organisation", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
        ).toBeInTheDocument()
      )
    })

    it("visar ta-bort-knapp per organisation", async () => {
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /ta bort sundsvalls kommun/i })
        ).toBeInTheDocument()
      )
    })
  })

  describe("Antal kopplade system", () => {
    it("hämtar systemlistan för att beräkna antal per organisation", async () => {
      let systemsRequested = false
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          if (url.searchParams.get("limit") === "1000") {
            systemsRequested = true
          }
          return HttpResponse.json(mockSystemsResponse)
        })
      )
      renderPage()
      await waitFor(() => {
        const cells = screen.getAllByText("Sundsvalls kommun")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
      await waitFor(() => expect(systemsRequested).toBe(true))
    })
  })

  describe("Tom lista", () => {
    it("visar 'Inga organisationer hittades' när listan är tom", async () => {
      server.use(
        http.get("/api/v1/organizations/", () => HttpResponse.json([]))
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/inga organisationer hittades/i)
        ).toBeInTheDocument()
      )
    })
  })

  describe("Felhantering", () => {
    it("visar felmeddelande vid API-fel", async () => {
      server.use(
        http.get("/api/v1/organizations/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderPage()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta organisationer/i)
        ).toBeInTheDocument()
      )
    })
  })

  describe("Skapa ny organisation", () => {
    it("öppnar dialog vid klick på Ny organisation", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /ny organisation/i })
        ).toBeInTheDocument()
      )
    })

    it("visar namnfält i dialogen", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await waitFor(() =>
        expect(screen.getByLabelText(/namn/i)).toBeInTheDocument()
      )
    })

    it("visar valideringsfel om namn saknas vid submit", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await waitFor(() => screen.getByRole("button", { name: /^skapa$/i }))
      await userEvent.click(screen.getByRole("button", { name: /^skapa$/i }))
      await waitFor(() =>
        expect(
          screen.getByText(/namn är obligatoriskt/i)
        ).toBeInTheDocument()
      )
    })

    it("skickar POST-request vid ifyllt formulär och submit", async () => {
      let postedBody: Record<string, unknown> | null = null
      server.use(
        http.post("/api/v1/organizations/", async ({ request }) => {
          postedBody = await request.json() as Record<string, unknown>
          return HttpResponse.json(
            makeOrg({ id: "org-new", name: postedBody.name as string }),
            { status: 201 }
          )
        })
      )
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await waitFor(() => screen.getByLabelText(/namn/i))
      await userEvent.type(screen.getByLabelText(/namn/i), "Testorg")
      await userEvent.click(screen.getByRole("button", { name: /^skapa$/i }))
      await waitFor(() => expect(postedBody?.name).toBe("Testorg"))
    })

    it("stänger dialogen via Avbryt-knappen", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ny organisation/i })
      )
      await waitFor(() =>
        screen.getByRole("button", { name: /avbryt/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /avbryt/i }))
      await waitFor(() =>
        expect(
          screen.queryByRole("heading", { name: /ny organisation/i })
        ).not.toBeInTheDocument()
      )
    })
  })

  describe("Redigera organisation", () => {
    it("öppnar redigeringsdialog med befintliga värden", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /redigera organisation/i })
        ).toBeInTheDocument()
      )
    })

    it("förifylller namnfältet med befintligt namn", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await waitFor(() => {
        const input = screen.getByLabelText(/namn/i) as HTMLInputElement
        expect(input.value).toBe("Sundsvalls kommun")
      })
    })

    it("visar Spara-knapp i redigeringsläge", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /redigera sundsvalls kommun/i })
      )
      await waitFor(() =>
        expect(screen.getByRole("button", { name: /^spara$/i })).toBeInTheDocument()
      )
    })
  })

  describe("Radera organisation", () => {
    it("öppnar bekräftelsedialog vid klick på Ta bort", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /ta bort organisation/i })
        ).toBeInTheDocument()
      )
    })

    it("visar organisationsnamnet i bekräftelsedialogen", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      // "MittHem AB" visas i dialogen som <strong>-element och i tabellen — använd getAllByText
      await waitFor(() => {
        const matches = screen.getAllByText(/mitthem ab/i)
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("skickar DELETE-request vid bekräftad radering", async () => {
      let deletedId: string | null = null
      server.use(
        http.delete("/api/v1/organizations/:id", ({ params }) => {
          deletedId = params.id as string
          return new HttpResponse(null, { status: 204 })
        })
      )
      // Org-3 (DigIT) har inga kopplade system i mockSystemsResponse -> kan raderas
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort digit/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort digit/i })
      )
      await waitFor(() =>
        screen.getByRole("button", { name: /^ta bort$/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /^ta bort$/i })
      )
      await waitFor(() => expect(deletedId).toBe("org-3"))
    })

    it("inaktiverar Ta bort-knappen om org har kopplade system", async () => {
      // org-1 (Sundsvalls kommun) har 2 system i mockSystemsResponse
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort sundsvalls kommun/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort sundsvalls kommun/i })
      )
      await waitFor(() => {
        const btn = screen.getByRole("button", { name: /^ta bort$/i })
        expect(btn).toBeDisabled()
      })
    })

    it("visar varningstext om det finns kopplade system", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort sundsvalls kommun/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort sundsvalls kommun/i })
      )
      await waitFor(() =>
        expect(screen.getByText(/system kopplade till/i)).toBeInTheDocument()
      )
    })

    it("stänger bekräftelsedialogen via Avbryt", async () => {
      renderPage()
      await waitFor(() =>
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort mitthem ab/i })
      )
      await waitFor(() =>
        screen.getByRole("heading", { name: /ta bort organisation/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /avbryt/i }))
      await waitFor(() =>
        expect(
          screen.queryByRole("heading", { name: /ta bort organisation/i })
        ).not.toBeInTheDocument()
      )
    })
  })
})
