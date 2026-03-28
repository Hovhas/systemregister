/**
 * Testsvit: ConfirmDialog-komponent
 * ~20 testfall
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ConfirmDialog } from "@/components/ConfirmDialog"

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  title: "Bekräfta borttagning",
  description: "Är du säker på att du vill ta bort detta system?",
  onConfirm: vi.fn(),
}

describe("ConfirmDialog", () => {
  it("renders title when open", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText("Bekräfta borttagning")).toBeInTheDocument()
  })

  it("renders description when open", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText(/Är du säker/)).toBeInTheDocument()
  })

  it("does not render content when closed", () => {
    render(<ConfirmDialog {...defaultProps} open={false} />)
    expect(screen.queryByText("Bekräfta borttagning")).not.toBeInTheDocument()
  })

  it("renders Avbryt button", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText("Avbryt")).toBeInTheDocument()
  })

  it("renders Ta bort button", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText("Ta bort")).toBeInTheDocument()
  })

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByText("Ta bort"))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it("calls onOpenChange(false) when Avbryt clicked", () => {
    const onOpenChange = vi.fn()
    render(<ConfirmDialog {...defaultProps} onOpenChange={onOpenChange} />)
    fireEvent.click(screen.getByText("Avbryt"))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it("shows loading text when loading=true", () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    expect(screen.getByText("Tar bort...")).toBeInTheDocument()
  })

  it("hides Ta bort text when loading", () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    expect(screen.queryByText("Ta bort")).not.toBeInTheDocument()
  })

  it("disables confirm button when loading", () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    const btn = screen.getByText("Tar bort...")
    expect(btn.closest("button")).toBeDisabled()
  })

  it("confirm button is not disabled by default", () => {
    render(<ConfirmDialog {...defaultProps} />)
    const btn = screen.getByText("Ta bort")
    expect(btn.closest("button")).not.toBeDisabled()
  })

  it("defaults to destructive variant", () => {
    render(<ConfirmDialog {...defaultProps} />)
    const btn = screen.getByText("Ta bort").closest("button")
    expect(btn?.className).toMatch(/destructive/)
  })

  it("supports default variant", () => {
    render(<ConfirmDialog {...defaultProps} variant="default" />)
    const btn = screen.getByText("Ta bort").closest("button")
    expect(btn?.className).not.toMatch(/bg-destructive/)
  })

  it("renders with custom title", () => {
    render(<ConfirmDialog {...defaultProps} title="Radera organisation" />)
    expect(screen.getByText("Radera organisation")).toBeInTheDocument()
  })

  it("renders with custom description", () => {
    render(<ConfirmDialog {...defaultProps} description="Alla system tas bort." />)
    expect(screen.getByText(/Alla system/)).toBeInTheDocument()
  })

  it("renders with Swedish characters in title", () => {
    render(<ConfirmDialog {...defaultProps} title="Ändra ägare för systemförvaltare" />)
    expect(screen.getByText("Ändra ägare för systemförvaltare")).toBeInTheDocument()
  })

  it("does not call onConfirm when loading and clicked", () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} loading={true} />)
    const btn = screen.getByText("Tar bort...").closest("button")
    if (btn) fireEvent.click(btn)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it("Avbryt button is always enabled even when loading", () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    const avbryt = screen.getByText("Avbryt").closest("button")
    expect(avbryt).not.toBeDisabled()
  })

  it("dialog has accessible role", () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })

  it("title is rendered as heading", () => {
    render(<ConfirmDialog {...defaultProps} />)
    const heading = screen.getByRole("heading", { name: "Bekräfta borttagning" })
    expect(heading).toBeInTheDocument()
  })
})
