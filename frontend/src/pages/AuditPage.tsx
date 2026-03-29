import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronDownIcon, ChevronRightIcon, ClipboardListIcon } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getAuditLog } from "@/lib/api"
import type { AuditEntry, AuditResponse } from "@/types"

// ---------------------------------------------------------------------------
// Hjälpfunktioner
// ---------------------------------------------------------------------------

const ACTION_LABELS: Record<AuditEntry["action"], string> = {
  INSERT: "Skapad",
  UPDATE: "Ändrad",
  DELETE: "Borttagen",
}

const ACTION_VARIANT: Record<
  AuditEntry["action"],
  "default" | "secondary" | "destructive"
> = {
  INSERT: "default",
  UPDATE: "secondary",
  DELETE: "destructive",
}

const TABLE_LABELS: Record<string, string> = {
  systems: "System",
  organizations: "Organisation",
  owners: "Ägare",
  classifications: "Klassning",
  integrations: "Integration",
  contracts: "Avtal",
  gdpr_treatments: "GDPR",
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("sv-SE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

// ---------------------------------------------------------------------------
// JSON-diff-visning
// ---------------------------------------------------------------------------

function JsonDiff({
  oldValues,
  newValues,
}: {
  oldValues: Record<string, unknown> | null
  newValues: Record<string, unknown> | null
}) {
  if (!oldValues && !newValues) {
    return <p className="text-muted-foreground text-sm">Inga värden</p>
  }

  const allKeys = Array.from(
    new Set([
      ...Object.keys(oldValues ?? {}),
      ...Object.keys(newValues ?? {}),
    ])
  ).sort()

  if (allKeys.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {oldValues !== null && (
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase">
              Innan
            </p>
            <pre className="rounded bg-muted p-3 text-xs overflow-auto">
              {JSON.stringify(oldValues, null, 2)}
            </pre>
          </div>
        )}
        {newValues !== null && (
          <div>
            <p className="mb-1 text-xs font-semibold text-muted-foreground uppercase">
              Efter
            </p>
            <pre className="rounded bg-muted p-3 text-xs overflow-auto">
              {JSON.stringify(newValues, null, 2)}
            </pre>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="overflow-auto rounded border text-xs">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-3 py-2 text-left font-medium">Fält</th>
            <th className="px-3 py-2 text-left font-medium">Innan</th>
            <th className="px-3 py-2 text-left font-medium">Efter</th>
          </tr>
        </thead>
        <tbody>
          {allKeys.map((key) => {
            const before = oldValues?.[key]
            const after = newValues?.[key]
            const changed =
              JSON.stringify(before) !== JSON.stringify(after)
            return (
              <tr
                key={key}
                className={changed ? "bg-yellow-50 dark:bg-yellow-900/20" : ""}
              >
                <td className="px-3 py-1.5 font-mono text-muted-foreground">
                  {key}
                </td>
                <td className="px-3 py-1.5 font-mono">
                  {before === undefined ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={changed ? "text-red-600 dark:text-red-400" : ""}>
                      {JSON.stringify(before)}
                    </span>
                  )}
                </td>
                <td className="px-3 py-1.5 font-mono">
                  {after === undefined ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={changed ? "text-green-600 dark:text-green-400" : ""}>
                      {JSON.stringify(after)}
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Expanderbar rad
// ---------------------------------------------------------------------------

function AuditRow({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => { if (e.key === "Enter") setExpanded((v) => !v) }}
      >
        <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
          {formatDateTime(entry.changed_at)}
        </TableCell>
        <TableCell>
          {TABLE_LABELS[entry.table_name] ?? entry.table_name}
        </TableCell>
        <TableCell>
          <Badge variant={ACTION_VARIANT[entry.action]}>
            {ACTION_LABELS[entry.action]}
          </Badge>
        </TableCell>
        <TableCell className="text-sm">
          {entry.changed_by ?? <span className="text-muted-foreground">System</span>}
        </TableCell>
        <TableCell className="text-right">
          {expanded ? (
            <ChevronDownIcon className="size-4 inline text-muted-foreground" />
          ) : (
            <ChevronRightIcon className="size-4 inline text-muted-foreground" />
          )}
        </TableCell>
      </TableRow>
      {expanded && (
        <TableRow>
          <TableCell colSpan={5} className="bg-muted/30 p-4">
            <JsonDiff
              oldValues={entry.old_values}
              newValues={entry.new_values}
            />
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Huvudkomponent
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25

export default function AuditPage() {
  const [tableFilter, setTableFilter] = useState<string>("")
  const [actionFilter, setActionFilter] = useState<string>("")
  const [page, setPage] = useState(0)

  const { data, isLoading, isError } = useQuery<AuditResponse>({
    queryKey: ["audit-log", tableFilter, actionFilter, page],
    queryFn: () =>
      getAuditLog({
        table_name: tableFilter || undefined,
        action: actionFilter || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="space-y-4 p-6">
      {/* Rubrik */}
      <div className="flex items-center gap-2">
        <ClipboardListIcon className="size-5 text-muted-foreground" />
        <h1 className="text-2xl font-bold">Ändringslogg</h1>
      </div>
      <p className="text-muted-foreground text-sm">
        Alla skapade, ändrade och borttagna poster i systemregistret
      </p>

      {/* Filter */}
      <div className="flex flex-wrap gap-3">
        <Select
          value={tableFilter}
          onValueChange={(v) => {
            setTableFilter(v ?? "")
            setPage(0)
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Alla tabeller">
              {tableFilter
                ? (TABLE_LABELS[tableFilter] ?? tableFilter)
                : "Alla tabeller"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla tabeller</SelectItem>
            {Object.entries(TABLE_LABELS).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={actionFilter}
          onValueChange={(v) => {
            setActionFilter(v ?? "")
            setPage(0)
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Alla åtgärder">
              {actionFilter
                ? ACTION_LABELS[actionFilter as AuditEntry["action"]]
                : "Alla åtgärder"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla åtgärder</SelectItem>
            <SelectItem value="INSERT">Skapad</SelectItem>
            <SelectItem value="UPDATE">Ändrad</SelectItem>
            <SelectItem value="DELETE">Borttagen</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tabell */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            {data ? `${data.total} poster` : "Ändringar"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <p className="text-muted-foreground text-sm">Laddar ändringslogg…</p>
          )}
          {isError && (
            <p className="text-destructive text-sm">
              Kunde inte hämta ändringsloggen.
            </p>
          )}
          {data && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tidpunkt</TableHead>
                  <TableHead>Tabell</TableHead>
                  <TableHead>Åtgärd</TableHead>
                  <TableHead>Ändrad av</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="text-center text-muted-foreground"
                    >
                      Inga poster hittades
                    </TableCell>
                  </TableRow>
                ) : (
                  data.items.map((entry) => (
                    <AuditRow key={entry.id} entry={entry} />
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Paginering */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Sida {page + 1} av {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Föregående
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              Nästa
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
