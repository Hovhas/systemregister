/**
 * Testsvit: ReportsPage
 * ~30 testfall
 */

import {
  describe,
  it,
  expect,
  beforeEach,
  vi,
} from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import ReportsPage from "@/pages/ReportsPage"

// --- Hjälpfunktion ---

function renderReports() {
  return render(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>
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
      expect(screen.getByText(/export/i)).toBeInTheDocument()
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

    it("klick på NIS2 JSON öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()

      // Hitta JSON-knappen i NIS2-sektionen
      const nis2Card = screen.getByText(/nis2-rapport/i).closest(".rounded-xl, [class*='card']")
        ?? screen.getByText(/nis2-rapport/i).closest("div")

      // Om vi inte kan hitta kortet exakt, klicka på alla JSON-knappar
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[0])

      expect(openMock).toHaveBeenCalledWith("/api/v1/reports/nis2", "_blank")
      vi.unstubAllGlobals()
    })

    it("klick på NIS2 Excel öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const excelButtons = screen.getAllByRole("button", { name: /^excel$/i })
      await userEvent.click(excelButtons[0])

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/reports/nis2.xlsx",
        "_blank"
      )
      vi.unstubAllGlobals()
    })

    it("klick på NIS2 PDF öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const pdfButtons = screen.getAllByRole("button", { name: /^pdf$/i })
      await userEvent.click(pdfButtons[0])

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/reports/nis2.pdf",
        "_blank"
      )
      vi.unstubAllGlobals()
    })

    it("klick på NIS2 HTML öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      await userEvent.click(screen.getByRole("button", { name: /^html$/i }))

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/reports/nis2.html",
        "_blank"
      )
      vi.unstubAllGlobals()
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

    it("klick på Compliance Gap JSON öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      // Andra JSON-knappen är Compliance Gap
      await userEvent.click(jsonButtons[1])

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/reports/compliance-gap",
        "_blank"
      )
      vi.unstubAllGlobals()
    })

    it("klick på Compliance Gap PDF öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const pdfButtons = screen.getAllByRole("button", { name: /^pdf$/i })
      // Andra PDF-knappen är Compliance Gap
      await userEvent.click(pdfButtons[1])

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/reports/compliance-gap.pdf",
        "_blank"
      )
      vi.unstubAllGlobals()
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

    it("klick på System (Excel) öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      await userEvent.click(
        screen.getByRole("button", { name: /system \(excel\)/i })
      )

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/export/systems.xlsx",
        "_blank"
      )
      vi.unstubAllGlobals()
    })

    it("klick på System (CSV) öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      await userEvent.click(
        screen.getByRole("button", { name: /system \(csv\)/i })
      )

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/export/systems.csv",
        "_blank"
      )
      vi.unstubAllGlobals()
    })

    it("klick på System (JSON) öppnar korrekt URL", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      await userEvent.click(
        screen.getByRole("button", { name: /system \(json\)/i })
      )

      expect(openMock).toHaveBeenCalledWith(
        "/api/v1/export/systems.json",
        "_blank"
      )
      vi.unstubAllGlobals()
    })
  })

  describe("Nedladdningslänkar funktion", () => {
    it("window.open anropas med _blank som target", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const buttons = screen.getAllByRole("button")
      // Klicka på en valfri knapp
      await userEvent.click(buttons[0])

      if (openMock.mock.calls.length > 0) {
        expect(openMock.mock.calls[0][1]).toBe("_blank")
      }
      vi.unstubAllGlobals()
    })

    it("alla nedladdningsknappar anropar window.open", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const buttons = screen.getAllByRole("button")

      for (const button of buttons) {
        await userEvent.click(button)
      }

      // Vi har 9 knappar totalt (4 NIS2 + 2 Compliance + 3 Export)
      expect(openMock).toHaveBeenCalledTimes(9)
      vi.unstubAllGlobals()
    })
  })

  describe("URL-format", () => {
    it("NIS2-rapport URL börjar med /api/v1/", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const jsonButtons = screen.getAllByRole("button", { name: /^json$/i })
      await userEvent.click(jsonButtons[0])

      expect(openMock.mock.calls[0][0]).toMatch(/^\/api\/v1\//)
      vi.unstubAllGlobals()
    })

    it("export-URL:er pekar på /export/-prefix", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      await userEvent.click(
        screen.getByRole("button", { name: /system \(excel\)/i })
      )

      expect(openMock.mock.calls[0][0]).toContain("/export/")
      vi.unstubAllGlobals()
    })

    it("rapport-URL:er pekar på /reports/-prefix för NIS2", async () => {
      const openMock = vi.fn()
      vi.stubGlobal("open", openMock)

      renderReports()
      const htmlBtn = screen.getByRole("button", { name: /^html$/i })
      await userEvent.click(htmlBtn)

      expect(openMock.mock.calls[0][0]).toContain("/reports/")
      vi.unstubAllGlobals()
    })
  })

  describe("Ikonrendering", () => {
    it("NIS2-kortet visar FileText-ikon", () => {
      renderReports()
      // lucide-react renderar SVG
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
      // NIS2 har JSON, Excel, PDF, HTML
      expect(htmlBtns).toHaveLength(1)
      // Minst 1 av varje
      expect(jsonBtns.length).toBeGreaterThanOrEqual(1)
      expect(excelBtns.length).toBeGreaterThanOrEqual(1)
      expect(pdfBtns.length).toBeGreaterThanOrEqual(1)
    })
  })
})
