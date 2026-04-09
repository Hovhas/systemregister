import { useState, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { SearchIcon, ChevronUpIcon, ChevronDownIcon, XIcon, Loader2Icon, PlusIcon } from "lucide-react"

import { getModules, getOrganizations, createModule } from "@/lib/api"
import { LifecycleStatus, AIRiskClass } from "@/types"
import type { ModuleCreate } from "@/types"
import { lifecycleLabels, aiRiskClassLabels, aiRiskBadgeClass } from "@/lib/labels"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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
      {Array.from({ length: 6 }).map((_, i) => (
        <TableCell key={i}>
          <div className="skeleton h-4 w-full max-w-[120px]" />
        </TableCell>
      ))}
    </TableRow>
  )
}

// --- Hjälpkomponenter ---

function AIRiskBadge({ value }: { value: AIRiskClass }) {
  const colorClass = aiRiskBadgeClass[value]
  return (
    <span
      className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${colorClass}`}
    >
      {aiRiskClassLabels[value]}
    </span>
  )
}

const PAGE_SIZE = 50

const emptyModuleForm: ModuleCreate = {
  name: "",
  organization_id: "",
  description: "",
  lifecycle_status: undefined,
  uses_ai: false,
  ai_risk_class: undefined,
}

export default function ModulesPage() {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [newModule, setNewModule] = useState<ModuleCreate>({ ...emptyModuleForm })

  const createMut = useMutation({
    mutationFn: (data: ModuleCreate) => createModule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modules"] })
      setCreateOpen(false)
      setNewModule({ ...emptyModuleForm })
      toast.success("Modul skapad")
    },
    onError: () => toast.error("Kunde inte skapa modul"),
  })

  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [organization, setOrganization] = useState("")
  const [offset, setOffset] = useState(0)
  const [sortField, setSortField] = useState<string>("name")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")

  // Debounce sökning 300ms
  const debounceRef = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>
      return (value: string) => {
        clearTimeout(timer)
        timer = setTimeout(() => {
          setDebouncedSearch(value)
          setOffset(0)
        }, 300)
      }
    })(),
    []
  )

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

  const isSearching = searchInput !== debouncedSearch
  const hasFilters = !!(organization || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["modules", debouncedSearch, organization, offset],
    queryFn: () =>
      getModules({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  function SortHeader({ field, label }: { field: string; label: string }) {
    const active = sortField === field
    return (
      <TableHead
        className="cursor-pointer select-none hover:text-foreground transition-colors"
        onClick={() => {
          if (active) setSortDir((d) => (d === "asc" ? "desc" : "asc"))
          else {
            setSortField(field)
            setSortDir("asc")
          }
          setOffset(0)
        }}
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
          <h1 className="text-2xl font-bold tracking-tight">Moduler</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} moduler totalt` : "Inga moduler hittade"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny modul
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
            placeholder="Sök moduler..."
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

      {/* Tabell */}
      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta moduler. Kontrollera att backend körs.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <SortHeader field="name" label="Namn" />
                <SortHeader field="organization_id" label="Organisation" />
                <TableHead>Status</TableHead>
                <TableHead>Produkt</TableHead>
                <TableHead>AI</TableHead>
                <TableHead>AI-riskklass</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRowSkeleton key={i} />
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    Inga moduler matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((mod, idx) => (
                  <TableRow
                    key={mod.id}
                    className={`transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                  >
                    <TableCell className="font-medium">{mod.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {orgNameMap[mod.organization_id] ?? mod.organization_id}
                    </TableCell>
                    <TableCell>
                      {mod.lifecycle_status
                        ? lifecycleLabels[mod.lifecycle_status as LifecycleStatus] ?? mod.lifecycle_status
                        : "—"}
                    </TableCell>
                    <TableCell>{mod.product_name ?? "—"}</TableCell>
                    <TableCell>
                      {mod.uses_ai ? (
                        <Badge variant="default">Ja</Badge>
                      ) : (
                        <Badge variant="outline">Nej</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {mod.ai_risk_class ? (
                        <AIRiskBadge value={mod.ai_risk_class as AIRiskClass} />
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
      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); setNewModule({ ...emptyModuleForm }) } else { setCreateOpen(true) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny modul</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMut.mutate(newModule)
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input
                required
                placeholder="Modulnamn"
                value={newModule.name}
                onChange={(e) => setNewModule({ ...newModule, name: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Organisation *</label>
              <Select
                value={newModule.organization_id || undefined}
                onValueChange={(val) => setNewModule({ ...newModule, organization_id: val ?? "" })}
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
                value={newModule.description ?? ""}
                onChange={(e) => setNewModule({ ...newModule, description: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Livscykelstatus</label>
              <Select
                value={newModule.lifecycle_status ?? ""}
                onValueChange={(val) => setNewModule({ ...newModule, lifecycle_status: val ? (val as LifecycleStatus) : undefined })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Ingen</SelectItem>
                  {Object.values(LifecycleStatus).map((s) => (
                    <SelectItem key={s} value={s}>
                      {lifecycleLabels[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="create-uses-ai"
                checked={newModule.uses_ai ?? false}
                onChange={(e) => setNewModule({ ...newModule, uses_ai: e.target.checked, ai_risk_class: e.target.checked ? newModule.ai_risk_class : undefined })}
                className="size-4 rounded border"
              />
              <label htmlFor="create-uses-ai" className="text-sm font-medium">Använder AI</label>
            </div>
            {newModule.uses_ai && (
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">AI-riskklass</label>
                <Select
                  value={newModule.ai_risk_class ?? ""}
                  onValueChange={(val) => setNewModule({ ...newModule, ai_risk_class: val ? (val as AIRiskClass) : undefined })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Välj riskklass" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Ingen</SelectItem>
                    {Object.values(AIRiskClass).map((r) => (
                      <SelectItem key={r} value={r}>
                        {aiRiskClassLabels[r]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setCreateOpen(false); setNewModule({ ...emptyModuleForm }) }}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMut.isPending || !newModule.name || !newModule.organization_id}>
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
