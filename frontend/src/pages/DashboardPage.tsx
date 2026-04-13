import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { AlertTriangleIcon, TrendingUpIcon, ShieldIcon, UsersIcon, ServerIcon, BrainCircuitIcon, FileCheckIcon, LockIcon, FolderIcon, PuzzleIcon, PackageIcon, DatabaseIcon, ClipboardCheckIcon } from "lucide-react"
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
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getExpiringContracts, getSystemStats, getOrganizations } from "@/lib/api"
import type { ExpiringContract, SystemStats, Organization } from "@/types"
import { Criticality } from "@/types"
import { criticalityLabels, criticalityVariant, lifecycleLabels, aiRiskClassLabels, aiRiskBadgeClass } from "@/lib/labels"
import { AIRiskClass } from "@/types"

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function KpiSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="skeleton h-4 w-28" />
      </CardHeader>
      <CardContent className="pt-1">
        <div className="skeleton h-9 w-16 mb-1" />
        <div className="skeleton h-3 w-20" />
      </CardContent>
    </Card>
  )
}

function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="skeleton h-4 flex-1" />
          <div className="skeleton h-4 w-12" />
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function formatPercent(value: number, total: number): string {
  if (total === 0) return "0 %"
  return `${Math.round((value / total) * 100)} %`
}

// ---------------------------------------------------------------------------
// KPI-kort
// ---------------------------------------------------------------------------

interface KpiCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon: React.ElementType
  iconClassName?: string
}

function KpiCard({ title, value, subtitle, icon: Icon, iconClassName }: KpiCardProps) {
  return (
    <Card className="group hover:shadow-md transition-shadow duration-200">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-muted-foreground text-sm font-medium">
            {title}
          </CardTitle>
          <div className={`rounded-lg p-2 ${iconClassName ?? "bg-primary/10 text-primary"}`}>
            <Icon className="size-4" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-1">
        <p className="text-3xl font-bold tracking-tight">{value}</p>
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
  const navigate = useNavigate()
  const [selectedOrg, setSelectedOrg] = useState<string>("alla")

  const { data: orgs } = useQuery<Organization[]>({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const {
    data: stats,
    isLoading,
    isError,
    refetch,
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
    <div className="space-y-8">
      {/* Rubrik + filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
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

      {/* Felhantering */}
      {isError && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta statistik. Kontrollera att API:et är tillgängligt.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      )}

      {/* KPI-kort */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiSkeleton />
          <KpiSkeleton />
          <KpiSkeleton />
          <KpiSkeleton />
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Totalt antal system"
            value={total}
            icon={ServerIcon}
          />
          <KpiCard
            title="NIS2-tillämpliga"
            value={stats.nis2_applicable_count}
            subtitle={formatPercent(stats.nis2_applicable_count, total)}
            icon={ShieldIcon}
            iconClassName="bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400"
          />
          <KpiCard
            title="Behandlar personuppgifter"
            value={stats.treats_personal_data_count}
            subtitle={formatPercent(stats.treats_personal_data_count, total)}
            icon={UsersIcon}
            iconClassName="bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-400"
          />
          <KpiCard
            title="Kritiska system"
            value={kritiskCount}
            icon={TrendingUpIcon}
            iconClassName="bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-400"
          />
        </div>
      ) : null}

      {/* Nya KPI-kort: AI, GDPR, Klassning */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* AI-användning */}
          <Card className="group hover:shadow-md transition-shadow duration-200">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  AI-användning
                </CardTitle>
                <div className="rounded-lg p-2 bg-violet-50 text-violet-600 dark:bg-violet-950 dark:text-violet-400">
                  <BrainCircuitIcon className="size-4" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-1">
              <p className="text-3xl font-bold tracking-tight">{stats.uses_ai_count}</p>
              <p className="text-muted-foreground mt-1 text-sm">
                {formatPercent(stats.uses_ai_count, total)} av alla system
              </p>
              {Object.keys(stats.ai_by_risk_class).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {Object.entries(stats.ai_by_risk_class).map(([rc, count]) => (
                    <Badge
                      key={rc}
                      variant="outline"
                      className={aiRiskBadgeClass[rc as AIRiskClass] ?? ""}
                    >
                      {aiRiskClassLabels[rc as AIRiskClass] ?? rc}: {count}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* GDPR-täckning */}
          <Card className="group hover:shadow-md transition-shadow duration-200">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  GDPR-täckning
                </CardTitle>
                <div className="rounded-lg p-2 bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-400">
                  <LockIcon className="size-4" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-1">
              <div className="space-y-2">
                <div>
                  <p className="text-sm text-muted-foreground">PuB-avtal</p>
                  <p className="text-2xl font-bold tracking-tight">
                    {stats.gdpr_stats.pub_agreement_count}
                    <span className="text-sm font-normal text-muted-foreground ml-1">
                      system ({formatPercent(stats.gdpr_stats.pub_agreement_count, stats.treats_personal_data_count)})
                    </span>
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">DPIA genomförd</p>
                  <p className="text-2xl font-bold tracking-tight">
                    {stats.gdpr_stats.dpia_count}
                    <span className="text-sm font-normal text-muted-foreground ml-1">
                      system ({formatPercent(stats.gdpr_stats.dpia_count, stats.treats_personal_data_count)})
                    </span>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Klassningsstatus */}
          <Card className="group hover:shadow-md transition-shadow duration-200">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-muted-foreground text-sm font-medium">
                  Klassningsstatus
                </CardTitle>
                <div className="rounded-lg p-2 bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
                  <FileCheckIcon className="size-4" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-1">
              <p className="text-3xl font-bold tracking-tight">
                {formatPercent(stats.classification_stats.with_classification, total)}
              </p>
              <p className="text-muted-foreground mt-1 text-sm">
                {stats.classification_stats.with_classification} av {total} system klassade
              </p>
              {stats.classification_stats.expired > 0 && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                  {stats.classification_stats.expired} utgångna klassningar
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Entiteter */}
      {stats && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Entiteter</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card
              className="group hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => navigate("/objekt")}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-muted-foreground text-sm font-medium">Objekt</CardTitle>
                  <div className="rounded-lg p-2 bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
                    <FolderIcon className="size-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-1">
                <p className="text-3xl font-bold tracking-tight">{stats.objekt_count}</p>
              </CardContent>
            </Card>

            <Card
              className="group hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => navigate("/modules")}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-muted-foreground text-sm font-medium">Moduler</CardTitle>
                  <div className="rounded-lg p-2 bg-teal-50 text-teal-600 dark:bg-teal-950 dark:text-teal-400">
                    <PackageIcon className="size-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-1">
                <p className="text-3xl font-bold tracking-tight">{stats.module_count}</p>
              </CardContent>
            </Card>

            <Card
              className="group hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => navigate("/components")}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-muted-foreground text-sm font-medium">Komponenter</CardTitle>
                  <div className="rounded-lg p-2 bg-orange-50 text-orange-600 dark:bg-orange-950 dark:text-orange-400">
                    <PuzzleIcon className="size-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-1">
                <p className="text-3xl font-bold tracking-tight">{stats.component_count}</p>
              </CardContent>
            </Card>

            <Card
              className="group hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => navigate("/information-assets")}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-muted-foreground text-sm font-medium">Informationsm.</CardTitle>
                  <div className="rounded-lg p-2 bg-cyan-50 text-cyan-600 dark:bg-cyan-950 dark:text-cyan-400">
                    <DatabaseIcon className="size-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-1">
                <p className="text-3xl font-bold tracking-tight">{stats.information_asset_count}</p>
              </CardContent>
            </Card>

            <Card
              className={`group hover:shadow-md transition-shadow duration-200 cursor-pointer ${
                stats.pending_approval_count > 0
                  ? "ring-2 ring-yellow-400/50 bg-yellow-50/30 dark:bg-yellow-950/20"
                  : ""
              }`}
              onClick={() => navigate("/approvals")}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-muted-foreground text-sm font-medium">Vantande godk.</CardTitle>
                  <div className={`rounded-lg p-2 ${
                    stats.pending_approval_count > 0
                      ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                      : "bg-slate-50 text-slate-600 dark:bg-slate-950 dark:text-slate-400"
                  }`}>
                    <ClipboardCheckIcon className="size-4" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-1">
                <p className="text-3xl font-bold tracking-tight">{stats.pending_approval_count}</p>
              </CardContent>
            </Card>
          </div>
        </section>
      )}

      {/* Utgående avtal */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangleIcon className="size-4 text-amber-500" />
            Avtal som går ut inom 90 dagar
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!expiringContracts || expiringContracts.length === 0 ? (
            <p className="text-muted-foreground text-sm py-2">
              Inga avtal som går ut snart
            </p>
          ) : (
            <div className="rounded-lg overflow-hidden">
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
                            ? "bg-red-50/60 dark:bg-red-950/20"
                            : isWarning
                              ? "bg-orange-50/60 dark:bg-orange-950/20"
                              : ""
                        }
                      >
                        <TableCell className="font-medium">
                          {contract.supplier_name}
                        </TableCell>
                        <TableCell>{contract.system_name}</TableCell>
                        <TableCell>
                          {new Date(contract.contract_end).toLocaleDateString("sv-SE")}
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
            </div>
          )}
        </CardContent>
      </Card>

      {stats && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Per livscykelstatus */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Per livscykelstatus</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <TableSkeleton />
              ) : (
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
                          className="text-muted-foreground text-center py-6"
                        >
                          Inga data
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(stats.by_lifecycle_status).map(
                        ([status, count]) => (
                          <TableRow key={status} className="hover:bg-muted/50 transition-colors">
                            <TableCell>
                              {lifecycleLabels[status as keyof typeof lifecycleLabels] ?? status}
                            </TableCell>
                            <TableCell className="text-right font-semibold tabular-nums">
                              {count}
                            </TableCell>
                          </TableRow>
                        )
                      )
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Per kritikalitet */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Per kritikalitet</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <TableSkeleton />
              ) : (
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
                          className="text-muted-foreground text-center py-6"
                        >
                          Inga data
                        </TableCell>
                      </TableRow>
                    ) : (
                      Object.entries(stats.by_criticality).map(
                        ([level, count]) => (
                          <TableRow key={level} className="hover:bg-muted/50 transition-colors">
                            <TableCell>
                              <Badge
                                variant={
                                  criticalityVariant[level as Criticality] ?? "outline"
                                }
                              >
                                {criticalityLabels[level as Criticality] ?? level}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-semibold tabular-nums">
                              {count}
                            </TableCell>
                          </TableRow>
                        )
                      )
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
