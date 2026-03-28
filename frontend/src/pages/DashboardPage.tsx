import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// ---------------------------------------------------------------------------
// Typer
// ---------------------------------------------------------------------------

interface SystemStats {
  total_systems: number
  by_lifecycle_status: Record<string, number>
  by_criticality: Record<string, number>
  nis2_applicable_count: number
  treats_personal_data_count: number
}

interface Organization {
  id: string
  name: string
}

// ---------------------------------------------------------------------------
// API-funktioner (inline, ersätts med @/lib/api när den skapas)
// ---------------------------------------------------------------------------

const API_BASE = "/api/v1"

async function getSystemStats(organizationId?: string): Promise<SystemStats> {
  const params = new URLSearchParams()
  if (organizationId && organizationId !== "alla") {
    params.set("organization_id", organizationId)
  }
  const url = `${API_BASE}/systems/stats/overview${params.size ? "?" + params : ""}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Fel vid hämtning av statistik: ${res.status}`)
  return res.json()
}

async function getOrganizations(): Promise<Organization[]> {
  const res = await fetch(`${API_BASE}/organizations`)
  if (!res.ok) throw new Error(`Fel vid hämtning av organisationer: ${res.status}`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Hjälpfunktioner
// ---------------------------------------------------------------------------

function formatPercent(value: number, total: number): string {
  if (total === 0) return "0 %"
  return `${Math.round((value / total) * 100)} %`
}

const CRITICALITY_LABELS: Record<string, string> = {
  kritisk: "Kritisk",
  hog: "Hög",
  medium: "Medium",
  lag: "Låg",
}

const CRITICALITY_VARIANT: Record<
  string,
  "destructive" | "default" | "secondary" | "outline"
> = {
  kritisk: "destructive",
  hog: "default",
  medium: "secondary",
  lag: "outline",
}

const LIFECYCLE_LABELS: Record<string, string> = {
  planerad: "Planerad",
  aktiv: "Aktiv",
  avveckling: "Avveckling",
  avvecklad: "Avvecklad",
}

// ---------------------------------------------------------------------------
// KPI-kort
// ---------------------------------------------------------------------------

interface KpiCardProps {
  title: string
  value: number | string
  subtitle?: string
}

function KpiCard({ title, value, subtitle }: KpiCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-muted-foreground text-sm font-medium">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
        {subtitle && (
          <p className="text-muted-foreground mt-1 text-sm">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Huvudkomponent
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [selectedOrg, setSelectedOrg] = useState<string>("alla")

  const { data: orgs } = useQuery<Organization[]>({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const {
    data: stats,
    isLoading,
    isError,
  } = useQuery<SystemStats>({
    queryKey: ["system-stats", selectedOrg],
    queryFn: () =>
      getSystemStats(selectedOrg !== "alla" ? selectedOrg : undefined),
  })

  const total = stats?.total_systems ?? 0

  const kritiskCount = stats?.by_criticality?.["kritisk"] ?? 0

  return (
    <div className="space-y-6 p-6">
      {/* Rubrik + filter */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground text-sm">
            Översikt av systemregistret
          </p>
        </div>

        {orgs && orgs.length > 0 && (
          <Select value={selectedOrg} onValueChange={(val) => setSelectedOrg(val ?? "alla")}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Filtrera organisation">
                {selectedOrg === "alla"
                  ? "Alla organisationer"
                  : orgs?.find((o) => o.id === selectedOrg)?.name}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="alla">Alla organisationer</SelectItem>
              {orgs.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Laddnings- och felhantering */}
      {isLoading && (
        <p className="text-muted-foreground text-sm">Laddar statistik…</p>
      )}
      {isError && (
        <p className="text-destructive text-sm">
          Kunde inte hämta statistik. Kontrollera att API:et är tillgängligt.
        </p>
      )}

      {stats && (
        <>
          {/* KPI-kort */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard title="Totalt antal system" value={total} />

            <KpiCard
              title="NIS2-tillämpliga"
              value={stats.nis2_applicable_count}
              subtitle={formatPercent(stats.nis2_applicable_count, total)}
            />

            <KpiCard
              title="Behandlar personuppgifter"
              value={stats.treats_personal_data_count}
              subtitle={formatPercent(
                stats.treats_personal_data_count,
                total
              )}
            />

            <KpiCard title="Kritiska system" value={kritiskCount} />
          </div>

          {/* Tabeller */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Per livscykelstatus */}
            <Card>
              <CardHeader>
                <CardTitle>Per livscykelstatus</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Antal</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(stats.by_lifecycle_status).length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={2}
                          className="text-muted-foreground text-center"
                        >
                          Inga data
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(stats.by_lifecycle_status).map(
                        ([status, count]) => (
                          <TableRow key={status}>
                            <TableCell>
                              {LIFECYCLE_LABELS[status] ?? status}
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {count}
                            </TableCell>
                          </TableRow>
                        )
                      )
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Per kritikalitet */}
            <Card>
              <CardHeader>
                <CardTitle>Per kritikalitet</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nivå</TableHead>
                      <TableHead className="text-right">Antal</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(stats.by_criticality).length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={2}
                          className="text-muted-foreground text-center"
                        >
                          Inga data
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(stats.by_criticality).map(
                        ([level, count]) => (
                          <TableRow key={level}>
                            <TableCell>
                              <Badge
                                variant={
                                  CRITICALITY_VARIANT[level] ?? "outline"
                                }
                              >
                                {CRITICALITY_LABELS[level] ?? level}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {count}
                            </TableCell>
                          </TableRow>
                        )
                      )
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
