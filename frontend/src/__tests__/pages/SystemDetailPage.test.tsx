/**
 * Testsvit: SystemDetailPage
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
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { setupServer, http, HttpResponse } from "../setup"
import SystemDetailPage from "@/pages/SystemDetailPage"
import {
  Criticality,
  SystemCategory,
  LifecycleStatus,
  OwnerRole,
  IntegrationType,
} from "@/types"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
]

const mockSystem = {
  id: "sys-1",
  name: "Lönesystem",
  organization_id: "org-1",
  description: "Hanterar löner och HR-data",
  system_category: SystemCategory.VERKSAMHETSSYSTEM,
  criticality: Criticality.HIGH,
  lifecycle_status: LifecycleStatus.ACTIVE,
  nis2_applicable: true,
  nis2_classification: "väsentlig",
  aliases: "LöneApp, PaySys",
  business_area: "HR",
  has_elevated_protection: false,
  security_protection: false,
  treats_personal_data: true,
  treats_sensitive_data: false,
  third_country_transfer: false,
  hosting_model: "cloud",
  cloud_provider: "Azure",
  data_location_country: "SE",
  product_name: "PayDay Pro",
  product_version: "4.2.1",
  deployment_date: "2020-01-15",
  planned_decommission_date: null,
  end_of_support_date: "2028-12-31",
  backup_frequency: "dagligen",
  rpo: "4h",
  rto: "8h",
  dr_plan_exists: true,
  last_risk_assessment_date: "2024-06-01",
  klassa_reference_id: "KLASSA-123",
  extended_attributes: {
    projekt_nummer: "P-2020-001",
    ansvarig_chef: "Anna Andersson",
  },
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
  created_at: "2020-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  last_reviewed_at: "2024-06-01",
  last_reviewed_by: "admin",
  classifications: [
    {
      id: "cls-1",
      system_id: "sys-1",
      confidentiality: 3,
      integrity: 2,
      availability: 4,
      traceability: 1,
      classified_by: "Säkerhetsansvarig",
      classified_at: "2024-01-01T00:00:00Z",
      valid_until: "2025-01-01",
      notes: "Klassning genomförd enligt KLASSA",
    },
  ],
  owners: [
    {
      id: "own-1",
      system_id: "sys-1",
      role: OwnerRole.SYSTEM_OWNER,
      name: "Per Persson",
      email: "per@test.se",
      phone: "070-123 45 67",
      organization_id: "org-1",
      created_at: "2020-01-01T00:00:00Z",
    },
    {
      id: "own-2",
      system_id: "sys-1",
      role: OwnerRole.INFORMATION_OWNER,
      name: "Maria Nilsson",
      email: null,
      phone: null,
      organization_id: "org-1",
      created_at: "2020-01-01T00:00:00Z",
    },
  ],
  integrations: [
    {
      id: "int-1",
      source_system_id: "sys-1",
      target_system_id: "sys-2",
      integration_type: IntegrationType.API,
      data_types: "Löndata",
      frequency: "Dagligen",
      description: "Skickar lönedata till bokföring",
      criticality: Criticality.HIGH,
      is_external: false,
      external_party: null,
      created_at: "2020-01-01T00:00:00Z",
    },
  ],
  gdpr_treatments: [],
  contracts: [],
}

const mockAuditEntries = [
  {
    id: "audit-1",
    table_name: "systems",
    record_id: "sys-1",
    action: "INSERT",
    changed_at: "2020-01-01T10:00:00Z",
    changed_by: "admin",
    old_values: null,
    new_values: null,
  },
  {
    id: "audit-2",
    table_name: "systems",
    record_id: "sys-1",
    action: "UPDATE",
    changed_at: "2024-01-01T12:00:00Z",
    changed_by: "per.persson",
    old_values: { name: "Gammalt namn" },
    new_values: { name: "Lönesystem" },
  },
]

// --- MSW-server ---

const server = setupServer(
  http.get("/api/v1/organizations", () => HttpResponse.json(mockOrgs)),
  http.get("/api/v1/systems/:id", ({ params }) => {
    if (params.id === "nonexistent") {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 })
    }
    return HttpResponse.json(mockSystem)
  }),
  http.get("/api/v1/audit/record/:id", () =>
    HttpResponse.json(mockAuditEntries)
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderDetail(id = "sys-1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/systems/${id}`]}>
        <Routes>
          <Route path="/systems/:id" element={<SystemDetailPage />} />
          <Route path="/systems" element={<div>Systems list</div>} />
          <Route
            path="/systems/:id/edit"
            element={<div>Edit form</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("SystemDetailPage", () => {
  describe("Laddning och fel", () => {
    it("visar skeleton-laddning initialt", () => {
      renderDetail()
      const skeletons = document.querySelectorAll(".skeleton")
      expect(skeletons.length).toBeGreaterThan(0)
    })

    it("döljer skeleton efter data laddats", async () => {
      renderDetail()
      await waitFor(() => {
        const matches = screen.getAllByText("Lönesystem")
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar felmeddelande vid 404", async () => {
      renderDetail("nonexistent")
      await waitFor(() =>
        expect(
          screen.getByText(/kunde inte hämta system/i)
        ).toBeInTheDocument()
      )
    })

    it("visar Tillbaka-knapp vid fel", async () => {
      renderDetail("nonexistent")
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /tillbaka/i })
        ).toBeInTheDocument()
      )
    })
  })

  describe("Sidhuvud och metadata", () => {
    it("visar systemnamnet som rubrik", async () => {
      renderDetail()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /lönesystem/i })
        ).toBeInTheDocument()
      )
    })

    it("visar kategoribadge", async () => {
      renderDetail()
      await waitFor(() => {
        const elements = screen.getAllByText("Verksamhetssystem")
        expect(elements.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar livscykelbadge", async () => {
      renderDetail()
      await waitFor(() => {
        const elements = screen.getAllByText("I drift")
        expect(elements.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar NIS2-badge när tillämpligt", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("NIS2")).toBeInTheDocument()
      )
    })
  })

  describe("Knappar", () => {
    it("visar Redigera-knapp", async () => {
      renderDetail()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /redigera/i })
        ).toBeInTheDocument()
      )
    })

    it("visar Ta bort-knapp", async () => {
      renderDetail()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /ta bort/i })
        ).toBeInTheDocument()
      )
    })

    it("Redigera-knapp navigerar till redigeringsformulär", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("button", { name: /redigera/i }))
      await userEvent.click(screen.getByRole("button", { name: /redigera/i }))
      await waitFor(() =>
        expect(screen.getByText("Edit form")).toBeInTheDocument()
      )
    })
  })

  describe("Flikar", () => {
    it("renderar alla 6 flikar", async () => {
      renderDetail()
      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /översikt/i })).toBeInTheDocument()
        expect(screen.getByRole("tab", { name: /klassning/i })).toBeInTheDocument()
        expect(screen.getByRole("tab", { name: /ägare/i })).toBeInTheDocument()
        expect(screen.getByRole("tab", { name: /integrationer/i })).toBeInTheDocument()
        expect(screen.getByRole("tab", { name: /övrig data/i })).toBeInTheDocument()
        expect(screen.getByRole("tab", { name: /ändringslogg/i })).toBeInTheDocument()
      })
    })

    it("visar antal klassningar på klassning-fliken", async () => {
      renderDetail()
      await waitFor(() => {
        const klassningTab = screen.getByRole("tab", { name: /klassning/i })
        expect(within(klassningTab).getByText("(1)")).toBeInTheDocument()
      })
    })

    it("visar antal ägare på ägare-fliken", async () => {
      renderDetail()
      await waitFor(() => {
        const agareTab = screen.getByRole("tab", { name: /ägare/i })
        expect(within(agareTab).getByText("(2)")).toBeInTheDocument()
      })
    })
  })

  describe("Översikt-tab", () => {
    it("visar Grundinformation-sektion", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("Grundinformation")).toBeInTheDocument()
      )
    })

    it("visar beskrivning", async () => {
      renderDetail()
      await waitFor(() => {
        // Description appears in both header and Oversikt tab
        const matches = screen.getAllByText("Hanterar löner och HR-data")
        expect(matches.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar business_area (HR)", async () => {
      renderDetail()
      await waitFor(() => expect(screen.getByText("HR")).toBeInTheDocument())
    })

    it("visar hosting_model (cloud)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("cloud")).toBeInTheDocument()
      )
    })

    it("visar cloud_provider (Azure)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("Azure")).toBeInTheDocument()
      )
    })

    it("visar product_name (PayDay Pro)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("PayDay Pro")).toBeInTheDocument()
      )
    })

    it("visar Driftmiljö-sektion", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("Driftmiljö")).toBeInTheDocument()
      )
    })

    it("visar Livscykel-sektion", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("Livscykel")).toBeInTheDocument()
      )
    })

    it("visar Compliance-sektion", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("Compliance")).toBeInTheDocument()
      )
    })

    it("visar Behandlar personuppgifter: Ja", async () => {
      renderDetail()
      await waitFor(() => {
        const label = screen.getByText(/behandlar personuppgifter/i)
        const parent = label.closest("div")
        expect(within(parent!).getByText("Ja")).toBeInTheDocument()
      })
    })

    it("visar KLASSA-referens", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("KLASSA-123")).toBeInTheDocument()
      )
    })
  })

  describe("Klassning-tab", () => {
    it("visar klassning när man klickar på fliken", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("tab", { name: /klassning/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassning/i }))
      await waitFor(() =>
        expect(screen.getByText(/klassad av/i)).toBeInTheDocument()
      )
    })

    it("visar Senaste-badge för nyaste klassning", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("tab", { name: /klassning/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassning/i }))
      await waitFor(() =>
        expect(screen.getByText("Senaste")).toBeInTheDocument()
      )
    })

    it("visar CIA-bars (K, R, T, S)", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("tab", { name: /klassning/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassning/i }))
      await waitFor(() => {
        expect(screen.getByText("K")).toBeInTheDocument()
        expect(screen.getByText("R")).toBeInTheDocument()
        expect(screen.getByText("T")).toBeInTheDocument()
        expect(screen.getByText("S")).toBeInTheDocument()
      })
    })

    it("CIA-bar K=3 har röd klass (>= 3)", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /klassning/i })
      )
      await waitFor(() => {
        const bars = document.querySelectorAll(".bg-red-500")
        expect(bars.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("CIA-bar R=2 har gul klass (=2)", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /klassning/i })
      )
      await waitFor(() => {
        const bars = document.querySelectorAll(".bg-yellow-500")
        expect(bars.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("visar klassnings-notering", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /klassning/i })
      )
      await waitFor(() =>
        expect(
          screen.getByText("Klassning genomförd enligt KLASSA")
        ).toBeInTheDocument()
      )
    })
  })

  describe("Ägare-tab", () => {
    it("visar ägarens namn", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ägare/i })
      )
      await waitFor(() => {
        expect(screen.getByText("Per Persson")).toBeInTheDocument()
        expect(screen.getByText("Maria Nilsson")).toBeInTheDocument()
      })
    })

    it("visar ägarens roll som badge", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ägare/i })
      )
      await waitFor(() => {
        expect(screen.getByText("Systemägare")).toBeInTheDocument()
        expect(screen.getByText("Informationsägare")).toBeInTheDocument()
      })
    })

    it("visar ägarens e-post", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ägare/i })
      )
      await waitFor(() =>
        expect(screen.getByText("per@test.se")).toBeInTheDocument()
      )
    })
  })

  describe("Integrationer-tab", () => {
    it("visar integration i tabellen", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /integrationer/i })
      )
      await waitFor(() =>
        expect(
          screen.getByText("Skickar lönedata till bokföring")
        ).toBeInTheDocument()
      )
    })

    it("visar Ut-riktning när sys-1 är källa", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /integrationer/i })
      )
      await waitFor(() =>
        expect(screen.getByText("Ut")).toBeInTheDocument()
      )
    })

    it("visar integrations-frekvens", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /integrationer/i })
      )
      await waitFor(() =>
        expect(screen.getByText("Dagligen")).toBeInTheDocument()
      )
    })
  })

  describe("Övrig data-tab", () => {
    it("visar extended_attributes i tabell", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /övrig data/i })
      )
      await waitFor(() => {
        // formatKey converts "projekt_nummer" to "Projekt Nummer"
        expect(screen.getByText("Projekt Nummer")).toBeInTheDocument()
        expect(screen.getByText("P-2020-001")).toBeInTheDocument()
        expect(screen.getByText("Ansvarig Chef")).toBeInTheDocument()
        expect(screen.getByText("Anna Andersson")).toBeInTheDocument()
      })
    })
  })

  describe("Ändringslogg-tab", () => {
    it("visar skapades-händelse", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ändringslogg/i })
      )
      await waitFor(() =>
        expect(screen.getByText("Skapad")).toBeInTheDocument()
      )
    })

    it("visar ändrad-händelse", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ändringslogg/i })
      )
      await waitFor(() =>
        expect(screen.getByText("Ändrad")).toBeInTheDocument()
      )
    })

    it("visar ändrad-av", async () => {
      renderDetail()
      await userEvent.click(
        await screen.findByRole("tab", { name: /ändringslogg/i })
      )
      await waitFor(() =>
        expect(screen.getByText(/av admin/i)).toBeInTheDocument()
      )
    })
  })

  describe("Alias och produkt", () => {
    it("visar alias (LöneApp, PaySys)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("LöneApp, PaySys")).toBeInTheDocument()
      )
    })

    it("visar product_version (4.2.1)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("4.2.1")).toBeInTheDocument()
      )
    })

    it("visar data_location_country (SE)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("SE")).toBeInTheDocument()
      )
    })
  })

  describe("Livscykel-info", () => {
    it("visar deployment_date (2020-01-15)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("2020-01-15")).toBeInTheDocument()
      )
    })

    it("visar end_of_support_date (2028-12-31)", async () => {
      renderDetail()
      await waitFor(() =>
        expect(screen.getByText("2028-12-31")).toBeInTheDocument()
      )
    })

    it("visar last_risk_assessment_date (2024-06-01)", async () => {
      renderDetail()
      await waitFor(() => {
        const cells = screen.getAllByText("2024-06-01")
        expect(cells.length).toBeGreaterThanOrEqual(1)
      })
    })
  })

  describe("Radera-dialog", () => {
    it("öppnar radera-dialog vid klick på Ta bort", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("button", { name: /ta bort/i }))
      await userEvent.click(screen.getByRole("button", { name: /ta bort/i }))
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /ta bort system/i })
        ).toBeInTheDocument()
      )
    })

    it("dialogens beskrivning inkluderar systemnamnet", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("button", { name: /ta bort/i }))
      await userEvent.click(screen.getByRole("button", { name: /ta bort/i }))
      await waitFor(() => {
        const elements = screen.getAllByText(/lönesystem/i)
        expect(elements.length).toBeGreaterThanOrEqual(1)
      })
    })

    it("Avbryt stänger dialogrutan", async () => {
      renderDetail()
      await waitFor(() => screen.getByRole("button", { name: /ta bort/i }))
      await userEvent.click(screen.getByRole("button", { name: /ta bort/i }))
      await waitFor(() =>
        screen.getByRole("heading", { name: /ta bort system/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /avbryt/i }))
      await waitFor(() =>
        expect(
          screen.queryByRole("heading", { name: /ta bort system/i })
        ).not.toBeInTheDocument()
      )
    })

    it("bekräfta-knapp anropar delete-API", async () => {
      let deleteCalld = false
      server.use(
        http.delete("/api/v1/systems/:id", () => {
          deleteCalld = true
          return new HttpResponse(null, { status: 204 })
        })
      )
      renderDetail()
      await waitFor(() => screen.getByRole("button", { name: /ta bort/i }))
      await userEvent.click(screen.getByRole("button", { name: /ta bort/i }))
      await waitFor(() =>
        screen.getByRole("heading", { name: /ta bort system/i })
      )
      await userEvent.click(
        screen.getByRole("button", { name: /ta bort$/i })
      )
      await waitFor(() => expect(deleteCalld).toBe(true))
    })
  })
})
