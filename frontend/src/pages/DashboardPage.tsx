import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangleIcon } from "lucide-react"
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
import { getExpiringContracts, getSystemStats, getOrganizations } from "@/lib/api"
import type { ExpiringContract, SystemStats, Organization } from "@/types"

// ---------------------------------------------------------------------------
// Hjälpfunktioner
// ---------------------------------------------------------------------------

function formatPercent(value: number, total: number): string {
  if (total === 0) return "0 %"
  return `${Math.round((value / total) * 100)} %`
}

const CRITICALITY_LABELS: Record<string, string> = {
  kritisk: "Kritisk",
  hög: "Hög",
  medel: "Medel",
  låg: "Låg",
}

const CRITICALITY_VARIANT: Record<
  string,
  "destructive" | "default" | "secondary" | "outline"
> = {
  kritisk: "destructive",
  hög: "default",
  medel: "secondary",
  låg: "outline",
}

const LIFECYCLE_LABELS: Record<string, string> = {
  planerad: "Planerad",
  under_inforande: "Under införande",
  i_drift: "I drift",
  under_avveckling: "Under avveckling",
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

  const { data: expiringContracts } = useQuery<ExpiringContract[]>({
    queryKey: ["expiring-contracts"],
    queryFn: () => getExpiringContracts(90),
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

      {/* Utgående avtal */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangleIcon className="size-4 text-amber-500" />
            Avtal som går ut inom 90 dagar
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!expiringContracts || expiringContracts.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              Inga avtal som går ut snart
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Leverantör</TableHead>
                  <TableHead>System</TableHead>
                  <TableHead>Slutdatum</TableHead>
                  <TableHead className="text-right">Dagar kvar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expiringContracts.map((contract) => {
                  const isUrgent = contract.days_remaining < 30
                  const isWarning = contract.days_remaining < 90
                  return (
                    <TableRow
                      key={contract.id}
                      className={
                        isUrgent
                          ? "bg-red-50 dark:bg-red-950/20"
                          : isWarning
                            ? "bg-orange-50 dark:bg-orange-950/20"
                            : ""
                      }
                    >
                      <TableCell className="font-medium">
                        {contract.supplier_name}
                      </TableCell>
                      <TableCell>{contract.system_name}</TableCell>
                      <TableCell>
                        {new Date(contract.contract_end).toLocaleDateString(
                          "sv-SE"
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant={
                            isUrgent
                              ? "destructive"
                              : isWarning
                                ? "default"
                                : "outline"
                          }
                        >
                          {contract.days_remaining} dagar
                        </Badge>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

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
