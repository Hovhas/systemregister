import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { SearchIcon, PlusIcon, ChevronUpIcon, ChevronDownIcon, XIcon, Loader2Icon } from "lucide-react"

import { getSystems, getOrganizations } from "@/lib/api"
import { SystemCategory, LifecycleStatus, Criticality } from "@/types"
import { categoryLabels, lifecycleLabels, criticalityLabels, criticalityBadgeClass } from "@/lib/labels"
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

function CriticalityBadge({ value }: { value: Criticality }) {
  const colorClass = criticalityBadgeClass[value]

  return (
    <span
      className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${colorClass}`}
    >
      {criticalityLabels[value]}
    </span>
  )
}

function Nis2Badge({ applicable }: { applicable: boolean }) {
  return applicable ? (
    <Badge variant="default">Ja</Badge>
  ) : (
    <Badge variant="outline">Nej</Badge>
  )
}

const PAGE_SIZE = 25

export default function SystemsPage() {
  const navigate = useNavigate()
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [organization, setOrganization] = useState("")
  const [category, setCategory] = useState<SystemCategory | "">("")
  const [lifecycle, setLifecycle] = useState<LifecycleStatus | "">("")
  const [criticality, setCriticality] = useState<Criticality | "">("")
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
  const hasFilters = !!(organization || category || lifecycle || criticality || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setCategory("")
    setLifecycle("")
    setCriticality("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      "systems",
      debouncedSearch,
      organization,
      category,
      lifecycle,
      criticality,
      offset,
      sortField,
      sortDir,
    ],
    queryFn: () =>
      getSystems({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        system_category: category || undefined,
        lifecycle_status: lifecycle || undefined,
        criticality: criticality || undefined,
        limit: PAGE_SIZE,
        offset,
        sort_by: sortField,
        sort_dir: sortDir,
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
          <h1 className="text-2xl font-bold tracking-tight">System</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} system totalt` : "Inga system hittade"}
          </p>
        </div>
        <Button onClick={() => navigate("/systems/new")}>
          <PlusIcon className="mr-1.5 size-4" /> Nytt system
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
            placeholder="Sök system..."
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
          value={category as string}
          onValueChange={(val) => {
            setCategory(val as SystemCategory | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Kategori">
              {category ? categoryLabels[category as SystemCategory] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla kategorier</SelectItem>
            {Object.values(SystemCategory).map((cat) => (
              <SelectItem key={cat} value={cat}>
                {categoryLabels[cat]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={lifecycle as string}
          onValueChange={(val) => {
            setLifecycle(val as LifecycleStatus | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Livscykelstatus">
              {lifecycle ? lifecycleLabels[lifecycle as LifecycleStatus] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla statusar</SelectItem>
            {Object.values(LifecycleStatus).map((s) => (
              <SelectItem key={s} value={s}>
                {lifecycleLabels[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={criticality as string}
          onValueChange={(val) => {
            setCriticality(val as Criticality | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Kritikalitet">
              {criticality ? criticalityLabels[criticality as Criticality] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla nivåer</SelectItem>
            {Object.values(Criticality).map((c) => (
              <SelectItem key={c} value={c}>
                {criticalityLabels[c]}
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
          <p>Kunde inte hämta system. Kontrollera att backend körs.</p>
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
                <SortHeader field="system_category" label="Kategori" />
                <SortHeader field="criticality" label="Kritikalitet" />
                <SortHeader field="lifecycle_status" label="Status" />
                <TableHead>NIS2</TableHead>
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
                    Inga system matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((system, idx) => (
                  <TableRow
                    key={system.id}
                    className={`cursor-pointer transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                    tabIndex={0}
                    onClick={() => navigate(`/systems/${system.id}`)}
                    onKeyDown={(e) => { if (e.key === "Enter") navigate(`/systems/${system.id}`) }}
                  >
                    <TableCell className="font-medium">{system.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {orgNameMap[system.organization_id] ?? system.organization_id}
                    </TableCell>
                    <TableCell>
                      {categoryLabels[system.system_category]}
                    </TableCell>
                    <TableCell>
                      <CriticalityBadge value={system.criticality} />
                    </TableCell>
                    <TableCell>
                      {lifecycleLabels[system.lifecycle_status]}
                    </TableCell>
                    <TableCell>
                      <Nis2Badge applicable={system.nis2_applicable} />
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
    </div>
  )
}
