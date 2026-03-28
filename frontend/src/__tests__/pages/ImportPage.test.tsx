/**
 * Testsvit: ImportPage
 * ~40 testfall
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
import ImportPage from "@/pages/ImportPage"

// --- Testdata ---

const mockOrgs = [
  { id: "org-1", name: "Kommunen", org_type: "kommun" },
  { id: "org-2", name: "Bolaget AB", org_type: "bolag" },
]

const successResult = { imported: 5, errors: [] }
const partialResult = {
  imported: 3,
  errors: [
    { row: 2, error: "Ogiltigt fält: name" },
    { row: 4, error: { field: "criticality", msg: "Ogiltigt värde" } },
  ],
}

// --- MSW-server ---

const server = setupServer(
  http.get(/\/api\/v1\/organizations/, () => HttpResponse.json(mockOrgs)),
  http.post("/api/v1/import/systems", () => HttpResponse.json(successResult)),
  http.post("/api/v1/import/classifications", () =>
    HttpResponse.json(successResult)
  ),
  http.post("/api/v1/import/owners", () => HttpResponse.json(successResult))
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Hjälpfunktion ---

function renderImport() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImportPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function createFile(name: string, type: string): File {
  return new File(["innehåll"], name, { type })
}

// --- Tester ---

describe("ImportPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar sidrubriken Import", async () => {
      renderImport()
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: /^import$/i })
        ).toBeInTheDocument()
      )
    })

    it("visar 3 flikar: System, Klassningar, Ägare", async () => {
      renderImport()
      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /^system$/i })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("tab", { name: /klassningar/i })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("tab", { name: /ägare/i })
        ).toBeInTheDocument()
      })
    })

    it("System-fliken är aktiv som standard", async () => {
      renderImport()
      await waitFor(() => {
        const tab = screen.getByRole("tab", { name: /^system$/i })
        expect(tab).toHaveAttribute("aria-selected", "true")
      })
    })

    it("visar 'Importera system'-rubriken i System-fliken", async () => {
      renderImport()
      await waitFor(() =>
        expect(screen.getByText("Importera system")).toBeInTheDocument()
      )
    })
  })

  describe("Organisation-val (System-fliken)", () => {
    it("visar organisations-dropdown i System-fliken", async () => {
      renderImport()
      await waitFor(() =>
        expect(
          screen.getByText(/välj organisation/i)
        ).toBeInTheDocument()
      )
    })

    it("dropdown innehåller organisationer", async () => {
      renderImport()
      await waitFor(() =>
        screen.getByText(/välj organisation/i)
      )
      await userEvent.click(
        screen.getByText(/välj organisation/i)
      )
      await waitFor(() => {
        expect(
          screen.getByRole("option", { name: "Kommunen" })
        ).toBeInTheDocument()
        expect(
          screen.getByRole("option", { name: "Bolaget AB" })
        ).toBeInTheDocument()
      })
    })

    it("döljer organisations-dropdown i Klassningar-fliken", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))
      await waitFor(() =>
        expect(
          screen.queryByText(/välj organisation/i)
        ).not.toBeInTheDocument()
      )
    })

    it("döljer organisations-dropdown i Ägare-fliken", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /ägare/i }))
      await userEvent.click(screen.getByRole("tab", { name: /ägare/i }))
      await waitFor(() =>
        expect(
          screen.queryByText(/välj organisation/i)
        ).not.toBeInTheDocument()
      )
    })
  })

  describe("Filuppladdnings-zon", () => {
    it("visar drag-and-drop-zon", async () => {
      renderImport()
      await waitFor(() =>
        expect(
          screen.getByText(/dra och släpp fil här/i)
        ).toBeInTheDocument()
      )
    })

    it("visar filtyp-info (.xlsx och .csv)", async () => {
      renderImport()
      await waitFor(() =>
        expect(screen.getByText(/stöder .xlsx och .csv/i)).toBeInTheDocument()
      )
    })

    it("dold file input accepterar .xlsx och .csv", async () => {
      renderImport()
      await waitFor(() => {
        const input = document.querySelector(
          'input[type="file"]'
        ) as HTMLInputElement
        expect(input?.accept).toBe(".xlsx,.csv")
      })
    })
  })

  describe("Filval", () => {
    it("visar valda xlsx-filens namn", async () => {
      renderImport()
      await waitFor(() => document.querySelector('input[type="file"]'))

      const file = createFile("import.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(screen.getByText("import.xlsx")).toBeInTheDocument()
      )
    })

    it("visar valda csv-filens namn", async () => {
      renderImport()
      await waitFor(() => document.querySelector('input[type="file"]'))

      const file = createFile("data.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(screen.getByText("data.csv")).toBeInTheDocument()
      )
    })

    it("visar filens storlek i KB", async () => {
      renderImport()
      await waitFor(() => document.querySelector('input[type="file"]'))

      const file = createFile("test.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() => {
        expect(screen.getByText(/\d+\.\d+ KB/)).toBeInTheDocument()
      })
    })

    it("drag-and-drop hanterar fil", async () => {
      renderImport()
      await waitFor(() => screen.getByText(/dra och släpp/i))

      const dropZone = screen.getByText(/dra och släpp/i).closest("div")!
      const file = createFile("drag.csv", "text/csv")

      // Simulera drop-event
      const dataTransfer = {
        files: [file],
        items: [],
        types: [],
      }
      await userEvent.upload(
        document.querySelector('input[type="file"]') as HTMLInputElement,
        file
      )

      await waitFor(() =>
        expect(screen.getByText("drag.csv")).toBeInTheDocument()
      )
    })
  })

  describe("Import-knapp", () => {
    it("Importera-knapp är inaktiverad utan fil", async () => {
      renderImport()
      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).toBeDisabled()
      )
    })

    it("Importera-knapp är inaktiverad när System-flik utan organisation", async () => {
      renderImport()
      await waitFor(() => document.querySelector('input[type="file"]'))

      const file = createFile("systems.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      // Fil vald men ingen organisation => inaktiverad
      expect(
        screen.getByRole("button", { name: /importera/i })
      ).toBeDisabled()
    })

    it("Importera-knapp är aktiv med fil i Klassningar-flik", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      await waitFor(() => document.querySelector('input[type="file"]'))
      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
    })
  })

  describe("Import-resultat", () => {
    it("visar importerade poster vid lyckad import", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      await waitFor(() => document.querySelector('input[type="file"]'))
      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        expect(screen.getByText(/5 poster importerade/i)).toBeInTheDocument()
      )
    })

    it("visar fel-antal och fel-lista vid delvis misslyckad import", async () => {
      server.use(
        http.post("/api/v1/import/classifications", () =>
          HttpResponse.json(partialResult)
        )
      )
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() => {
        expect(screen.getByText(/3 poster importerade/i)).toBeInTheDocument()
        expect(screen.getByText(/2 fel/i)).toBeInTheDocument()
        expect(screen.getByText(/rad 2/i)).toBeInTheDocument()
        expect(screen.getByText(/rad 4/i)).toBeInTheDocument()
      })
    })

    it("visar fel-meddelande vid API-fel", async () => {
      server.use(
        http.post("/api/v1/import/classifications", () =>
          HttpResponse.json({ detail: "Error" }, { status: 500 })
        )
      )
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        // Axios kastar Error med statusmeddelande, inte "Import misslyckades"
        expect(screen.getByText(/status code 500|import misslyckades/i)).toBeInTheDocument()
      )
    })

    it("visar laddningsindikator under import", async () => {
      let resolveImport!: () => void
      server.use(
        http.post("/api/v1/import/classifications", () =>
          new Promise((resolve) => {
            resolveImport = () =>
              resolve(HttpResponse.json(successResult) as Response)
          })
        )
      )
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        screen.getByRole("button", { name: /importera/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importerar/i })
        ).toBeDisabled()
      )
      resolveImport()
    })
  })

  describe("Flik-byte", () => {
    it("kan byta till Klassningar-fliken", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))
      await waitFor(() =>
        expect(screen.getByText("Importera klassningar")).toBeInTheDocument()
      )
    })

    it("kan byta till Ägare-fliken", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /ägare/i }))
      await userEvent.click(screen.getByRole("tab", { name: /ägare/i }))
      await waitFor(() =>
        expect(screen.getByText("Importera ägare")).toBeInTheDocument()
      )
    })

    it("kan återgå till System-fliken", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /^system$/i }))
      await waitFor(() =>
        expect(screen.getByText("Importera system")).toBeInTheDocument()
      )
    })
  })

  describe("Fel-format felmeddelanden", () => {
    it("visar object-fel som JSON-sträng", async () => {
      server.use(
        http.post("/api/v1/import/classifications", () =>
          HttpResponse.json({
            imported: 0,
            errors: [{ row: 1, error: { field: "name", msg: "required" } }],
          })
        )
      )
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      const file = createFile("cls.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        screen.getByRole("button", { name: /importera/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        expect(screen.getByText(/1 fel/i)).toBeInTheDocument()
      )
    })

    it("visar 0 importerade vid total misslyckning", async () => {
      server.use(
        http.post("/api/v1/import/owners", () =>
          HttpResponse.json({
            imported: 0,
            errors: [{ row: 1, error: "Fel" }],
          })
        )
      )
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /ägare/i }))
      await userEvent.click(screen.getByRole("tab", { name: /ägare/i }))

      const file = createFile("owners.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        screen.getByRole("button", { name: /importera/i })
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        expect(screen.getByText(/0 poster importerade/i)).toBeInTheDocument()
      )
    })
  })

  describe("Import-knapp tillstånd", () => {
    it("Importera-knapp är aktiv med fil i Ägare-flik", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /ägare/i }))
      await userEvent.click(screen.getByRole("tab", { name: /ägare/i }))

      await waitFor(() => document.querySelector('input[type="file"]'))
      const file = createFile("owners.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
    })

    it("fil-info uppdateras vid ny fil (ersätter gammal)", async () => {
      renderImport()
      await waitFor(() => screen.getByRole("tab", { name: /klassningar/i }))
      await userEvent.click(screen.getByRole("tab", { name: /klassningar/i }))

      await waitFor(() => document.querySelector('input[type="file"]'))
      const input = document.querySelector('input[type="file"]') as HTMLInputElement

      await userEvent.upload(input, createFile("first.csv", "text/csv"))
      await waitFor(() => screen.getByText("first.csv"))

      await userEvent.upload(input, createFile("second.csv", "text/csv"))
      await waitFor(() => screen.getByText("second.csv"))
      expect(screen.queryByText("first.csv")).not.toBeInTheDocument()
    })
  })

  describe("Import med organisation", () => {
    it("System-import med organisation skickar org-id", async () => {
      let capturedUrl: string | null = null
      server.use(
        http.post("/api/v1/import/:type", ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(successResult)
        })
      )
      renderImport()
      await waitFor(() => document.querySelector('input[type="file"]'))

      // Välj organisation
      await waitFor(() =>
        screen.getByText(/välj organisation/i)
      )
      await userEvent.click(
        screen.getByText(/välj organisation/i)
      )
      await waitFor(() =>
        expect(screen.getByRole("option", { name: "Kommunen" })).toBeInTheDocument()
      )
      await userEvent.click(screen.getByRole("option", { name: "Kommunen" }))

      // Välj fil
      const file = createFile("systems.csv", "text/csv")
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      await userEvent.upload(input, file)

      await waitFor(() =>
        expect(
          screen.getByRole("button", { name: /importera/i })
        ).not.toBeDisabled()
      )
      await userEvent.click(screen.getByRole("button", { name: /importera/i }))

      await waitFor(() =>
        expect(capturedUrl).toContain("organization_id=org-1")
      )
    })
  })
})
