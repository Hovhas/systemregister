import { TableRow, TableCell } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { InboxIcon } from "lucide-react"

interface Props {
  columns: number
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ columns, title, description, actionLabel, onAction }: Props) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="text-center py-12">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <InboxIcon className="size-12 opacity-30" />
          <div>
            <p className="font-medium text-foreground">{title}</p>
            {description && <p className="text-sm mt-1">{description}</p>}
          </div>
          {actionLabel && onAction && (
            <Button variant="outline" size="sm" onClick={onAction} className="mt-2">
              {actionLabel}
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}
