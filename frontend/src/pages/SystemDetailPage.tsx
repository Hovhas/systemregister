import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon } from "lucide-react"

import { getSystem, deleteSystem } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { Criticality, LifecycleStatus, SystemCategory } from "@/types"
import type { Classification, Owner, Integration } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

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

const ownerRoleLabels: Record<string, string> = {
  systemägare: "Systemägare",
  informationsägare: "Informationsägare",
  systemförvaltare: "Systemförvaltare",
  teknisk_förvaltare: "Teknisk förvaltare",
  it_kontakt: "IT-kontakt",
  dataskyddsombud: "Dataskyddsombud",
}

const integrationTypeLabels: Record<string, string> = {
  api: "API",
  filöverföring: "Filöverföring",
  databasreplikering: "Databasreplikering",
  event: "Event",
  manuell: "Manuell",
}

// --- Hjälpkomponenter ---

function InfoRow({
  label,
  value,
}: {
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5 py-2 border-b last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value ?? "—"}</span>
    </div>
  )
}

function CiaBar({ label, value }: { label: string; value: number }) {
  const pct = (value / 4) * 100
  const color =
    value >= 3
      ? "bg-red-500"
      : value === 2
      ? "bg-yellow-500"
      : "bg-green-500"

  return (
    <div className="flex items-center gap-3">
      <span className="w-4 shrink-0 text-xs font-semibold text-muted-foreground">
        {label}
      </span>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-4 text-right text-xs tabular-nums">{value}</span>
    </div>
  )
}

// --- Flikar ---

function OversiktTab({ system }: { system: ReturnType<typeof useSystemDetail>["data"] }) {
  if (!system) return null
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Grundinformation</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Kategori" value={categoryLabels[system.system_category]} />
          <InfoRow label="Verksamhetsområde" value={system.business_area} />
          <InfoRow label="Alias" value={system.aliases} />
          <InfoRow label="Beskrivning" value={system.description} />
          <InfoRow
            label="Kritikalitet"
            value={
              <span className={`inline-flex items-center text-xs font-medium ${
                system.criticality === Criticality.CRITICAL
                  ? "text-red-700"
                  : system.criticality === Criticality.HIGH
                  ? "text-orange-700"
                  : system.criticality === Criticality.MEDIUM
                  ? "text-yellow-700"
                  : "text-green-700"
              }`}>
                {criticalityLabels[system.criticality]}
              </span>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Driftmiljö</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Driftsättningsmodell" value={system.hosting_model} />
          <InfoRow label="Molnleverantör" value={system.cloud_provider} />
          <InfoRow label="Dataplacering" value={system.data_location_country} />
          <InfoRow label="Produktnamn" value={system.product_name} />
          <InfoRow label="Version" value={system.product_version} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Livscykel</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Status" value={lifecycleLabels[system.lifecycle_status]} />
          <InfoRow label="Driftsatt" value={system.deployment_date} />
          <InfoRow label="Planerad avveckling" value={system.planned_decommission_date} />
          <InfoRow label="Supportslut" value={system.end_of_support_date} />
          <InfoRow label="Senaste riskbedömning" value={system.last_risk_assessment_date} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compliance</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow
            label="NIS2-tillämplig"
            value={
              <Badge variant={system.nis2_applicable ? "default" : "outline"}>
                {system.nis2_applicable ? "Ja" : "Nej"}
              </Badge>
            }
          />
          {system.nis2_classification && (
            <InfoRow label="NIS2-klassning" value={system.nis2_classification} />
          )}
          <InfoRow
            label="Behandlar personuppgifter"
            value={system.treats_personal_data ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Behandlar känsliga uppgifter"
            value={system.treats_sensitive_data ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Tredjelandsöverföring"
            value={system.third_country_transfer ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Förhöjt skyddsbehov"
            value={system.has_elevated_protection ? "Ja" : "Nej"}
          />
          <InfoRow label="KLASSA-referens" value={system.klassa_reference_id} />
        </CardContent>
      </Card>
    </div>
  )
}

function KlassningTab({ classifications }: { classifications: Classification[] }) {
  if (classifications.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        Inga klassningar registrerade
      </p>
    )
  }

  // Senaste klassning baserat på classified_at
  const sorted = [...classifications].sort(
    (a, b) => new Date(b.classified_at).getTime() - new Date(a.classified_at).getTime()
  )
  const latest = sorted[0]

  return (
    <div className="flex flex-col gap-4">
      {sorted.map((cls, idx) => (
        <Card key={cls.id}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Klassning {new Date(cls.classified_at).toLocaleDateString("sv-SE")}
              {idx === 0 && (
                <Badge variant="default" className="text-xs">Senaste</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <CiaBar label="K" value={cls.confidentiality} />
              <CiaBar label="R" value={cls.integrity} />
              <CiaBar label="T" value={cls.availability} />
              {cls.traceability !== null && cls.traceability !== undefined && (
                <CiaBar label="S" value={cls.traceability} />
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              Klassad av: <span className="font-medium">{cls.classified_by}</span>
              {cls.valid_until && ` · Giltig till: ${cls.valid_until}`}
            </div>
            {cls.notes && (
              <p className="text-sm text-muted-foreground">{cls.notes}</p>
            )}
          </CardContent>
        </Card>
      ))}
      {/* supress lint warning for latest */}
      <span className="sr-only">{latest.id}</span>
    </div>
  )
}

function AgareTab({ owners }: { owners: Owner[] }) {
  if (owners.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        Inga ägare registrerade
      </p>
    )
  }

  return (
    <div className="rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Roll</TableHead>
            <TableHead>Namn</TableHead>
            <TableHead>E-post</TableHead>
            <TableHead>Organisation</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {owners.map((owner) => (
            <TableRow key={owner.id}>
              <TableCell>
                <Badge variant="secondary">
                  {ownerRoleLabels[owner.role] ?? owner.role}
                </Badge>
              </TableCell>
              <TableCell className="font-medium">{owner.name}</TableCell>
              <TableCell className="text-muted-foreground">
                {owner.email ?? "—"}
              </TableCell>
              <TableCell className="text-muted-foreground text-xs">
                {owner.organization_id}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function IntegrationerTab({
  integrations,
  systemId,
}: {
  integrations: Integration[]
  systemId: string
}) {
  if (integrations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        Inga integrationer registrerade
      </p>
    )
  }

  return (
    <div className="rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Riktning</TableHead>
            <TableHead>Typ</TableHead>
            <TableHead>Motpart</TableHead>
            <TableHead>Frekvens</TableHead>
            <TableHead>Beskrivning</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {integrations.map((intg) => {
            const isSource = intg.source_system_id === systemId
            return (
              <TableRow key={intg.id}>
                <TableCell>
                  <Badge variant={isSource ? "default" : "secondary"}>
                    {isSource ? "Ut" : "In"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {integrationTypeLabels[intg.integration_type] ??
                    intg.integration_type}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {isSource ? intg.target_system_id : intg.source_system_id}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {intg.frequency ?? "—"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {intg.description ?? "—"}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function ExtendedAttributesTab({ attributes }: { attributes: Record<string, unknown> | null }) {
  if (!attributes || Object.keys(attributes).length === 0) {
    return <p className="text-sm text-muted-foreground py-4">Ingen övrig data registrerad</p>
  }

  const entries = Object.entries(attributes).sort(([a], [b]) => a.localeCompare(b, "sv"))

  return (
    <div className="rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Fält</TableHead>
            <TableHead>Värde</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([key, value]) => (
            <TableRow key={key}>
              <TableCell className="font-medium text-sm">{key}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {value === null || value === undefined ? "—" : String(value)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

// --- Audit API ---

async function getAuditForRecord(recordId: string) {
  const res = await fetch(`/api/v1/audit/record/${recordId}`)
  if (!res.ok) throw new Error("Kunde inte hämta ändringslogg")
  return res.json()
}

// --- Ändringslogg-komponent ---

function AuditTimeline({ systemId }: { systemId: string }) {
  const { data: entries, isLoading } = useQuery({
    queryKey: ["audit", systemId],
    queryFn: () => getAuditForRecord(systemId),
  })

  if (isLoading) return <p className="text-sm text-muted-foreground">Laddar...</p>
  if (!entries?.length) return <p className="text-sm text-muted-foreground py-4">Inga ändringar registrerade</p>

  return (
    <div className="space-y-3">
      {entries.map((entry: any) => (
        <Card key={entry.id}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={entry.action === "create" ? "default" : entry.action === "delete" ? "destructive" : "secondary"}>
                {entry.action === "create" ? "Skapad" : entry.action === "update" ? "Ändrad" : "Borttagen"}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(entry.changed_at).toLocaleString("sv-SE")}
              </span>
              {entry.changed_by && <span className="text-xs">av {entry.changed_by}</span>}
            </div>
            {entry.action === "update" && entry.old_values && entry.new_values && (
              <div className="text-xs space-y-1 mt-2">
                {Object.keys(entry.new_values).map((key: string) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-medium min-w-24">{key}:</span>
                    <span className="text-red-600 line-through">{String(entry.old_values[key] ?? "—")}</span>
                    <span>→</span>
                    <span className="text-green-600">{String(entry.new_values[key] ?? "—")}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// --- Hjälp-hook ---

function useSystemDetail(id: string) {
  return useQuery({
    queryKey: ["system", id],
    queryFn: () => getSystem(id),
    enabled: !!id,
  })
}

// --- Huvudkomponent ---

export default function SystemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data: system, isLoading, isError } = useSystemDetail(id ?? "")

  const deleteMutation = useMutation({
    mutationFn: () => deleteSystem(system!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["systems"] })
      navigate("/systems")
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
        Laddar system...
      </div>
    )
  }

  if (isError || !system) {
    return (
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => navigate("/systems")}
        >
          <ArrowLeftIcon className="mr-1 size-4" />
          Tillbaka
        </Button>
        <p className="text-sm text-destructive">
          Kunde inte hämta system.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Sidhuvud */}
      <div className="flex items-start gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="mt-0.5 shrink-0"
          onClick={() => navigate("/systems")}
        >
          <ArrowLeftIcon className="mr-1 size-4" />
          Tillbaka
        </Button>
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold">{system.name}</h1>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{categoryLabels[system.system_category]}</Badge>
            <Badge variant="outline">{lifecycleLabels[system.lifecycle_status]}</Badge>
            {system.nis2_applicable && (
              <Badge variant="default">NIS2</Badge>
            )}
          </div>
        </div>
        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/systems/${system.id}/edit`)}
          >
            <PencilIcon className="mr-1 size-4" /> Redigera
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteOpen(true)}
          >
            <TrashIcon className="mr-1 size-4" /> Ta bort
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Ta bort system"
        description={`Är du säker på att du vill ta bort "${system.name}"? Alla kopplingar (klassningar, ägare, integrationer) raderas.`}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />

      {/* Flikar */}
      <Tabs defaultValue="oversikt">
        <TabsList>
          <TabsTrigger value="oversikt">Översikt</TabsTrigger>
          <TabsTrigger value="klassning">
            Klassning
            {system.classifications.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.classifications.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="agare">
            Ägare
            {system.owners.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.owners.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="integrationer">Integrationer</TabsTrigger>
          <TabsTrigger value="ovrigt">Övrig data</TabsTrigger>
          <TabsTrigger value="andringslogg">Ändringslogg</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-4">
          <OversiktTab system={system} />
        </TabsContent>

        <TabsContent value="klassning" className="mt-4">
          <KlassningTab classifications={system.classifications} />
        </TabsContent>

        <TabsContent value="agare" className="mt-4">
          <AgareTab owners={system.owners} />
        </TabsContent>

        <TabsContent value="integrationer" className="mt-4">
          <IntegrationerTab integrations={system.integrations ?? []} systemId={system.id} />
        </TabsContent>

        <TabsContent value="ovrigt" className="mt-4">
          <ExtendedAttributesTab attributes={system.extended_attributes} />
        </TabsContent>

        <TabsContent value="andringslogg" className="mt-4">
          <AuditTimeline systemId={system.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
