import { Component, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangleIcon } from "lucide-react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="flex min-h-screen items-center justify-center p-6">
          <div className="max-w-md rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-center">
            <AlertTriangleIcon className="mx-auto size-10 text-destructive mb-3" />
            <h2 className="text-lg font-semibold mb-2">Något gick fel</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Ett oväntat fel uppstod. Försök ladda om sidan eller kontakta support om felet kvarstår.
            </p>
            {this.state.error && (
              <pre className="text-xs text-left bg-muted/50 rounded p-2 mb-4 overflow-auto max-h-40">
                {this.state.error.message}
              </pre>
            )}
            <Button onClick={() => window.location.reload()}>Ladda om sidan</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
