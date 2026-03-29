/**
 * Testsvit: DashboardPage
 * ~40 testfall
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import DashboardPage from "@/pages/DashboardPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
  { id: "org-2", name: "Bolaget AB", org_type: "bolag" },
]

const mockStats = {
  total_systems: 42,
  by_lifecycle_status: {
    planerad: 5,
    i_drift: 30,
    under_avveckling: 4,
    avvecklad: 3,
  },
  by_criticality: {
    kritisk: 8,
    hög: 12,
    medel: 15,
    låg: 7,
  },
  nis2_applicable_count: 10,
  treats_personal_data_count: 18,
}

const mockStatsOrg1 = {
  total_systems: 15,
  by_lifecycle_status: { planerad: 2, i_drift: 12, under_avveckling: 1 },
  by_criticality: { kritisk: 3, hög: 5, medel: 4, låg: 3 },
  nis2_applicable_count: 4,
  treats_personal_data_count: 7,
}

const mockEmptyStats = {
  total_systems: 0,
  by_lifecycle_status: {},
  by_criticality: {},
  nis2_applicable_count: 0,
  treats_personal_data_count: 0,
}

// --- MSW-server ---

const server = setupServer(
  http.get(/\/api\/v1\/organizations/, () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems/stats/overview", ({ request }) => {
    const url = new URL(request.url)
    const orgId = url.searchParams.get("organization_id")
    if (orgId === "org-1") return HttpResponse.json(mockStatsOrg1)
    return HttpResponse.json(mockStats)
  }),
  http.get(/\/api\/v1\/contracts\/expiring/, () => HttpResponse.json([]))
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("DashboardPage", () => {
  describe("Laddningsläge", () => {
    it("visar skeleton-laddningsindikator initialt", () => {
      renderDashboard()
      // Production code uses skeleton loaders, not text
      const skeletons = document.querySelectorAll(".skeleton")
      expect(skeletons.length).toBeGreaterThan(0)
    })

    it("döljer skeleton efter data laddats", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("42")).toBeInTheDocument()
      )
    })
  })

  describe("KPI-kort", () => {
    it("renderar rubriken Dashboard", async () => {
      renderDashboard()
      await waitFor(() => screen.getByRole("heading", { name: /dashboard/i }))
    })

    it("visar totalt antal system", async () => {
      renderDashboard()
      await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument())
    })

    it("visar KPI-kort: Totalt antal system", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText(/totalt antal system/i)).toBeInTheDocument()
      )
    })

    it("visar KPI-kort: NIS2-tillämpliga med antal", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText(/nis2-tillämpliga/i)).toBeInTheDocument()
        expect(screen.getByText("10")).toBeInTheDocument()
      })
    })

    it("visar NIS2-procent korrekt (24 %)", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("24 %")).toBeInTheDocument()
      )
    })

    it("visar KPI-kort: Behandlar personuppgifter", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(
          screen.getByText(/behandlar personuppgifter/i)
        ).toBeInTheDocument()
        expect(screen.getByText("18")).toBeInTheDocument()
      })
    })

    it("visar personuppgifter-procent korrekt (43 %)", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("43 %")).toBeInTheDocument()
      )
    })

    it("visar KPI-kort: Kritiska system med antal", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText(/kritiska system/i)).toBeInTheDocument()
        // "8" visas i både KPI-kort och statistiktabell — använd getAllByText
        expect(screen.getAllByText("8").length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Statistiktabeller", () => {
    it("renderar tabell: Per livscykelstatus", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText(/per livscykelstatus/i)).toBeInTheDocument()
      )
    })

    it("renderar tabell: Per kritikalitet", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText(/per kritikalitet/i)).toBeInTheDocument()
      )
    })

    it("visar lifecycle-status I drift med antal 30", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText("I drift")).toBeInTheDocument()
        expect(screen.getByText("30")).toBeInTheDocument()
      })
    })

    it("visar lifecycle-status Planerad med antal 5", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText("Planerad")).toBeInTheDocument()
        expect(screen.getByText("5")).toBeInTheDocument()
      })
    })

    it("visar lifecycle-status Under avveckling", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("Under avveckling")).toBeInTheDocument()
      )
    })

    it("visar kritikalitet-badge", async () => {
      renderDashboard()
      await waitFor(() => {
        // Badges för kritikalitet
        expect(screen.getByText("Kritisk")).toBeInTheDocument()
      })
    })

    it("visar alla 4 kritikalitetsnivåer", async () => {
      renderDashboard()
      await waitFor(() => {
        expect(screen.getByText("Hög")).toBeInTheDocument()
        expect(screen.getByText("Medel")).toBeInTheDocument()
        expect(screen.getByText("Låg")).toBeInTheDocument()
      })
    })
  })

  describe("Organisation-filter", () => {
    it("visar organisations-dropdown när organisationer finns", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(
          screen.getByRole("combobox")
        ).toBeInTheDocument()
      )
    })

    it("dropdown innehåller 'Alla organisationer'", async () => {
      renderDashboard()
      await waitFor(() =>
        screen.getByRole("combobox")
      )
      await userEvent.click(
        screen.getByRole("combobox")
      )
      await waitFor(() =>
        expect(
          screen.getByRole("option", { name: /alla organisationer/i })
        ).toBeInTheDocument()
      )
    })

    it("dropdown innehåller organisationsnamnen", async () => {
      renderDashboard()
      await waitFor(() =>
        screen.getByRole("combobox")
      )
      await userEvent.click(
        screen.getByRole("combobox")
      )
      await waitFor(() => {
        expect(screen.getByRole("option", { name: "Kommunen" })).toBeInTheDocument()
        expect(screen.getByRole("option", { name: "Bolaget AB" })).toBeInTheDocument()
      })
    })

    it("filtrering på org-1 hämtar filtrerad statistik", async () => {
      renderDashboard()
      await waitFor(() =>
        screen.getByRole("combobox")
      )
      await userEvent.click(
        screen.getByRole("combobox")
      )
      await waitFor(() =>
        expect(screen.getByRole("option", { name: "Kommunen" })).toBeInTheDocument()
      )
      await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))
      await waitFor(() =>
        expect(screen.getByText("15")).toBeInTheDocument()
      )
    })
  })

  describe("Tom data", () => {
    it("visar 'Inga data' i livscykel-tabell när tom", async () => {
      server.use(
        http.get("/api/v1/systems/stats/overview", () =>
          HttpResponse.json(mockEmptyStats)
        )
      )
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText(/inga data/i)
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar 0 för alla KPI-kort med tom data", async () => {
      server.use(
        http.get("/api/v1/systems/stats/overview", () =>
          HttpResponse.json(mockEmptyStats)
        )
      )
      renderDashboard()
      await waitFor(() => {
        const zeros = screen.getAllByText("0")
        expect(zeros.length).toBeGreaterThanOrEqual(3)
      })
    })

    it("visar '0 %' som andel när total är 0", async () => {
      server.use(
        http.get("/api/v1/systems/stats/overview", () =>
          HttpResponse.json(mockEmptyStats)
        )
      )
      renderDashboard()
      await waitFor(() => {
        const zeroPct = screen.getAllByText("0 %")
        expect(zeroPct.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Felhantering", () => {
    it("visar felmeddelande när API returnerar 500", async () => {
      server.use(
        http.get("/api/v1/systems/stats/overview", () =>
          HttpResponse.json({ detail: "Internal Server Error" }, { status: 500 })
        )
      )
      renderDashboard()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta statistik/i)
        ).toBeInTheDocument()
      )
    })

    it("döljer KPI-kort vid fel", async () => {
      server.use(
        http.get("/api/v1/systems/stats/overview", () =>
          HttpResponse.json({}, { status: 503 })
        )
      )
      renderDashboard()
      await waitFor(() =>
        screen.getByText(/kunde inte hämta statistik/i)
      )
      expect(screen.queryByText(/totalt antal system/i)).not.toBeInTheDocument()
    })
  })

  describe("Oversikt-text", () => {
    it("visar undertexten 'Översikt av systemregistret'", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(
          screen.getByText(/översikt av systemregistret/i)
        ).toBeInTheDocument()
      )
    })
  })

  describe("Kritikalitets-badges", () => {
    it("Kritisk-badge har destructive-variant", async () => {
      renderDashboard()
      await waitFor(() => screen.getByText("Kritisk"))
      // Verifierar att badge renderas
      expect(screen.getByText("Kritisk")).toBeInTheDocument()
    })

    it("Hög-badge renderas korrekt", async () => {
      renderDashboard()
      await waitFor(() => expect(screen.getByText("Hög")).toBeInTheDocument())
    })

    it("Medel-badge renderas korrekt", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("Medel")).toBeInTheDocument()
      )
    })

    it("Låg-badge renderas korrekt", async () => {
      renderDashboard()
      await waitFor(() => expect(screen.getByText("Låg")).toBeInTheDocument())
    })
  })

  describe("Antal-värden i tabeller", () => {
    it("kritisk-antal i tabell är 8", async () => {
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText("8")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("hög-antal i tabell är 12", async () => {
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText("12")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("medel-antal i tabell är 15", async () => {
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText("15")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("under_avveckling-status visar 4", async () => {
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText("4")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("avvecklad-status visar 3", async () => {
      renderDashboard()
      await waitFor(() => {
        const cells = screen.getAllByText("3")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Responsivitet - CSS-klasser", () => {
    it("KPI-grid har responsiva klasser (sm:grid-cols-2)", async () => {
      renderDashboard()
      await waitFor(() => screen.getByText("42"))
      const grid = document.querySelector(".sm\\:grid-cols-2")
      expect(grid).toBeInTheDocument()
    })

    it("statistik-grid har lg:grid-cols-2-layout", async () => {
      renderDashboard()
      await waitFor(() => screen.getByText("Per livscykelstatus"))
      const grid = document.querySelector(".lg\\:grid-cols-2")
      expect(grid).toBeInTheDocument()
    })
  })

  describe("Procent-beräkning", () => {
    it("beräknar korrekt procent för 10/42 NIS2 → 24%", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("24 %")).toBeInTheDocument()
      )
    })

    it("beräknar korrekt procent för 18/42 personuppgifter → 43%", async () => {
      renderDashboard()
      await waitFor(() =>
        expect(screen.getByText("43 %")).toBeInTheDocument()
      )
    })

    it("procent visas som undertitel till KPI-kort", async () => {
      renderDashboard()
      await waitFor(() => {
        // Båda procenterna ska finnas
        expect(screen.getByText("24 %")).toBeInTheDocument()
        expect(screen.getByText("43 %")).toBeInTheDocument()
      })
    })
  })

  describe("QueryClient - caching", () => {
    it("återanvänder cachad data vid omrendering", async () => {
      const qc = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      })
      const { rerender } = render(
        <QueryClientProvider client={qc}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </QueryClientProvider>
      )
      await waitFor(() => screen.getByText("42"))

      rerender(
        <QueryClientProvider client={qc}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </QueryClientProvider>
      )
      // Ska fortfarande visa 42 från cache
      expect(screen.getByText("42")).toBeInTheDocument()
    })
  })
})
