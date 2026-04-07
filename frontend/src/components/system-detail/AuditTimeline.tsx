import { useQuery } from "@tanstack/react-query"
import { getAuditForRecord } from "@/lib/api"
import type { AuditEntry } from "@/types"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
} from "@/components/ui/card"

export function AuditTimeline({ systemId }: { systemId: string }) {
  const { data: entries, isLoading } = useQuery({
    queryKey: ["audit", systemId],
    queryFn: () => getAuditForRecord(systemId),
  })

  if (isLoading) return <p className="text-sm text-muted-foreground">Laddar...</p>
  if (!entries?.length) return <p className="text-sm text-muted-foreground py-4">Inga ändringar registrerade</p>

  return (
    <div className="space-y-3">
      {entries.map((entry: AuditEntry) => (
        <Card key={entry.id}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={entry.action === "INSERT" ? "default" : entry.action === "DELETE" ? "destructive" : "secondary"}>
                {entry.action === "INSERT" ? "Skapad" : entry.action === "UPDATE" ? "Ändrad" : "Borttagen"}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(entry.changed_at).toLocaleString("sv-SE")}
              </span>
              {entry.changed_by && <span className="text-xs">av {entry.changed_by}</span>}
            </div>
            {entry.action === "UPDATE" && entry.old_values && entry.new_values && (
              <div className="text-xs space-y-1 mt-2">
                {Object.keys(entry.new_values!).map((key: string) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-medium min-w-24">{key}:</span>
                    <span className="text-red-600 line-through">{String(entry.old_values![key] ?? "—")}</span>
                    <span>-&gt;</span>
                    <span className="text-green-600">{String(entry.new_values![key] ?? "—")}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
