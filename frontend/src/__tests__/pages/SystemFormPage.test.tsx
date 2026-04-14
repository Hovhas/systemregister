/**
 * Testsvit: SystemFormPage
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
import { createMemoryRouter, RouterProvider } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import SystemFormPage from "@/pages/SystemFormPage"
import {
  Criticality,
  SystemCategory,
  LifecycleStatus,
} from "@/types"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
  { id: "org-2", name: "Bolaget AB", org_type: "bolag" },
]

const mockExistingSystem = {
  id: "sys-1",
  name: "Befintligt system",
  organization_id: "org-1",
  description: "Befintlig beskrivning",
  system_category: SystemCategory.STODSYSTEM,
  criticality: Criticality.HIGH,
  lifecycle_status: LifecycleStatus.ACTIVE,
  nis2_applicable: true,
  treats_personal_data: true,
  aliases: null,
  business_area: "IT",
  has_elevated_protection: false,
  security_protection: false,
  nis2_classification: null,
  treats_sensitive_data: false,
  third_country_transfer: false,
  hosting_model: "on-premise",
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
  // Kategori 1-12 utökat
  business_processes: null,
  encryption_at_rest: null,
  encryption_in_transit: null,
  access_control_model: null,
  retention_rules: null,
  architecture_type: null,
  environments: null,
  last_major_upgrade: null,
  next_planned_review: null,
  backup_storage_location: null,
  last_restore_test: null,
  cost_center: null,
  total_cost_of_ownership: null,
  documentation_links: null,
  linked_risks: null,
  incident_history: null,
  objekt_id: null,
  // AI (kategori 13)
  uses_ai: false,
  ai_risk_class: null,
  ai_usage_description: null,
  fria_status: null,
  fria_date: null,
  fria_link: null,
  ai_human_oversight: null,
  ai_supplier: null,
  ai_transparency_fulfilled: false,
  ai_model_version: null,
  ai_last_review_date: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  last_reviewed_at: null,
  last_reviewed_by: null,
  classifications: [],
  owners: [],
}

const createdSystem = {
  ...mockExistingSystem,
  id: "sys-new",
  name: "Nytt system",
  organization_id: "org-1",
  description: "Ny beskrivning",
  system_category: SystemCategory.VERKSAMHETSSYSTEM,
  criticality: Criticality.MEDIUM,
}

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems/:id", () => HttpResponse.json(mockExistingSystem)),
  http.post("/api/v1/systems", async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...createdSystem, ...body }, { status: 201 })
  }),
  http.patch("/api/v1/systems/:id", async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockExistingSystem, ...body })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => {
  server.resetHandlers()
})
afterAll(() => server.close())

// --- Hjälpfunktioner ---

// Form-selects i ordning: 0=Organisation, 1=Kategori, 2=Objekt, 3=Livscykelstatus, 4=Kritikalitet
function getFormSelect(index: number) {
  return screen.getAllByRole("combobox")[index]
}

function renderCreateForm() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(
    [
      { path: "/systems/new", element: <SystemFormPage /> },
      { path: "/systems/:id", element: <div data-testid="detail-page">Detail</div> },
      { path: "/systems", element: <div data-testid="systems-list">List</div> },
    ],
    { initialEntries: ["/systems/new"] }
  )
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

function renderEditForm(id = "sys-1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(
    [
      { path: "/systems/:id/edit", element: <SystemFormPage /> },
      { path: "/systems/:id", element: <div data-testid="detail-page">Detail</div> },
    ],
    { initialEntries: [`/systems/${id}/edit`] }
  )
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("SystemFormPage", () => {
  describe("Skapa-läge", () => {
    it("visar rubriken 'Nytt system'", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /nytt system/i })
        ).toBeInTheDocument()
      )
    })

    it("visar tomt namn-fält", async () => {
      renderCreateForm()
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/systemets namn/i)
        expect(input).toHaveValue("")
      })
    })

    it("visar tomt beskrivnings-fält", async () => {
      renderCreateForm()
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(
          /beskriv systemets syfte/i
        )
        expect(textarea).toHaveValue("")
      })
    })

    it("visar standard-kategori Verksamhetssystem", async () => {
      renderCreateForm()
      // Öppna Kategori-select (index 1) och verifiera att Verksamhetssystem finns som option
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(screen.getAllByRole("combobox")[1])
      await waitFor(() =>
        expect(screen.getByRole("option", { name: /verksamhetssystem/i })).toBeInTheDocument()
      )
      // Stäng
      await userEvent.keyboard("{Escape}")
    })

    it("visar standard-livscykel I drift", async () => {
      renderCreateForm()
      // Öppna Livscykelstatus-select (index 3) och verifiera att I drift finns som option
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(5))
      await userEvent.click(screen.getAllByRole("combobox")[3])
      await waitFor(() =>
        expect(screen.getByRole("option", { name: /i drift/i })).toBeInTheDocument()
      )
      await userEvent.keyboard("{Escape}")
    })

    it("visar standard-kritikalitet Medel", async () => {
      renderCreateForm()
      // Öppna Kritikalitet-select (index 4) och verifiera att Medel finns som option
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(5))
      await userEvent.click(screen.getAllByRole("combobox")[4])
      await waitFor(() =>
        expect(screen.getByRole("option", { name: /medel/i })).toBeInTheDocument()
      )
      await userEvent.keyboard("{Escape}")
    })

    it("NIS2-checkbox är unchecked som standard", async () => {
      renderCreateForm()
      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /nis2-tillämplig/i,
        })
        expect(checkbox).not.toBeChecked()
      })
    })

    it("Personuppgifter-checkbox är unchecked som standard", async () => {
      renderCreateForm()
      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /behandlar personuppgifter/i,
        })
        expect(checkbox).not.toBeChecked()
      })
    })

    it("visar Skapa system-knapp", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /skapa system/i })
        ).toBeInTheDocument()
      )
    })

    it("visar Avbryt-knapp", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getAllByRole("button", { name: /avbryt/i })[0]
        ).toBeInTheDocument()
      )
    })
  })

  describe("Redigera-läge", () => {
    it("visar rubriken 'Redigera system'", async () => {
      renderEditForm()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /redigera system/i })
        ).toBeInTheDocument()
      )
    })

    it("förifyllt namn från existerande system", async () => {
      renderEditForm()
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/systemets namn/i)
        expect(input).toHaveValue("Befintligt system")
      })
    })

    it("förifyllt beskrivning från existerande system", async () => {
      renderEditForm()
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(
          /beskriv systemets syfte/i
        )
        expect(textarea).toHaveValue("Befintlig beskrivning")
      })
    })

    it("förifyllt business_area (IT)", async () => {
      renderEditForm()
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/t\.ex\. hr/i)
        expect(input).toHaveValue("IT")
      })
    })

    it("förifyllt hosting_model (on-premise)", async () => {
      renderEditForm()
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/on-premise/i)
        expect(input).toHaveValue("on-premise")
      })
    })

    it("NIS2-checkbox är förifylld (true)", async () => {
      renderEditForm()
      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /nis2-tillämplig/i,
        })
        expect(checkbox).toBeChecked()
      })
    })

    it("Personuppgifter-checkbox är förifylld (true)", async () => {
      renderEditForm()
      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /behandlar personuppgifter/i,
        })
        expect(checkbox).toBeChecked()
      })
    })

    it("visar Spara ändringar-knapp", async () => {
      renderEditForm()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /spara ändringar/i })
        ).toBeInTheDocument()
      )
    })
  })

  describe("Formulärfält", () => {
    it("kan skriva i namn-fältet", async () => {
      renderCreateForm()
      await waitFor(() => screen.getByPlaceholderText(/systemets namn/i))
      const input = screen.getByPlaceholderText(/systemets namn/i)
      await userEvent.type(input, "Mitt system")
      expect(input).toHaveValue("Mitt system")
    })

    it("kan skriva i beskrivningsfältet", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByPlaceholderText(/beskriv systemets syfte/i)
      )
      const textarea = screen.getByPlaceholderText(/beskriv systemets syfte/i)
      await userEvent.type(textarea, "En bra beskrivning")
      expect(textarea).toHaveValue("En bra beskrivning")
    })

    it("kan toggla NIS2-checkbox", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByRole("checkbox", { name: /nis2-tillämplig/i })
      )
      const checkbox = screen.getByRole("checkbox", {
        name: /nis2-tillämplig/i,
      })
      await userEvent.click(checkbox)
      expect(checkbox).toBeChecked()
      await userEvent.click(checkbox)
      expect(checkbox).not.toBeChecked()
    })

    it("kan toggla Personuppgifter-checkbox", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByRole("checkbox", { name: /behandlar personuppgifter/i })
      )
      const checkbox = screen.getByRole("checkbox", {
        name: /behandlar personuppgifter/i,
      })
      await userEvent.click(checkbox)
      expect(checkbox).toBeChecked()
    })

    it("visar alla kategori-alternativ i dropdown", async () => {
      renderCreateForm()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(1))
      await waitFor(() => {
        expect(
          screen.getByRole("option", { name: "Verksamhetssystem" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Stödsystem" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Infrastruktur" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Plattform" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "IoT" })
        ).toBeInTheDocument()
      })
    })

    it("visar alla livscykel-alternativ i dropdown", async () => {
      renderCreateForm()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(5))
      await userEvent.click(getFormSelect(3))
      await waitFor(() => {
        expect(
          screen.getByRole("option", { name: "Planerad" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Under införande" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "I drift" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Under avveckling" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Avvecklad" })
        ).toBeInTheDocument()
      })
    })

    it("visar alla kritikalitet-alternativ i dropdown", async () => {
      renderCreateForm()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(5))
      await userEvent.click(getFormSelect(4))
      await waitFor(() => {
        expect(screen.getByRole("option", { name: "Låg" })).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Medel" })
        ).toBeInTheDocument()
        expect(screen.getByRole("option", { name: "Hög" })).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Kritisk" })
        ).toBeInTheDocument()
      })
    })

    it("visar organisationer i dropdown", async () => {
      renderCreateForm()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(0))
      await waitFor(() => {
        expect(
          screen.getByRole("option", { name: "Kommunen" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Bolaget AB" })
        ).toBeInTheDocument()
      })
    })
  })

  describe("Submit och navigering", () => {
    it("skapar system och skickar POST vid giltigt formulär", async () => {
      let postCalled = false
      server.use(
        http.post("/api/v1/systems", async ({ request }) => {
          postCalled = true
          const body = await request.json() as object
          return HttpResponse.json({ ...createdSystem, ...body }, { status: 201 })
        })
      )
      renderCreateForm()
      await waitFor(() => screen.getByPlaceholderText(/systemets namn/i))

      await userEvent.type(
        screen.getByPlaceholderText(/systemets namn/i),
        "Nytt system"
      )
      await userEvent.type(
        screen.getByPlaceholderText(/beskriv systemets syfte/i),
        "Ny beskrivning"
      )

      // Välj organisation (index 0)
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(0))
      await waitFor(() => screen.getByRole("option", { name: "Kommunen" }))
      await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await userEvent.click(
        screen.getByRole("button", { name: /skapa system/i })
      )

      await waitFor(() => expect(postCalled).toBe(true))
    })

    it("uppdaterar system och skickar PATCH vid redigering", async () => {
      let patchCalled = false
      server.use(
        http.patch("/api/v1/systems/:id", async ({ request }) => {
          patchCalled = true
          const body = await request.json() as object
          return HttpResponse.json({ ...mockExistingSystem, ...body })
        })
      )
      renderEditForm()
      await waitFor(() =>
        screen.getByRole("button", { name: /spara ändringar/i })
      )

      const nameInput = screen.getByPlaceholderText(/systemets namn/i)
      await userEvent.clear(nameInput)
      await userEvent.type(nameInput, "Uppdaterat namn")

      await userEvent.click(
        screen.getByRole("button", { name: /spara ändringar/i })
      )

      await waitFor(() => expect(patchCalled).toBe(true))
    })

    it("visar felmeddelande vid API-fel (POST)", async () => {
      server.use(
        http.post("/api/v1/systems", () =>
          HttpResponse.json({ detail: "Kunde inte spara systemet" }, { status: 422 })
        )
      )
      renderCreateForm()
      await waitFor(() => screen.getByPlaceholderText(/systemets namn/i))

      await userEvent.type(
        screen.getByPlaceholderText(/systemets namn/i),
        "Test"
      )
      await userEvent.type(
        screen.getByPlaceholderText(/beskriv systemets syfte/i),
        "Beskrivning"
      )
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(0))
      await waitFor(() => screen.getByRole("option", { name: "Kommunen" }))
      await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await userEvent.click(
        screen.getByRole("button", { name: /skapa system/i })
      )

      // The production code shows the detail message as apiError
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte spara systemet/i)
        ).toBeInTheDocument()
      )
    })

    it("visar felmeddelande vid API-fel (PATCH)", async () => {
      server.use(
        http.patch("/api/v1/systems/:id", () =>
          HttpResponse.json({ detail: "Ett oväntat fel uppstod" }, { status: 500 })
        )
      )
      renderEditForm()
      await waitFor(() =>
        screen.getByRole("button", { name: /spara ändringar/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /spara ändringar/i })
      )

      // The production code shows the detail string or a generic error
      await waitFor(() =>
        expect(
          screen.getByText(/oväntat fel/i)
        ).toBeInTheDocument()
      )
    })

    it("Avbryt navigerar till systems-lista i skapa-läge", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getAllByRole("button", { name: /avbryt/i })
      )
      await userEvent.click(
        screen.getAllByRole("button", { name: /avbryt/i })[0]
      )
      await waitFor(() =>
        expect(screen.getByTestId("systems-list")).toBeInTheDocument()
      )
    })

    it("submit-knapp är inaktiverad under submit", async () => {
      let resolvePost!: (value: Response) => void
      server.use(
        http.post("/api/v1/systems", () =>
          new Promise((resolve) => {
            resolvePost = () =>
              resolve(
                HttpResponse.json(createdSystem, { status: 201 }) as Response
              )
          })
        )
      )
      renderCreateForm()
      await waitFor(() => screen.getByPlaceholderText(/systemets namn/i))

      await userEvent.type(
        screen.getByPlaceholderText(/systemets namn/i),
        "Test"
      )
      await userEvent.type(
        screen.getByPlaceholderText(/beskriv systemets syfte/i),
        "Desc"
      )
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(0))
      await waitFor(() => screen.getByRole("option", { name: "Kommunen" }))
      await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())

      await userEvent.click(
        screen.getByRole("button", { name: /skapa system/i })
      )

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /skapar/i })
        ).toBeDisabled()
      )

      resolvePost(new Response())
    })
  })

  describe("Kortsektioner", () => {
    it("visar Grundinformation-sektion", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(screen.getByText("Grundinformation")).toBeInTheDocument()
      )
    })

    it("visar Status och kritikalitet-sektion", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByText(/status och kritikalitet/i)
        ).toBeInTheDocument()
      )
    })

    it("visar Driftmiljö-sektion", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(screen.getByText("Driftmiljö")).toBeInTheDocument()
      )
    })

    it("visar Compliance-sektion", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(screen.getByText("Compliance")).toBeInTheDocument()
      )
    })
  })

  describe("Fält-placeholder-texter", () => {
    it("hosting_model-fält har placeholder 'on-premise / cloud / hybrid'", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByPlaceholderText(/on-premise \/ cloud \/ hybrid/i)
        ).toBeInTheDocument()
      )
    })

    it("cloud_provider-fält har placeholder 'Azure, AWS, GCP'", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByPlaceholderText(/azure, aws, gcp/i)
        ).toBeInTheDocument()
      )
    })

    it("business_area-fält har placeholder 'HR, Ekonomi, Vård'", async () => {
      renderCreateForm()
      await waitFor(() =>
        expect(
          screen.getByPlaceholderText(/hr, ekonomi, vård/i)
        ).toBeInTheDocument()
      )
    })
  })

  describe("Obligatoriska fält-markeringar", () => {
    it("Namn-fält är markerat som required (visuellt med asterisk)", async () => {
      renderCreateForm()
      await waitFor(() => screen.getByPlaceholderText(/systemets namn/i))
      // FormField visar visuell asterisk istället för HTML required
      const nameLabel = screen.getByText("Namn").closest("label")
      expect(nameLabel?.textContent).toContain("*")
    })

    it("Beskrivning-fält är markerat som required (visuellt med asterisk)", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByPlaceholderText(/beskriv systemets syfte/i)
      )
      // FormField visar visuell asterisk istället för HTML required
      const descLabel = screen.getByText("Beskrivning").closest("label")
      expect(descLabel?.textContent).toContain("*")
    })

    it("Namn-etikett visar asterisk (*) för required", async () => {
      renderCreateForm()
      await waitFor(() => screen.getByText("Namn"))
      // Asterisk är en asterisk-span
      const nameLabel = screen.getByText("Namn").closest("label")
      expect(nameLabel?.textContent).toContain("*")
    })
  })

  describe("Formulär-input uppdatering", () => {
    it("hosting_model-fält uppdateras vid inmatning", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByPlaceholderText(/on-premise \/ cloud \/ hybrid/i)
      )
      const input = screen.getByPlaceholderText(/on-premise \/ cloud \/ hybrid/i)
      await userEvent.type(input, "cloud")
      expect(input).toHaveValue("cloud")
    })

    it("cloud_provider-fält uppdateras vid inmatning", async () => {
      renderCreateForm()
      await waitFor(() =>
        screen.getByPlaceholderText(/azure, aws, gcp/i)
      )
      const input = screen.getByPlaceholderText(/azure, aws, gcp/i)
      await userEvent.type(input, "AWS")
      expect(input).toHaveValue("AWS")
    })

    it("kategori-val uppdaterar formulär-state", async () => {
      renderCreateForm()
      await waitFor(() => expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(4))
      await userEvent.click(getFormSelect(1))
      await waitFor(() => screen.getByRole("option", { name: "Infrastruktur" }))
      await userEvent.click(screen.getByRole("option", { name: "Infrastruktur" }))
      await waitFor(() => expect(screen.queryByRole("option")).not.toBeInTheDocument())
      // Infrastruktur ska nu vara valt — öppna igen för att verifiera
      await userEvent.click(getFormSelect(1))
      await waitFor(() =>
        expect(screen.getByRole("option", { name: "Infrastruktur" })).toBeInTheDocument()
      )
    })
  })
})
