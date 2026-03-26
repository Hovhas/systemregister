import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { SearchIcon } from "lucide-react"

import { getSystems } from "@/lib/api"
import { SystemCategory, LifecycleStatus, Criticality } from "@/types"
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

// --- Etiketter ---

const categoryLabels: Record<SystemCategory, string> = {
  [SystemCategory.VERKSAMHETSSYSTEM]: "Verksamhetssystem",
  [SystemCategory.STODSYSTEM]: "Stödsystem",
  [SystemCategory.INFRASTRUKTUR]: "Infrastruktur",
  [SystemCategory.PLATTFORM]: "Plattform",
  [SystemCategory.IOT]: "IoT",
}

const lifecycleLabels: Record<LifecycleStatus, string> = {
  [LifecycleStatus.PLANNED]: "Planerad",
  [LifecycleStatus.IMPLEMENTING]: "Under införande",
  [LifecycleStatus.ACTIVE]: "I drift",
  [LifecycleStatus.DECOMMISSIONING]: "Under avveckling",
  [LifecycleStatus.DECOMMISSIONED]: "Avvecklad",
}

const criticalityLabels: Record<Criticality, string> = {
  [Criticality.LOW]: "Låg",
  [Criticality.MEDIUM]: "Medel",
  [Criticality.HIGH]: "Hög",
  [Criticality.CRITICAL]: "Kritisk",
}

// --- Hjälpkomponenter ---

function CriticalityBadge({ value }: { value: Criticality }) {
  const colorClass = {
    [Criticality.CRITICAL]: "bg-red-100 text-red-800 border-red-200",
    [Criticality.HIGH]: "bg-orange-100 text-orange-800 border-orange-200",
    [Criticality.MEDIUM]: "bg-yellow-100 text-yellow-800 border-yellow-200",
    [Criticality.LOW]: "bg-green-100 text-green-800 border-green-200",
  }[value]

  return (
    <span
      className={`inline-flex h-5 items-center rounded-full border px-2 py-0.5 text-xs font-medium ${colorClass}`}
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
  const [category, setCategory] = useState<SystemCategory | "">("")
  const [lifecycle, setLifecycle] = useState<LifecycleStatus | "">("")
  const [criticality, setCriticality] = useState<Criticality | "">("")
  const [offset, setOffset] = useState(0)

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

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      "systems",
      debouncedSearch,
      category,
      lifecycle,
      criticality,
      offset,
    ],
    queryFn: () =>
      getSystems({
        q: debouncedSearch || undefined,
        system_category: category || undefined,
        lifecycle_status: lifecycle || undefined,
        criticality: criticality || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">System</h1>
        <p className="text-sm text-muted-foreground">
          {total > 0 ? `${total} system totalt` : "Inga system hittade"}
        </p>
      </div>

      {/* Filter-rad */}
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-48 flex-1">
          <SearchIcon className="absolute left-2 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Sök system..."
            value={searchInput}
            onChange={handleSearchChange}
            className="pl-8"
          />
        </div>

        <Select
          value={category}
          onValueChange={(val) => {
            setCategory(val as SystemCategory | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Kategori" />
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
          value={lifecycle}
          onValueChange={(val) => {
            setLifecycle(val as LifecycleStatus | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Livscykelstatus" />
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
          value={criticality}
          onValueChange={(val) => {
            setCriticality(val as Criticality | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Kritikalitet" />
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
      </div>

      {/* Tabell */}
      {isError ? (
        <p className="text-sm text-destructive">
          Kunde inte hämta system. Kontrollera att backend körs.
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Namn</TableHead>
                <TableHead>Organisation</TableHead>
                <TableHead>Kategori</TableHead>
                <TableHead>Kritikalitet</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>NIS2</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    Laddar...
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    Inga system matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((system) => (
                  <TableRow
                    key={system.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/systems/${system.id}`)}
                  >
                    <TableCell className="font-medium">{system.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {system.organization_id}
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
        <div className="flex items-center justify-between">
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
