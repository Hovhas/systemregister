import { useState, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { SearchIcon, Loader2Icon, PlusIcon, XIcon } from "lucide-react"

import {
  getEmploymentTemplates,
  createEmploymentTemplate,
  getOrganizations,
  getPositions,
  getBusinessRoles,
} from "@/lib/api"
import type { EmploymentTemplateCreate } from "@/types"
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

const emptyForm: EmploymentTemplateCreate = {
  organization_id: "",
  name: "",
  position_id: null,
  is_active: true,
  notes: null,
  role_ids: [],
}

export default function EmploymentTemplatesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState<EmploymentTemplateCreate>({ ...emptyForm })
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
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

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const { data: positions } = useQuery({
    queryKey: ["positions", "dialog", form.organization_id],
    queryFn: () =>
      getPositions({
        organization_id: form.organization_id || undefined,
        limit: 200,
      }),
    enabled: createOpen,
  })

  const { data: allRoles } = useQuery({
    queryKey: ["business-roles", "dialog", form.organization_id],
    queryFn: () =>
      getBusinessRoles({
        organization_id: form.organization_id || undefined,
        limit: 200,
      }),
    enabled: createOpen,
  })

  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name]),
  )
  const positionNameMap = Object.fromEntries(
    (positions?.items ?? []).map((p) => [p.id, p.title]),
  )

  const isSearching = searchInput !== debouncedSearch
  const hasFilters = !!(organization || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["employment-templates", debouncedSearch, organization, offset],
    queryFn: () =>
      getEmploymentTemplates({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const createMut = useMutation({
    mutationFn: (d: EmploymentTemplateCreate) => createEmploymentTemplate(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employment-templates"] })
      setCreateOpen(false)
      setForm({ ...emptyForm })
      setSelectedRoles([])
      toast.success("Anställningsmall skapad")
    },
    onError: () => toast.error("Kunde inte skapa anställningsmall"),
  })

  function toggleRole(roleId: string) {
    setSelectedRoles((prev) =>
      prev.includes(roleId)
        ? prev.filter((r) => r !== roleId)
        : [...prev, roleId],
    )
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    createMut.mutate({ ...form, role_ids: selectedRoles })
  }

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Anställningsmallar
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0
              ? `${total} mallar totalt`
              : "Inga anställningsmallar hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny mall
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-48 flex-1">
          {isSearching ? (
            <Loader2Icon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground animate-spin" />
          ) : (
            <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          )}
          <Input
            placeholder="Sök mallar..."
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

      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta anställningsmallar.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Namn</TableHead>
                <TableHead className="text-center">Version</TableHead>
                <TableHead>Befattning</TableHead>
                <TableHead className="text-center">Aktiv</TableHead>
                <TableHead className="text-center">Antal roller</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRowSkeleton key={i} />
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center py-12 text-muted-foreground"
                  >
                    Inga mallar matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((tmpl, idx) => (
                  <TableRow
                    key={tmpl.id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                    onClick={() =>
                      navigate(`/employment-templates/${tmpl.id}`)
                    }
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter")
                        navigate(`/employment-templates/${tmpl.id}`)
                    }}
                    aria-label={`Öppna anställningsmall ${tmpl.name}`}
                  >
                    <TableCell className="font-medium">{tmpl.name}</TableCell>
                    <TableCell className="text-center">{tmpl.version}</TableCell>
                    <TableCell>
                      {tmpl.position_id
                        ? (positionNameMap[tmpl.position_id] ?? "—")
                        : "—"}
                    </TableCell>
                    <TableCell className="text-center">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${tmpl.is_active ? "bg-green-100 text-green-800 border-green-200" : "bg-gray-100 text-gray-600 border-gray-200"}`}
                      >
                        {tmpl.is_active ? "Aktiv" : "Inaktiv"}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      {tmpl.role_ids.length}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

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

      {/* Create dialog */}
      <Dialog
        open={createOpen}
        onOpenChange={(open) => {
          if (!open) {
            setCreateOpen(false)
            setForm({ ...emptyForm })
            setSelectedRoles([])
          } else {
            setCreateOpen(true)
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Ny anställningsmall</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input
                required
                placeholder="Mallnamn"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Organisation *</label>
              <Select
                value={form.organization_id || undefined}
                onValueChange={(val) => {
                  setForm({ ...form, organization_id: val ?? "", position_id: null })
                  setSelectedRoles([])
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj organisation">
                    {form.organization_id
                      ? (orgs ?? []).find((o) => o.id === form.organization_id)?.name
                      : undefined}
                  </SelectValue>
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
              <label className="text-sm font-medium">Befattning</label>
              <Select
                value={form.position_id ?? undefined}
                onValueChange={(val) =>
                  setForm({ ...form, position_id: val ?? null })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj befattning (valfritt)">
                    {form.position_id
                      ? (positions?.items ?? []).find((p) => p.id === form.position_id)?.title
                      : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Ingen</SelectItem>
                  {(positions?.items ?? []).map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Multi-select roles */}
            {(allRoles?.items ?? []).length > 0 && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">
                  Verksamhetsroller
                </label>
                <div className="max-h-40 overflow-y-auto rounded border p-2 flex flex-col gap-1">
                  {(allRoles?.items ?? []).map((role) => (
                    <label
                      key={role.id}
                      className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 rounded px-1 py-0.5"
                    >
                      <input
                        type="checkbox"
                        checked={selectedRoles.includes(role.id)}
                        onChange={() => toggleRole(role.id)}
                        className="rounded"
                        aria-label={`Välj roll ${role.name}`}
                      />
                      {role.name}
                    </label>
                  ))}
                </div>
                {selectedRoles.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedRoles.length} roll{selectedRoles.length !== 1 ? "ar" : ""} valda
                  </p>
                )}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Anteckningar</label>
              <Input
                placeholder="Anteckningar"
                value={form.notes ?? ""}
                onChange={(e) =>
                  setForm({ ...form, notes: e.target.value || null })
                }
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setCreateOpen(false)
                  setForm({ ...emptyForm })
                  setSelectedRoles([])
                }}
              >
                Avbryt
              </Button>
              <Button
                type="submit"
                disabled={
                  createMut.isPending || !form.name || !form.organization_id
                }
              >
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
