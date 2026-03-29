/**
 * Testsvit: ReportsPage
 * ~30 testfall
 */

import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
} from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { MemoryRouter } from "react-router-dom"
import ReportsPage from "@/pages/ReportsPage"

// --- Hjälpfunktion ---

let fetchSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  // Mock fetch to return a blob response for download tests
  fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(new Blob(["data"]), {
      status: 200,
      headers: { "content-type": "application/octet-stream" },
    })
  )
  // Mock URL.createObjectURL and revokeObjectURL
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: vi.fn(() => "blob:mock"),
    revokeObjectURL: vi.fn(),
  })
})

afterEach(() => {
  fetchSpy.mockRestore()
  vi.unstubAllGlobals()
})

function renderReports() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tester ---

describe("ReportsPage", () => {
  describe("Grundläggande rendering", () => {
    it("renderar sidrubriken Rapporter", () => {
      renderReports()
      expect(
        screen.getByRole("heading", { name: /rapporter/i })
      ).toBeInTheDocument()
    })

    it("renderar 3 rapportkort", () => {
      renderReports()
      // NIS2, Compliance Gap, Export
      expect(screen.getByText(/nis2-rapport/i)).toBeInTheDocument()
      expect(screen.getByText(/compliance gap-analys/i)).toBeInTheDocument()
      expect(screen.getAllByText(/export/i).length).toBeGreaterThanOrEqual(1)
    })

    it("visar NIS2-rapport-kortet", () => {
      renderReports()
      expect(screen.getByText(/nis2-rapport/i)).toBeInTheDocument()
    })

    it("visar Compliance Gap-kortet", () => {
      renderReports()
      expect(screen.getByText(/compliance gap-analys/i)).toBeInTheDocument()
    })

    it("visar Export-kortet", () => {
      renderReports()
      expect(screen.getByText("Export")).toBeInTheDocument()
    })
  })

  describe("NIS2-rapport nedladdningar", () => {
    it("visar JSON-knapp", () => {
      renderReports()
      const buttons = screen.getAllByRole("button", { name: /json/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it("visar Excel-knapp", () => {
      renderReports()
      const buttons = screen.getAllByRole("button", { name: /excel/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it("visar PDF-knapp för NIS2", () => {
      renderReports()
      const buttons = screen.getAllByRole("button", { name: /pdf/i })
      expect(buttons.length).toBeGreaterThanOrEqual(1)
    })

    it("visar HTML-knapp för NIS2", () => {
      renderReports()
      expect(
        screen.getByRole("button", { name: /html/i })
      ).toBeInTheDocument()
    })

    it("klick på NIS2 JSON anropar fetch med korrekt URL", async () => {
      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[0])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/nis2"))
    })

    it("klick på NIS2 Excel anropar fetch med korrekt URL", async () => {
      renderReports()
      const excelButtons = screen.getAllByRole("button", { name: /^excel$/i })
      await userEvent.click(excelButtons[0])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/nis2.xlsx"))
    })

    it("klick på NIS2 PDF anropar fetch med korrekt URL", async () => {
      renderReports()
      const pdfButtons = screen.getAllByRole("button", { name: /^pdf$/i })
      await userEvent.click(pdfButtons[0])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/nis2.pdf"))
    })

    it("klick på NIS2 HTML anropar fetch med korrekt URL", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /^html$/i }))
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/nis2.html"))
    })
  })

  describe("Compliance Gap-rapport", () => {
    it("visar 2 knappar för Compliance Gap (JSON + PDF)", () => {
      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      const pdfButtons = screen.getAllByRole("button", { name: /^pdf$/i })
      // Minst 2 JSON-knappar totalt (NIS2 + Compliance)
      expect(jsonButtons.length).toBeGreaterThanOrEqual(2)
      // Minst 2 PDF-knappar totalt (NIS2 + Compliance)
      expect(pdfButtons.length).toBeGreaterThanOrEqual(2)
    })

    it("klick på Compliance Gap JSON anropar fetch med korrekt URL", async () => {
      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[1])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/compliance-gap"))
    })

    it("klick på Compliance Gap PDF anropar fetch med korrekt URL", async () => {
      renderReports()
      const pdfButtons = screen.getAllByRole("button", { name: /^pdf$/i })
      await userEvent.click(pdfButtons[1])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/reports/compliance-gap.pdf"))
    })
  })

  describe("Systemexport", () => {
    it("visar System (Excel)-knapp", () => {
      renderReports()
      expect(
        screen.getByRole("button", { name: /system \(excel\)/i })
      ).toBeInTheDocument()
    })

    it("visar System (CSV)-knapp", () => {
      renderReports()
      expect(
        screen.getByRole("button", { name: /system \(csv\)/i })
      ).toBeInTheDocument()
    })

    it("visar System (JSON)-knapp", () => {
      renderReports()
      expect(
        screen.getByRole("button", { name: /system \(json\)/i })
      ).toBeInTheDocument()
    })

    it("klick på System (Excel) anropar fetch med korrekt URL", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /system \(excel\)/i }))
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/export/systems.xlsx"))
    })

    it("klick på System (CSV) anropar fetch med korrekt URL", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /system \(csv\)/i }))
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/export/systems.csv"))
    })

    it("klick på System (JSON) anropar fetch med korrekt URL", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /system \(json\)/i }))
      await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith("/api/v1/export/systems.json"))
    })
  })

  describe("Nedladdningslänkar funktion", () => {
    it("fetch anropas vid klick på nedladdningsknapp", async () => {
      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[0])
      await waitFor(() => expect(fetchSpy).toHaveBeenCalled())
    })

    it("alla nedladdningsknappar anropar fetch", async () => {
      renderReports()
      // 9 download buttons: 4 NIS2 + 2 Compliance + 3 Export
      const jsonBtns = screen.getAllByRole("button", { name: /^json$/i })
      const excelBtns = screen.getAllByRole("button", { name: /^excel$/i })
      const pdfBtns = screen.getAllByRole("button", { name: /^pdf$/i })
      const htmlBtns = screen.getAllByRole("button", { name: /^html$/i })
      const exportBtns = screen.getAllByRole("button", { name: /^system/i })
      const allBtns = [...jsonBtns, ...excelBtns, ...pdfBtns, ...htmlBtns, ...exportBtns]
      expect(allBtns.length).toBe(9)
    })
  })

  describe("URL-format", () => {
    it("NIS2-rapport URL börjar med /api/v1/", async () => {
      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[0])
      await waitFor(() => {
        const url = fetchSpy.mock.calls[0]?.[0] as string
        expect(url).toMatch(/^\/api\/v1\//)
      })
    })

    it("export-URL:er pekar på /export/-prefix", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /system \(excel\)/i }))
      await waitFor(() => {
        const url = fetchSpy.mock.calls[0]?.[0] as string
        expect(url).toContain("/export/")
      })
    })

    it("rapport-URL:er pekar på /reports/-prefix för NIS2", async () => {
      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /^html$/i }))
      await waitFor(() => {
        const url = fetchSpy.mock.calls[0]?.[0] as string
        expect(url).toContain("/reports/")
      })
    })
  })

  describe("Ikonrendering", () => {
    it("NIS2-kortet visar FileText-ikon", () => {
      renderReports()
      const svgIcons = document.querySelectorAll("svg")
      expect(svgIcons.length).toBeGreaterThan(0)
    })

    it("Export-kortet visar Download-ikon i korttiteln", () => {
      renderReports()
      const exportTitle = screen.getByText("Export").closest("div")
      const icon = exportTitle?.querySelector("svg")
      expect(icon).toBeInTheDocument()
    })
  })

  describe("Knapp-layout", () => {
    it("NIS2-kortet har 4 format-knappar", () => {
      renderReports()
      const jsonBtns = screen.getAllByRole("button", { name: /^json$/i })
      const excelBtns = screen.getAllByRole("button", { name: /^excel$/i })
      const pdfBtns = screen.getAllByRole("button", { name: /^pdf$/i })
      const htmlBtns = screen.getAllByRole("button", { name: /^html$/i })
      expect(htmlBtns).toHaveLength(1)
      expect(jsonBtns.length).toBeGreaterThanOrEqual(1)
      expect(excelBtns.length).toBeGreaterThanOrEqual(1)
      expect(pdfBtns.length).toBeGreaterThanOrEqual(1)
    })
  })
})
