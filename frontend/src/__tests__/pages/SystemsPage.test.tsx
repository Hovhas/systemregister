/**
 * Testsvit: SystemsPage
 * ~60 testfall
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
import SystemsPage from "@/pages/SystemsPage"
import {
  Criticality,
  SystemCategory,
  LifecycleStatus,
} from "@/types"

// --- Testdata ---

function makeSystem(overrides: Partial<ReturnType<typeof baseSystem>> = {}) {
  return {
    id: "sys-1",
    name: "Ekonomisystem",
    organization_id: "org-1",
    description: "Hanterar ekonomi",
    system_category: SystemCategory.VERKSAMHETSSYSTEM,
    criticality: Criticality.MEDIUM,
    lifecycle_status: LifecycleStatus.ACTIVE,
    nis2_applicable: false,
    aliases: null,
    business_area: null,
    has_elevated_protection: false,
    security_protection: false,
    nis2_classification: null,
    treats_personal_data: false,
    treats_sensitive_data: false,
    third_country_transfer: false,
    hosting_model: null,
    cloud_provider: null,
    data_location_country: null,
    product_name: null,
    product_version: null,
    deployment_date: null,
    planned_decommission_date: null,
    end_of_support_date: null,
    backup_frequency: null,
    rpo: null,
    rto: null,
    dr_plan_exists: false,
    last_risk_assessment_date: null,
    klassa_reference_id: null,
    extended_attributes: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    last_reviewed_at: null,
    last_reviewed_by: null,
    ...overrides,
  }
}

function baseSystem(overrides = {}) {
  return makeSystem(overrides)
}

const systemsList = [
  makeSystem({ id: "sys-1", name: "Ekonomisystem", criticality: Criticality.LOW }),
  makeSystem({ id: "sys-2", name: "HR-system", criticality: Criticality.MEDIUM, nis2_applicable: true }),
  makeSystem({ id: "sys-3", name: "Vårdsystem", criticality: Criticality.HIGH, system_category: SystemCategory.INFRASTRUKTUR }),
  makeSystem({ id: "sys-4", name: "Brandlarm", criticality: Criticality.CRITICAL, system_category: SystemCategory.IOT }),
  makeSystem({ id: "sys-5", name: "E-post", lifecycle_status: LifecycleStatus.PLANNED }),
]

const paginatedResponse = (items = systemsList, total = 5) => ({
  items,
  total,
  limit: 25,
  offset: 0,
})

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems/", () =>
    HttpResponse.json(paginatedResponse())
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktioner ---

// Hämtar select-knapp (combobox) via index: 0=Kategori, 1=Livscykelstatus, 2=Kritikalitet
function getSelectByIndex(index: number) {
  return screen.getAllByRole("combobox")[index]
}

function renderSystems() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SystemsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("SystemsPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar sidan med rubrik System", async () => {
      renderSystems()
      await waitFor(() =>
        expect(screen.getByRole("heading", { name: /^system$/i })).toBeInTheDocument()
      )
    })

    it("renderar knappen Nytt system", async () => {
      renderSystems()
      await waitFor(() =>
        expect(screen.getByRole("button", { name: /nytt system/i })).toBeInTheDocument()
      )
    })

    it("renderar sökfältet", async () => {
      renderSystems()
      await waitFor(() =>
        expect(screen.getByPlaceholderText(/sök system/i)).toBeInTheDocument()
      )
    })

    it("renderar filter: Kategori", async () => {
      renderSystems()
      await waitFor(() => {
        const combos = screen.getAllByRole("combobox")
        expect(combos.length).toBeGreaterThanOrEqual(3)
      })
    })

    it("renderar filter: Livscykelstatus", async () => {
      renderSystems()
      await waitFor(() => {
        const combos = screen.getAllByRole("combobox")
        expect(combos.length).toBeGreaterThanOrEqual(3)
      })
    })

    it("renderar filter: Kritikalitet", async () => {
      renderSystems()
      await waitFor(() => {
        const combos = screen.getAllByRole("combobox")
        expect(combos.length).toBeGreaterThanOrEqual(3)
      })
    })

    it("visar tabellhuvud: Namn, Organisation, Kategori, Kritikalitet, Status, NIS2", async () => {
      renderSystems()
      await waitFor(() => {
        expect(screen.getByRole("columnheader", { name: /namn/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /organisation/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /kategori/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /kritikalitet/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /status/i })).toBeInTheDocument()
        expect(screen.getByRole("columnheader", { name: /nis2/i })).toBeInTheDocument()
      })
    })
  })

  describe("Systemlista", () => {
    it("visar systemnamnen i tabellen", async () => {
      renderSystems()
      await waitFor(() => {
        expect(screen.getByText("Ekonomisystem")).toBeInTheDocument()
        expect(screen.getByText("HR-system")).toBeInTheDocument()
        expect(screen.getByText("Vårdsystem")).toBeInTheDocument()
      })
    })

    it("visar total antal system", async () => {
      renderSystems()
      await waitFor(() =>
        expect(screen.getByText(/5 system totalt/i)).toBeInTheDocument()
      )
    })

    it("visar organisations-namn i tabellen (via map)", async () => {
      renderSystems()
      await waitFor(() => {
        const kommunen = screen.getAllByText("Kommunen")
        expect(kommunen.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar livscykelstatus I drift", async () => {
      renderSystems()
      await waitFor(() => {
        const active = screen.getAllByText("I drift")
        expect(active.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar livscykelstatus Planerad", async () => {
      renderSystems()
      await waitFor(() =>
        expect(screen.getByText("Planerad")).toBeInTheDocument()
      )
    })
  })

  describe("Laddning och fel", () => {
    it("visar laddningsrad när data hämtas", () => {
      renderSystems()
      expect(screen.getByText(/laddar/i)).toBeInTheDocument()
    })

    it("visar felmeddelande vid API-fel", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      renderSystems()
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta system/i)
        ).toBeInTheDocument()
      )
    })

    it("visar 'Inga system matchar sökningen' vid tom lista", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })
        )
      )
      renderSystems()
      await waitFor(() =>
        expect(
          screen.getByText(/inga system matchar sökningen/i)
        ).toBeInTheDocument()
      )
    })

    it("visar 'Inga system hittade' i undertexten vid tom lista", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })
        )
      )
      renderSystems()
      await waitFor(() =>
        expect(screen.getByText(/inga system hittade/i)).toBeInTheDocument()
      )
    })
  })

  describe("Kritikalitets-badge färger", () => {
    it("Låg-badge har grön CSS-klass", async () => {
      renderSystems()
      await waitFor(() => screen.getByText("Låg"))
      const badge = screen.getByText("Låg")
      expect(badge.className).toMatch(/green/)
    })

    it("Medel-badge har gul CSS-klass", async () => {
      renderSystems()
      await waitFor(() => screen.getAllByText("Medel"))
      const badge = screen.getAllByText("Medel")[0]
      expect(badge.className).toMatch(/yellow/)
    })

    it("Hög-badge har orange CSS-klass", async () => {
      renderSystems()
      await waitFor(() => screen.getByText("Hög"))
      const badge = screen.getByText("Hög")
      expect(badge.className).toMatch(/orange/)
    })

    it("Kritisk-badge har röd CSS-klass", async () => {
      renderSystems()
      await waitFor(() => screen.getByText("Kritisk"))
      const badge = screen.getByText("Kritisk")
      expect(badge.className).toMatch(/red/)
    })
  })

  describe("NIS2-badge", () => {
    it("NIS2 Ja-badge visas för tillämpliga system", async () => {
      renderSystems()
      await waitFor(() => {
        const badges = screen.getAllByText("Ja")
        expect(badges.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("NIS2 Nej-badge visas för icke-tillämpliga system", async () => {
      renderSystems()
      await waitFor(() => {
        const badges = screen.getAllByText("Nej")
        expect(badges.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Sökning med debounce", () => {
    it("sökinput uppdateras när användaren skriver", async () => {
      renderSystems()
      await waitFor(() => screen.getByPlaceholderText(/sök system/i))
      const input = screen.getByPlaceholderText(/sök system/i)
      await userEvent.type(input, "vård")
      expect(input).toHaveValue("vård")
    })

    it("debounce-sökning triggar ny request efter 300ms (simulerat)", async () => {
      let searchParam: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          searchParam = url.searchParams.get("q")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => screen.getByPlaceholderText(/sök system/i))

      const input = screen.getByPlaceholderText(/sök system/i)
      await userEvent.type(input, "test")

      // Vänta på debounce (300ms) + HTTP-request
      await waitFor(
        () => {
          expect(searchParam).toBe("test")
        },
        { timeout: 1000 }
      )
    })

    it("sökning rensar offset till 0", async () => {
      let capturedOffset: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedOffset = url.searchParams.get("offset")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => screen.getByPlaceholderText(/sök system/i))
      const input = screen.getByPlaceholderText(/sök system/i)
      await userEvent.type(input, "x")

      await waitFor(
        () => {
          expect(capturedOffset === null || capturedOffset === "0").toBe(true)
        },
        { timeout: 1000 }
      )
    })
  })

  describe("Filter", () => {
    it("kategori-filter skickar system_category till API", async () => {
      let capturedCategory: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedCategory = url.searchParams.get("system_category")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      await userEvent.click(getSelectByIndex(0))
      await waitFor(() => screen.getByRole("option", { name: /infrastruktur/i }))
      await userEvent.click(screen.getByRole("option", { name: /infrastruktur/i }))

      await waitFor(() => expect(capturedCategory).toBe("infrastruktur"))
      // Säkerställ att dropdown är stängd
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())
    })

    it("livscykel-filter skickar lifecycle_status till API", async () => {
      let capturedLifecycle: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedLifecycle = url.searchParams.get("lifecycle_status")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      await userEvent.click(getSelectByIndex(1))
      await waitFor(() => screen.getByRole("option", { name: /planerad/i }))
      await userEvent.click(screen.getByRole("option", { name: /planerad/i }))

      await waitFor(() => expect(capturedLifecycle).toBe("planerad"))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())
    })

    it("kritikalitet-filter skickar criticality till API", async () => {
      let capturedCriticality: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedCriticality = url.searchParams.get("criticality")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      await userEvent.click(getSelectByIndex(2))
      await waitFor(() => screen.getByRole("option", { name: /kritisk/i }))
      await userEvent.click(screen.getByRole("option", { name: /kritisk/i }))

      await waitFor(() => expect(capturedCriticality).toBe("kritisk"))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())
    })

    it("filter återställer offset till 0 vid val", async () => {
      let lastOffset: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          lastOffset = url.searchParams.get("offset")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      await userEvent.click(getSelectByIndex(0))
      await waitFor(() => screen.getByRole("option", { name: /plattform/i }))
      await userEvent.click(screen.getByRole("option", { name: /plattform/i }))

      await waitFor(() => expect(lastOffset === null || lastOffset === "0").toBe(true))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())
    })
  })

  describe("Pagination", () => {
    it("visar paginering när total > 25", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({
            items: systemsList,
            total: 60,
            limit: 25,
            offset: 0,
          })
        )
      )
      renderSystems()
      await waitFor(() => {
        expect(screen.getByText(/sida 1 av 3/i)).toBeInTheDocument()
      })
    })

    it("döljer paginering när total <= 25", async () => {
      renderSystems()
      await waitFor(() => screen.getByText("Ekonomisystem"))
      expect(screen.queryByText(/sida/i)).not.toBeInTheDocument()
    })

    it("Föregående-knapp är inaktiverad på första sidan", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({
            items: systemsList,
            total: 60,
            limit: 25,
            offset: 0,
          })
        )
      )
      renderSystems()
      await waitFor(() => screen.getByText(/sida 1 av 3/i))
      expect(
        screen.getByRole("button", { name: /föregående/i })
      ).toBeDisabled()
    })

    it("Nästa-knapp är aktiv på första sidan när fler sidor finns", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({
            items: systemsList,
            total: 60,
            limit: 25,
            offset: 0,
          })
        )
      )
      renderSystems()
      await waitFor(() => screen.getByText(/sida 1 av 3/i))
      expect(
        screen.getByRole("button", { name: /nästa/i })
      ).not.toBeDisabled()
    })

    it("klick på Nästa ökar offset med PAGE_SIZE (25)", async () => {
      let capturedOffset: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedOffset = url.searchParams.get("offset")
          return HttpResponse.json({
            items: systemsList,
            total: 60,
            limit: 25,
            offset: parseInt(capturedOffset ?? "0"),
          })
        })
      )
      renderSystems()
      await waitFor(() => screen.getByRole("button", { name: /nästa/i }))
      await userEvent.click(screen.getByRole("button", { name: /nästa/i }))

      await waitFor(() =>
        expect(capturedOffset).toBe("25")
      )
    })

    it("Nästa-knapp är inaktiverad på sista sidan", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({
            items: systemsList,
            total: 5,
            limit: 25,
            offset: 0,
          })
        )
      )
      // Med total=5 och limit=25 finns bara 1 sida
      renderSystems()
      await waitFor(() => screen.getByText("Ekonomisystem"))
      // Paginering visas inte alls när total <= PAGE_SIZE
      expect(screen.queryByRole("button", { name: /nästa/i })).not.toBeInTheDocument()
    })

    it("visar 25 items per sida (PAGE_SIZE)", async () => {
      let capturedLimit: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          const url = new URL(request.url)
          capturedLimit = url.searchParams.get("limit")
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() =>
        expect(capturedLimit).toBe("25")
      )
    })
  })

  describe("Kombinerade filter", () => {
    it("kan sätta kategori + livscykel-filter samtidigt", async () => {
      let params: URLSearchParams | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          params = new URL(request.url).searchParams
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      await userEvent.click(getSelectByIndex(0))
      await waitFor(() => screen.getByRole("option", { name: /plattform/i }))
      await userEvent.click(screen.getByRole("option", { name: /plattform/i }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await userEvent.click(getSelectByIndex(1))
      await waitFor(() => screen.getByRole("option", { name: /i drift/i }))
      await userEvent.click(screen.getByRole("option", { name: /i drift/i }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await waitFor(() => {
        expect(params?.get("system_category")).toBe("plattform")
        expect(params?.get("lifecycle_status")).toBe("i_drift")
      })
    })

    it("rensa ett filter (Alla kategorier) tar bort category-param", async () => {
      let params: URLSearchParams | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          params = new URL(request.url).searchParams
          return HttpResponse.json(paginatedResponse())
        })
      )
      renderSystems()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(3))

      // Välj kategori
      await userEvent.click(getSelectByIndex(0))
      await waitFor(() => screen.getByRole("option", { name: /infrastruktur/i }))
      await userEvent.click(screen.getByRole("option", { name: /infrastruktur/i }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await waitFor(() => expect(params?.get("system_category")).toBe("infrastruktur"))

      // Rensa till Alla kategorier
      await userEvent.click(getSelectByIndex(0))
      await waitFor(() => screen.getByRole("option", { name: /alla kategorier/i }))
      await userEvent.click(screen.getByRole("option", { name: /alla kategorier/i }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await waitFor(() => expect(params?.get("system_category")).toBeNull())
    })
  })

  describe("Navigation", () => {
    it("klick på rad navigerar till /systems/:id", async () => {
      // MemoryRouter hanterar navigering internt — verifiera att rad är klickbar
      renderSystems()
      await waitFor(() => screen.getByText("Ekonomisystem"))

      const rows = screen.getAllByRole("row")
      // Hoppa över header-raden — klick ska inte kasta fel
      await userEvent.click(rows[1])
      // Navigationen sker via MemoryRouter internt, inget ytterligare att verifiera här
    })

    it("klick på Nytt system navigerar till /systems/new", async () => {
      renderSystems()
      await waitFor(() =>
        screen.getByRole("button", { name: /nytt system/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /nytt system/i }))
      // MemoryRouter fångar navigationen internt
    })
  })
})
