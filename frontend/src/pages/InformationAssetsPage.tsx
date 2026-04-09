import { useState, useCallback } from "react"
import { useQuery } from "@tanstack/react-query"
import { SearchIcon, ChevronUpIcon, ChevronDownIcon, XIcon, Loader2Icon } from "lucide-react"

import { getInformationAssets, getOrganizations } from "@/lib/api"
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
      {Array.from({ length: 7 }).map((_, i) => (
        <TableCell key={i}>
          <div className="skeleton h-4 w-full max-w-[120px]" />
        </TableCell>
      ))}
    </TableRow>
  )
}

const PAGE_SIZE = 50

export default function InformationAssetsPage() {
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [organization, setOrganization] = useState("")
  const [personalData, setPersonalData] = useState<"" | "true" | "false">("")
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
  const hasFilters = !!(organization || personalData || debouncedSearch)

  function clearFilters() {
    setSearchInput("")
    setDebouncedSearch("")
    setOrganization("")
    setPersonalData("")
    setOffset(0)
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["information-assets", debouncedSearch, organization, personalData, offset],
    queryFn: () =>
      getInformationAssets({
        q: debouncedSearch || undefined,
        organization_id: organization || undefined,
        contains_personal_data: personalData ? personalData === "true" : undefined,
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
          <h1 className="text-2xl font-bold tracking-tight">Informationsmängder</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} informationsmängder totalt` : "Inga informationsmängder hittade"}
          </p>
        </div>
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
            placeholder="Sök informationsmängder..."
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
          value={personalData || undefined}
          onValueChange={(val) => {
            setPersonalData(val as "" | "true" | "false")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Personuppgifter">
              {personalData === "true" ? "Innehåller personuppgifter" : personalData === "false" ? "Utan personuppgifter" : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla</SelectItem>
            <SelectItem value="true">Innehåller personuppgifter</SelectItem>
            <SelectItem value="false">Utan personuppgifter</SelectItem>
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
          <p>Kunde inte hämta informationsmängder. Kontrollera att backend körs.</p>
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
                <TableHead>Informationsägare</TableHead>
                <TableHead className="text-center w-12">K</TableHead>
                <TableHead className="text-center w-12">R</TableHead>
                <TableHead className="text-center w-12">T</TableHead>
                <TableHead>Personuppgifter</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRowSkeleton key={i} />
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    Inga informationsmängder matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((asset, idx) => (
                  <TableRow
                    key={asset.id}
                    className={`transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                  >
                    <TableCell className="font-medium">{asset.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {orgNameMap[asset.organization_id] ?? asset.organization_id}
                    </TableCell>
                    <TableCell>{asset.information_owner ?? "—"}</TableCell>
                    <TableCell className="text-center">{asset.confidentiality ?? "—"}</TableCell>
                    <TableCell className="text-center">{asset.integrity ?? "—"}</TableCell>
                    <TableCell className="text-center">{asset.availability ?? "—"}</TableCell>
                    <TableCell>
                      {asset.contains_personal_data ? (
                        <Badge variant="default">Ja</Badge>
                      ) : (
                        <Badge variant="outline">Nej</Badge>
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
    </div>
  )
}
