import { useState, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { SearchIcon, Loader2Icon, PlusIcon, XIcon } from "lucide-react"

import { getCapabilities, getOrganizations, createCapability } from "@/lib/api"
import type { CapabilityCreate } from "@/types"
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

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 6 }).map((_, i) => (
        <TableCell key={i}><div className="skeleton h-4 w-full max-w-[120px]" /></TableCell>
      ))}
    </TableRow>
  )
}

const PAGE_SIZE = 50

const emptyForm: CapabilityCreate = {
  organization_id: "",
  name: "",
  description: null,
  capability_owner: null,
  maturity_level: null,
  parent_capability_id: null,
}

export default function CapabilitiesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState<CapabilityCreate>({ ...emptyForm })
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [organization, setOrganization] = useState("")
  const [offset, setOffset] = useState(0)
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const debounceRef = useCallback((value: string) => {
    clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setDebouncedSearch(value)
      setOffset(0)
    }, 300)
  }, [])

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchInput(e.target.value)
    debounceRef(e.target.value)
  }

  const { data: orgs } = useQuery({ queryKey: ["organizations"], queryFn: getOrganizations })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  const isSearching = searchInput !== debouncedSearch
  const hasFilters = !!(organization || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["capabilities", debouncedSearch, organization, offset],
    queryFn: () => getCapabilities({ q: debouncedSearch || undefined, organization_id: organization || undefined, limit: PAGE_SIZE, offset }),
  })

  const createMut = useMutation({
    mutationFn: (data: CapabilityCreate) => createCapability(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capabilities"] })
      setCreateOpen(false)
      setForm({ ...emptyForm })
      toast.success("Förmåga skapad")
    },
    onError: () => toast.error("Kunde inte skapa förmåga"),
  })

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Förmågor</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} förmågor totalt` : "Inga förmågor hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny förmåga
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-48 flex-1">
          {isSearching ? (
            <Loader2Icon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground animate-spin" />
          ) : (
            <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          )}
          <Input placeholder="Sök förmågor..." value={searchInput} onChange={handleSearchChange} className="pl-9" />
        </div>
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
        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="shrink-0 text-muted-foreground hover:text-foreground">
            <XIcon className="mr-1 size-4" />Rensa
          </Button>
        )}
      </div>

      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta förmågor.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Namn</TableHead>
                <TableHead>Beskrivning</TableHead>
                <TableHead>Ägare</TableHead>
                <TableHead className="text-center">Mognad</TableHead>
                <TableHead className="text-center">System</TableHead>
                <TableHead className="text-center">Processer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} />)
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    Inga förmågor matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((cap, idx) => (
                  <TableRow
                    key={cap.id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                    onClick={() => navigate(`/capabilities/${cap.id}`)}
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") navigate(`/capabilities/${cap.id}`) }}
                    aria-label={`Öppna förmåga ${cap.name}`}
                  >
                    <TableCell className="font-medium">{cap.name}</TableCell>
                    <TableCell className="text-muted-foreground max-w-xs truncate">{cap.description ?? "—"}</TableCell>
                    <TableCell>{cap.capability_owner ?? "—"}</TableCell>
                    <TableCell className="text-center">{cap.maturity_level ?? "—"}</TableCell>
                    <TableCell className="text-center">{cap.system_count ?? 0}</TableCell>
                    <TableCell className="text-center">{cap.process_count ?? 0}</TableCell>
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
            <DialogTitle>Ny förmåga</DialogTitle>
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
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Ägare</label>
              <Input placeholder="Förmågeägare" value={form.capability_owner ?? ""} onChange={(e) => setForm({ ...form, capability_owner: e.target.value || null })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Mognadsnivå (1–5)</label>
              <Select value={form.maturity_level != null ? String(form.maturity_level) : ""} onValueChange={(val) => setForm({ ...form, maturity_level: val ? Number(val) : null })}>
                <SelectTrigger><SelectValue placeholder="Välj nivå">{form.maturity_level != null ? String(form.maturity_level) : undefined}</SelectValue></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Ingen</SelectItem>
                  {[1, 2, 3, 4, 5].map((v) => <SelectItem key={v} value={String(v)}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
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
