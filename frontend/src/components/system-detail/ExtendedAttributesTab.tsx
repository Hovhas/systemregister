import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function formatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function ExtendedAttributesTab({ attributes }: { attributes: Record<string, unknown> | null }) {
  if (!attributes || Object.keys(attributes).length === 0) {
    return <p className="text-sm text-muted-foreground py-4">Ingen övrig data registrerad</p>
  }

  const entries = Object.entries(attributes).sort(([a], [b]) => a.localeCompare(b, "sv"))

  return (
    <div className="rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Fält</TableHead>
            <TableHead>Värde</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key}>
              <TableCell className="font-medium text-sm">{formatKey(key)}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {value === null || value === undefined ? "—" : String(value)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
