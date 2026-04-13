import { Button } from "@/components/ui/button"
import { AlertCircleIcon } from "lucide-react"

interface Props {
  title?: string
  description?: string
  onRetry?: () => void
}

export function ErrorState({
  title = "Kunde inte hämta data",
  description = "Kontrollera att backend körs och försök igen.",
  onRetry,
}: Props) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      <AlertCircleIcon className="size-4 shrink-0" />
      <div className="flex-1">
        <p className="font-medium">{title}</p>
        {description && <p className="text-muted-foreground text-xs mt-0.5">{description}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Försök igen
        </Button>
      )}
    </div>
  )
}
