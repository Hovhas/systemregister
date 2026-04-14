import { useState, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { SearchIcon, ChevronUpIcon, ChevronDownIcon, XIcon, Loader2Icon, ExternalLinkIcon, PlusIcon } from "lucide-react"

import { getComponents, getOrganizations, getSystems, createComponent } from "@/lib/api"
import type { ComponentCreate } from "@/types"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

// --- Skeleton ---

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableCell key={i}>
          <div className="skeleton h-4 w-full max-w-[120px]" />
        </TableCell>
      ))}
    </TableRow>
  )
}

const PAGE_SIZE = 50

const emptyComponentForm: ComponentCreate = {
  name: "",
  system_id: "",
  organization_id: "",
  description: "",
  component_type: "",
  url: "",
  business_area: "",
}

export default function ComponentsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [newComponent, setNewComponent] = useState<ComponentCreate>({ ...emptyComponentForm })

  const createMut = useMutation({
    mutationFn: (data: ComponentCreate) => createComponent(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["components"] })
      setCreateOpen(false)
      setNewComponent({ ...emptyComponentForm })
      toast.success("Komponent skapad")
    },
    onError: () => toast.error("Kunde inte skapa komponent"),
  })

  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [organization, setOrganization] = useState("")
  const [systemFilter, setSystemFilter] = useState("")
  const [offset, setOffset] = useState(0)
  const [sortField, setSortField] = useState<string>("name")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")

  // Debounce sökning 300ms
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

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name])
  )

  const { data: systemsData } = useQuery({
    queryKey: ["systems", "all"],
    queryFn: () => getSystems({ limit: 200 }),
  })
  const systemNameMap = Object.fromEntries(
    (systemsData?.items ?? []).map((s) => [s.id, s.name])
  )

  const isSearching = searchInput !== debouncedSearch
  const hasFilters = !!(organization || systemFilter || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setSystemFilter("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["components", debouncedSearch, organization, systemFilter, offset],
    queryFn: () =>
      getComponents({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        system_id: systemFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  function handleSort(field: string) {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    else {
      setSortField(field)
      setSortDir("asc")
    }
    setOffset(0)
  }

  function renderSortHeader(field: string, label: string) {
    const active = sortField === field
    return (
      <TableHead
        className="cursor-pointer select-none hover:text-foreground transition-colors"
        onClick={() => handleSort(field)}
      >
        <span className="flex items-center gap-1">
          {label}
          {active &&
            (sortDir === "asc" ? (
              <ChevronUpIcon className="size-3" />
            ) : (
              <ChevronDownIcon className="size-3" />
            ))}
        </span>
      </TableHead>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Komponenter</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} komponenter totalt` : "Inga komponenter hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny komponent
        </Button>
      </div>

      {/* Filter-rad */}
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-48 flex-1">
          {isSearching ? (
            <Loader2Icon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground animate-spin" />
          ) : (
            <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          )}
          <Input
            placeholder="Sök komponenter..."
            value={searchInput}
            onChange={handleSearchChange}
            className="pl-9"
          />
        </div>

        <Select
          value={organization || undefined}
          onValueChange={(val) => {
            setOrganization(val ?? "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Organisation">
              {organization ? orgNameMap[organization] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla organisationer</SelectItem>
            {(orgs ?? []).map((org) => (
              <SelectItem key={org.id} value={org.id}>
                {org.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={systemFilter || undefined}
          onValueChange={(val) => {
            setSystemFilter(val ?? "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-52">
            <SelectValue placeholder="System">
              {systemFilter ? systemNameMap[systemFilter] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla system</SelectItem>
            {(systemsData?.items ?? []).map((sys) => (
              <SelectItem key={sys.id} value={sys.id}>
                {sys.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <XIcon className="mr-1 size-4" />
            Rensa
          </Button>
        )}
      </div>

      {/* Tabell */}
      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta komponenter. Kontrollera att backend körs.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                {renderSortHeader("name", "Namn")}
                <TableHead>System</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Verksamhetsområde</TableHead>
                <TableHead>URL</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRowSkeleton key={i} />
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                    Inga komponenter matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((component, idx) => (
                  <TableRow
                    key={component.id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                    onClick={() => navigate(`/systems/${component.system_id}`)}
                  >
                    <TableCell className="font-medium">{component.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {systemNameMap[component.system_id] ?? component.system_id}
                    </TableCell>
                    <TableCell>{component.component_type ?? "—"}</TableCell>
                    <TableCell>{component.business_area ?? "—"}</TableCell>
                    <TableCell>
                      {component.url ? (
                        <a
                          href={component.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Länk
                          <ExternalLinkIcon className="size-3" />
                        </a>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Paginering */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-muted-foreground">
            Sida {currentPage} av {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Föregående
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Nästa
            </Button>
          </div>
        </div>
      )}

      {/* Skapa-dialog */}
      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); setNewComponent({ ...emptyComponentForm }) } else { setCreateOpen(true) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny komponent</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMut.mutate(newComponent)
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input
                required
                placeholder="Komponentnamn"
                value={newComponent.name}
                onChange={(e) => setNewComponent({ ...newComponent, name: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">System *</label>
              <Select
                value={newComponent.system_id || undefined}
                onValueChange={(val) => setNewComponent({ ...newComponent, system_id: val ?? "" })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj system" />
                </SelectTrigger>
                <SelectContent>
                  {(systemsData?.items ?? []).map((sys) => (
                    <SelectItem key={sys.id} value={sys.id}>
                      {sys.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Organisation *</label>
              <Select
                value={newComponent.organization_id || undefined}
                onValueChange={(val) => setNewComponent({ ...newComponent, organization_id: val ?? "" })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj organisation" />
                </SelectTrigger>
                <SelectContent>
                  {(orgs ?? []).map((org) => (
                    <SelectItem key={org.id} value={org.id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input
                placeholder="Beskrivning"
                value={newComponent.description ?? ""}
                onChange={(e) => setNewComponent({ ...newComponent, description: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Typ</label>
              <Input
                placeholder="Komponenttyp"
                value={newComponent.component_type ?? ""}
                onChange={(e) => setNewComponent({ ...newComponent, component_type: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">URL</label>
              <Input
                placeholder="https://..."
                value={newComponent.url ?? ""}
                onChange={(e) => setNewComponent({ ...newComponent, url: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Verksamhetsområde</label>
              <Input
                placeholder="Verksamhetsområde"
                value={newComponent.business_area ?? ""}
                onChange={(e) => setNewComponent({ ...newComponent, business_area: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setCreateOpen(false); setNewComponent({ ...emptyComponentForm }) }}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMut.isPending || !newComponent.name || !newComponent.system_id || !newComponent.organization_id}>
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
