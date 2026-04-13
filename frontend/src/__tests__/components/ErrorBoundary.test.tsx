/**
 * Testsvit: ErrorBoundary-komponent
 */

import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ErrorBoundary } from "@/components/ErrorBoundary"

// Komponent som alltid kastar fel
function ThrowingChild(): JSX.Element {
  throw new Error("Test error!")
}

// Undertryck React console.error vid förväntade fel
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

describe("ErrorBoundary", () => {
  it("renderar children när inget fel uppstår", () => {
    render(
      <ErrorBoundary>
        <p>Allt fungerar</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText("Allt fungerar")).toBeInTheDocument()
  })

  it("renderar fallback-UI när child kastar fel", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText(/något gick fel/i)).toBeInTheDocument()
  })

  it("visar felmeddelandet i fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText("Test error!")).toBeInTheDocument()
  })

  it("custom fallback-prop åsidosätter standard", () => {
    render(
      <ErrorBoundary fallback={<div>Egen felvy</div>}>
        <ThrowingChild />
      </ErrorBoundary>,
    )
    expect(screen.getByText("Egen felvy")).toBeInTheDocument()
    expect(screen.queryByText(/något gick fel/i)).not.toBeInTheDocument()
  })

  it("Ladda om-knapp finns i standard-fallback", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    )
    expect(screen.getByRole("button", { name: /ladda om sidan/i })).toBeInTheDocument()
  })
})
