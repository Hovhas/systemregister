/**
 * Testsvit: SkipLink-komponent
 */

import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SkipLink } from "@/components/SkipLink"

describe("SkipLink", () => {
  it("renderas med sr-only klass", () => {
    render(<SkipLink />)
    const link = screen.getByText(/hoppa till huvudinnehåll/i)
    expect(link).toBeInTheDocument()
    expect(link.className).toMatch(/sr-only/)
  })

  it("href pekar till #main-content", () => {
    render(<SkipLink />)
    const link = screen.getByText(/hoppa till huvudinnehåll/i)
    expect(link).toHaveAttribute("href", "#main-content")
  })

  it("har focus-klasser för synlighet vid fokus", () => {
    render(<SkipLink />)
    const link = screen.getByText(/hoppa till huvudinnehåll/i)
    expect(link.className).toMatch(/focus:not-sr-only/)
  })
})
