import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { PlusIcon } from "lucide-react"

import { getValueStreams, getOrganizations, createValueStream } from "@/lib/api"
import type { ValueStreamCreate } from "@/types"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { formatDate } from "@/lib/format"

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 4 }).map((_, i) => (
        <TableCell key={i}><div className="skeleton h-4 w-full max-w-[120px]" /></TableCell>
      ))}
    </TableRow>
  )
}

const PAGE_SIZE = 50

const emptyForm: ValueStreamCreate = {
  organization_id: "",
  name: "",
  description: null,
}

export default function ValueStreamsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState<ValueStreamCreate>({ ...emptyForm })
  const [organization, setOrganization] = useState("")
  const [offset, setOffset] = useState(0)

  const { data: orgs } = useQuery({ queryKey: ["organizations"], queryFn: getOrganizations })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["value-streams", organization, offset],
    queryFn: () => getValueStreams({ organization_id: organization || undefined, limit: PAGE_SIZE, offset }),
  })

  const createMut = useMutation({
    mutationFn: (data: ValueStreamCreate) => createValueStream(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["value-streams"] })
      setCreateOpen(false)
      setForm({ ...emptyForm })
      toast.success("Värdeström skapad")
    },
    onError: () => toast.error("Kunde inte skapa värdeström"),
  })

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Värdeströmmar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} värdeströmmar totalt` : "Inga värdeströmmar hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny värdeström
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select value={organization || undefined} onValueChange={(val) => { setOrganization(val ?? ""); setOffset(0) }}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Organisation">
              {organization ? orgNameMap[organization] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla organisationer</SelectItem>
            {(orgs ?? []).map((org) => (
              <SelectItem key={org.id} value={org.id}>{org.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta värdeströmmar.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Namn</TableHead>
                <TableHead>Beskrivning</TableHead>
                <TableHead className="text-center">Steg</TableHead>
                <TableHead>Uppdaterad</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} />)
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-12 text-muted-foreground">
                    Inga värdeströmmar hittade
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((vs, idx) => (
                  <TableRow
                    key={vs.id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                    onClick={() => navigate(`/value-streams/${vs.id}`)}
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") navigate(`/value-streams/${vs.id}`) }}
                    aria-label={`Öppna värdeström ${vs.name}`}
                  >
                    <TableCell className="font-medium">{vs.name}</TableCell>
                    <TableCell className="text-muted-foreground max-w-xs truncate">{vs.description ?? "—"}</TableCell>
                    <TableCell className="text-center">{vs.stages?.length ?? 0}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(vs.updated_at)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-muted-foreground">Sida {currentPage} av {totalPages}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              Föregående
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Nästa
            </Button>
          </div>
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); setForm({ ...emptyForm }) } else { setCreateOpen(true) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny värdeström</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(form) }} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required placeholder="Namn" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Organisation *</label>
              <Select value={form.organization_id || undefined} onValueChange={(val) => setForm({ ...form, organization_id: val ?? "" })}>
                <SelectTrigger>
                  <SelectValue placeholder="Välj organisation">
                    {form.organization_id ? (orgs ?? []).find((o) => o.id === form.organization_id)?.name : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {(orgs ?? []).map((org) => (
                    <SelectItem key={org.id} value={org.id}>{org.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input placeholder="Beskrivning" value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value || null })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setCreateOpen(false); setForm({ ...emptyForm }) }}>Avbryt</Button>
              <Button type="submit" disabled={createMut.isPending || !form.name || !form.organization_id}>
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
