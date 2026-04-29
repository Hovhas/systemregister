import { useState, useCallback, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { SearchIcon, Loader2Icon, PlusIcon, XIcon, PencilIcon, TrashIcon } from "lucide-react"

import {
  getPositions,
  createPosition,
  updatePosition,
  deletePosition,
  getOrganizations,
  getOrgUnits,
} from "@/lib/api"
import type { PositionCreate, PositionUpdate, Position } from "@/types"
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
import { ConfirmDialog } from "@/components/ConfirmDialog"

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 4 }).map((_, i) => (
        <TableCell key={i}>
          <div className="skeleton h-4 w-full max-w-[120px]" />
        </TableCell>
      ))}
    </TableRow>
  )
}

const PAGE_SIZE = 50

const emptyForm: PositionCreate = {
  organization_id: "",
  title: "",
  position_code: null,
  description: null,
  org_unit_id: null,
}

export default function PositionsPage() {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Position | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Position | null>(null)
  const [form, setForm] = useState<PositionCreate>({ ...emptyForm })
  const [editForm, setEditForm] = useState<PositionUpdate>({})
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

  const { data: orgUnits } = useQuery({
    queryKey: ["org-units", organization],
    queryFn: () => getOrgUnits({ organization_id: organization || undefined, limit: 200 }),
    enabled: true,
  })

  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name]),
  )
  const unitNameMap = Object.fromEntries(
    (orgUnits?.items ?? []).map((u) => [u.id, u.name]),
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
    queryKey: ["positions", debouncedSearch, organization, offset],
    queryFn: () =>
      getPositions({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const createMut = useMutation({
    mutationFn: (d: PositionCreate) => createPosition(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] })
      setCreateOpen(false)
      setForm({ ...emptyForm })
      toast.success("Befattning skapad")
    },
    onError: () => toast.error("Kunde inte skapa befattning"),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PositionUpdate }) =>
      updatePosition(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] })
      setEditTarget(null)
      toast.success("Befattning uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera befattning"),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deletePosition(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["positions"] })
      setDeleteTarget(null)
      toast.success("Befattning borttagen")
    },
    onError: () => toast.error("Kunde inte ta bort befattning"),
  })

  function openEdit(pos: Position) {
    setEditTarget(pos)
    setEditForm({
      title: pos.title,
      position_code: pos.position_code,
      description: pos.description,
      org_unit_id: pos.org_unit_id,
    })
  }

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Befattningar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} befattningar totalt` : "Inga befattningar hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny befattning
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
            placeholder="Sök befattningar..."
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
          <p>Kunde inte hämta befattningar.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Titel</TableHead>
                <TableHead>Befattningskod</TableHead>
                <TableHead>Organisationsenhet</TableHead>
                <TableHead />
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
                    colSpan={4}
                    className="text-center py-12 text-muted-foreground"
                  >
                    Inga befattningar matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((pos, idx) => (
                  <TableRow
                    key={pos.id}
                    className={idx % 2 === 1 ? "bg-muted/20" : ""}
                  >
                    <TableCell className="font-medium">{pos.title}</TableCell>
                    <TableCell>{pos.position_code ?? "—"}</TableCell>
                    <TableCell>
                      {pos.org_unit_id
                        ? (unitNameMap[pos.org_unit_id] ?? pos.org_unit_id)
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEdit(pos)}
                          aria-label={`Redigera befattning ${pos.title}`}
                        >
                          <PencilIcon className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleteTarget(pos)}
                          aria-label={`Ta bort befattning ${pos.title}`}
                        >
                          <TrashIcon className="size-4" />
                        </Button>
                      </div>
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
          } else {
            setCreateOpen(true)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny befattning</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMut.mutate(form)
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Titel *</label>
              <Input
                required
                placeholder="Befattningstitel"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Organisation *</label>
              <Select
                value={form.organization_id || undefined}
                onValueChange={(val) =>
                  setForm({ ...form, organization_id: val ?? "" })
                }
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
              <label className="text-sm font-medium">Befattningskod</label>
              <Input
                placeholder="t.ex. 1234"
                value={form.position_code ?? ""}
                onChange={(e) =>
                  setForm({ ...form, position_code: e.target.value || null })
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input
                placeholder="Beskrivning"
                value={form.description ?? ""}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value || null })
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
                }}
              >
                Avbryt
              </Button>
              <Button
                type="submit"
                disabled={
                  createMut.isPending ||
                  !form.title ||
                  !form.organization_id
                }
              >
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog
        open={!!editTarget}
        onOpenChange={(open) => {
          if (!open) setEditTarget(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera befattning</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (editTarget)
                updateMut.mutate({ id: editTarget.id, data: editForm })
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Titel *</label>
              <Input
                required
                value={editForm.title ?? ""}
                onChange={(e) =>
                  setEditForm({ ...editForm, title: e.target.value })
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Befattningskod</label>
              <Input
                value={editForm.position_code ?? ""}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    position_code: e.target.value || null,
                  })
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input
                value={editForm.description ?? ""}
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    description: e.target.value || null,
                  })
                }
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditTarget(null)}
              >
                Avbryt
              </Button>
              <Button
                type="submit"
                disabled={updateMut.isPending || !editForm.title}
              >
                {updateMut.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="Ta bort befattning"
        description={`Är du säker på att du vill ta bort "${deleteTarget?.title}"?`}
        onConfirm={() => {
          if (deleteTarget) deleteMut.mutate(deleteTarget.id)
        }}
        loading={deleteMut.isPending}
      />
    </div>
  )
}
