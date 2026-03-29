import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon, PlusIcon } from "lucide-react"
import { toast } from "sonner"

import {
  getSystem,
  deleteSystem,
  getOrganizations,
  getSystems,
  createClassification,
  createOwner,
  deleteOwner,
  deleteIntegration,
  getGDPRTreatments,
  createGDPRTreatment,
  deleteGDPRTreatment,
  getContracts,
  createContract,
  deleteContract,
} from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import IntegrationDialog from "@/components/IntegrationDialog"
import { Criticality, LifecycleStatus, SystemCategory, OwnerRole } from "@/types"
import type {
  Classification,
  ClassificationCreate,
  Owner,
  OwnerCreate,
  Integration,
  GDPRTreatment,
  GDPRTreatmentCreate,
  Contract,
  ContractCreate,
} from "@/types"
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
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"

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

const legalBasisLabels: Record<string, string> = {
  samtycke: "Samtycke",
  avtal: "Avtal",
  rättslig_förpliktelse: "Rättslig förpliktelse",
  grundläggande_intresse: "Grundläggande intresse",
  allmänt_intresse: "Allmänt intresse",
  berättigat_intresse: "Berättigat intresse",
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

function CiaBar({ label, title, value }: { label: string; title?: string; value: number }) {
  const pct = (value / 4) * 100
  const color =
    value >= 3
      ? "bg-red-500"
      : value === 2
      ? "bg-yellow-500"
      : "bg-green-500"

  return (
    <div className="flex items-center gap-3">
      <span className="w-4 shrink-0 text-xs font-semibold text-muted-foreground" title={title}>
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

function FormField({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-muted-foreground">
        {label}{required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
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

// --- Klassning-tabb ---

function KlassningTab({
  classifications,
  systemId,
}: {
  classifications: Classification[]
  systemId: string
}) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState<{
    confidentiality: string
    integrity: string
    availability: string
    traceability: string
    classified_by: string
    valid_until: string
    notes: string
  }>({
    confidentiality: "2",
    integrity: "2",
    availability: "2",
    traceability: "",
    classified_by: "",
    valid_until: "",
    notes: "",
  })
  const [error, setError] = useState("")

  const createMutation = useMutation({
    mutationFn: (data: ClassificationCreate) =>
      createClassification(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Klassning skapad")
      setDialogOpen(false)
      setForm({
        confidentiality: "2",
        integrity: "2",
        availability: "2",
        traceability: "",
        classified_by: "",
        valid_until: "",
        notes: "",
      })
      setError("")
    },
    onError: () => setError("Kunde inte spara klassning. Försök igen."),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.classified_by.trim()) {
      setError("Klassad av är obligatoriskt")
      return
    }
    const payload: ClassificationCreate = {
      system_id: systemId,
      confidentiality: parseInt(form.confidentiality),
      integrity: parseInt(form.integrity),
      availability: parseInt(form.availability),
      classified_by: form.classified_by.trim(),
    }
    if (form.traceability !== "") payload.traceability = parseInt(form.traceability)
    if (form.valid_until) payload.valid_until = form.valid_until
    if (form.notes.trim()) payload.notes = form.notes.trim()
    createMutation.mutate(payload)
  }

  const sorted = [...classifications].sort(
    (a, b) => new Date(b.classified_at).getTime() - new Date(a.classified_at).getTime()
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Ny klassning
        </Button>
      </div>

      {sorted.length === 0 && (
        <p className="text-sm text-muted-foreground py-4">
          Inga klassningar registrerade
        </p>
      )}

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
              <CiaBar label="K" title="Konfidentialitet" value={cls.confidentiality} />
              <CiaBar label="R" title="Riktighet (Integrity)" value={cls.integrity} />
              <CiaBar label="T" title="Tillgänglighet (Availability)" value={cls.availability} />
              {cls.traceability !== null && cls.traceability !== undefined && (
                <CiaBar label="S" title="Spårbarhet (Traceability)" value={cls.traceability} />
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ny klassning</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Konfidentialitet (K)" required>
                <Input
                  type="number"
                  min={0}
                  max={4}
                  value={form.confidentiality}
                  onChange={(e) => setForm((f) => ({ ...f, confidentiality: e.target.value }))}
                />
              </FormField>
              <FormField label="Riktighet (R)" required>
                <Input
                  type="number"
                  min={0}
                  max={4}
                  value={form.integrity}
                  onChange={(e) => setForm((f) => ({ ...f, integrity: e.target.value }))}
                />
              </FormField>
              <FormField label="Tillgänglighet (T)" required>
                <Input
                  type="number"
                  min={0}
                  max={4}
                  value={form.availability}
                  onChange={(e) => setForm((f) => ({ ...f, availability: e.target.value }))}
                />
              </FormField>
              <FormField label="Spårbarhet (S)">
                <Input
                  type="number"
                  min={0}
                  max={4}
                  placeholder="Valfritt"
                  value={form.traceability}
                  onChange={(e) => setForm((f) => ({ ...f, traceability: e.target.value }))}
                />
              </FormField>
            </div>
            <FormField label="Klassad av" required>
              <Input
                value={form.classified_by}
                onChange={(e) => setForm((f) => ({ ...f, classified_by: e.target.value }))}
                placeholder="Namn eller e-post"
              />
            </FormField>
            <FormField label="Giltig till">
              <Input
                type="date"
                value={form.valid_until}
                onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))}
              />
            </FormField>
            <FormField label="Anteckningar">
              <textarea
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50 placeholder:text-muted-foreground resize-none"
                rows={3}
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="Valfria anteckningar..."
              />
            </FormField>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// --- Ägare-tabb ---

function AgareTab({
  owners,
  orgNameMap,
  systemId,
}: {
  owners: Owner[]
  orgNameMap: Record<string, string>
  systemId: string
}) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Owner | null>(null)
  const [form, setForm] = useState<{
    role: string
    name: string
    email: string
    phone: string
    organization_id: string
  }>({
    role: "",
    name: "",
    email: "",
    phone: "",
    organization_id: "",
  })
  const [error, setError] = useState("")

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const createMutation = useMutation({
    mutationFn: (data: OwnerCreate) => createOwner(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Ägare tillagd")
      setDialogOpen(false)
      setForm({ role: "", name: "", email: "", phone: "", organization_id: "" })
      setError("")
    },
    onError: () => setError("Kunde inte spara ägare. Försök igen."),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteOwner(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Ägare borttagen")
      setDeleteTarget(null)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.role) { setError("Roll är obligatoriskt"); return }
    if (!form.name.trim()) { setError("Namn är obligatoriskt"); return }
    if (!form.email.trim()) { setError("E-post är obligatoriskt"); return }
    if (!form.organization_id) { setError("Organisation är obligatoriskt"); return }
    createMutation.mutate({
      system_id: systemId,
      role: form.role as OwnerRole,
      name: form.name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim() || undefined,
      organization_id: form.organization_id,
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Lägg till ägare
        </Button>
      </div>

      {owners.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga ägare registrerade
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Roll</TableHead>
                <TableHead>Namn</TableHead>
                <TableHead>E-post</TableHead>
                <TableHead>Organisation</TableHead>
                <TableHead className="w-12"></TableHead>
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
                    {orgNameMap[owner.organization_id] ?? owner.organization_id}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Ta bort ägare ${owner.name}`}
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(owner)}
                    >
                      <TrashIcon className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Lägg till ägare</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <FormField label="Roll" required>
              <Select value={form.role} onValueChange={(v) => setForm((f) => ({ ...f, role: v ?? "" }))}>
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {form.role ? ownerRoleLabels[form.role] ?? form.role : "Välj roll..."}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(ownerRoleLabels).map(([val, label]) => (
                    <SelectItem key={val} value={val}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Namn" required>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Fullständigt namn"
              />
            </FormField>
            <FormField label="E-post" required>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="namn@sundsvall.se"
              />
            </FormField>
            <FormField label="Telefon">
              <Input
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                placeholder="Valfritt"
              />
            </FormField>
            <FormField label="Organisation" required>
              <Select value={form.organization_id} onValueChange={(v) => setForm((f) => ({ ...f, organization_id: v ?? "" }))}>
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {form.organization_id
                      ? (orgs?.find((o) => o.id === form.organization_id)?.name ?? form.organization_id)
                      : "Välj organisation..."}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {(orgs ?? []).map((org) => (
                    <SelectItem key={org.id} value={org.id}>{org.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort ägare"
        description={`Är du säker på att du vill ta bort ${deleteTarget?.name ?? ""}?`}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// --- Integrationer-tabb ---

function IntegrationerTab({
  integrations,
  systemId,
}: {
  integrations: Integration[]
  systemId: string
}) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Integration | null>(null)

  const { data: allSystemsData } = useQuery({
    queryKey: ["systems", { limit: 500 }],
    queryFn: () => getSystems({ limit: 500 }),
  })
  const allSystems = allSystemsData?.items ?? []

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Integration borttagen")
      setDeleteTarget(null)
    },
  })

  const systemNameMap = Object.fromEntries(allSystems.map((s) => [s.id, s.name]))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Ny integration
        </Button>
      </div>

      {integrations.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga integrationer registrerade
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Riktning</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Motpart</TableHead>
                <TableHead>Frekvens</TableHead>
                <TableHead>Beskrivning</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {integrations.map((intg) => {
                const isSource = intg.source_system_id === systemId
                const counterpartId = isSource ? intg.target_system_id : intg.source_system_id
                return (
                  <TableRow key={intg.id}>
                    <TableCell>
                      <Badge variant={isSource ? "default" : "secondary"}>
                        {isSource ? "Ut" : "In"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {integrationTypeLabels[intg.integration_type] ?? intg.integration_type}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {systemNameMap[counterpartId] ?? counterpartId}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {intg.frequency ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {intg.description ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Ta bort integration"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteTarget(intg)}
                      >
                        <TrashIcon className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <IntegrationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        systemId={systemId}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort integration"
        description="Är du säker på att du vill ta bort denna integration?"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// --- GDPR-tabb ---

function GdprTab({
  systemId,
}: {
  systemId: string
}) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<GDPRTreatment | null>(null)
  const [form, setForm] = useState<{
    data_categories: string
    categories_of_data_subjects: string
    legal_basis: string
    retention_policy: string
    dpia_conducted: boolean
    ropa_reference_id: string
  }>({
    data_categories: "",
    categories_of_data_subjects: "",
    legal_basis: "",
    retention_policy: "",
    dpia_conducted: false,
    ropa_reference_id: "",
  })
  const [error, setError] = useState("")

  const { data: treatments = [], isLoading } = useQuery({
    queryKey: ["gdpr", systemId],
    queryFn: () => getGDPRTreatments(systemId),
  })

  const createMutation = useMutation({
    mutationFn: (data: GDPRTreatmentCreate) => createGDPRTreatment(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gdpr", systemId] })
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("GDPR-behandling skapad")
      setDialogOpen(false)
      setForm({
        data_categories: "",
        categories_of_data_subjects: "",
        legal_basis: "",
        retention_policy: "",
        dpia_conducted: false,
        ropa_reference_id: "",
      })
      setError("")
    },
    onError: () => setError("Kunde inte spara GDPR-behandling. Försök igen."),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGDPRTreatment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gdpr", systemId] })
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("GDPR-behandling borttagen")
      setDeleteTarget(null)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const payload: GDPRTreatmentCreate = {
      dpia_conducted: form.dpia_conducted,
    }
    if (form.data_categories.trim()) {
      payload.data_categories = form.data_categories.split(",").map((s) => s.trim()).filter(Boolean)
    }
    if (form.categories_of_data_subjects.trim()) payload.categories_of_data_subjects = form.categories_of_data_subjects.trim()
    if (form.legal_basis) payload.legal_basis = form.legal_basis
    if (form.retention_policy.trim()) payload.retention_policy = form.retention_policy.trim()
    if (form.ropa_reference_id.trim()) payload.ropa_reference_id = form.ropa_reference_id.trim()
    createMutation.mutate(payload)
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Laddar...</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Ny behandling
        </Button>
      </div>

      {treatments.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga GDPR-behandlingar registrerade
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Datakategorier</TableHead>
                <TableHead>Rättslig grund</TableHead>
                <TableHead>DPIA</TableHead>
                <TableHead>Gallringspolicy</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {treatments.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="text-sm">
                    {t.data_categories?.join(", ") ?? "—"}
                  </TableCell>
                  <TableCell>
                    {t.legal_basis ? (legalBasisLabels[t.legal_basis] ?? t.legal_basis) : "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={t.dpia_conducted ? "default" : "outline"}>
                      {t.dpia_conducted ? "Genomförd" : "Ej genomförd"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {t.retention_policy ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label="Ta bort GDPR-behandling"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(t)}
                    >
                      <TrashIcon className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ny GDPR-behandling</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <FormField label="Kategorier av personuppgifter">
              <Input
                value={form.data_categories}
                onChange={(e) => setForm((f) => ({ ...f, data_categories: e.target.value }))}
                placeholder="Kommaseparerat, t.ex. namn, adress"
              />
            </FormField>
            <FormField label="Kategorier av registrerade">
              <Input
                value={form.categories_of_data_subjects}
                onChange={(e) => setForm((f) => ({ ...f, categories_of_data_subjects: e.target.value }))}
                placeholder="t.ex. anställda, medborgare"
              />
            </FormField>
            <FormField label="Rättslig grund">
              <Select value={form.legal_basis} onValueChange={(v) => setForm((f) => ({ ...f, legal_basis: v ?? "" }))}>
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {form.legal_basis ? legalBasisLabels[form.legal_basis] ?? form.legal_basis : "Välj rättslig grund..."}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(legalBasisLabels).map(([val, label]) => (
                    <SelectItem key={val} value={val}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Gallringspolicy">
              <Input
                value={form.retention_policy}
                onChange={(e) => setForm((f) => ({ ...f, retention_policy: e.target.value }))}
                placeholder="t.ex. 7 år efter avslutad tjänst"
              />
            </FormField>
            <FormField label="RoPA-referens">
              <Input
                value={form.ropa_reference_id}
                onChange={(e) => setForm((f) => ({ ...f, ropa_reference_id: e.target.value }))}
                placeholder="Valfritt referens-ID"
              />
            </FormField>
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.dpia_conducted}
                onChange={(e) => setForm((f) => ({ ...f, dpia_conducted: e.target.checked }))}
                className="rounded border-input"
              />
              DPIA genomförd
            </label>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort GDPR-behandling"
        description="Är du säker på att du vill ta bort denna behandlingspost?"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// --- Avtal-tabb ---

function AvtalTab({ systemId }: { systemId: string }) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Contract | null>(null)
  const [form, setForm] = useState<{
    supplier_name: string
    contract_start: string
    contract_end: string
    license_model: string
    annual_license_cost: string
    annual_operations_cost: string
    notice_period_months: string
    sla_description: string
    auto_renewal: boolean
  }>({
    supplier_name: "",
    contract_start: "",
    contract_end: "",
    license_model: "",
    annual_license_cost: "",
    annual_operations_cost: "",
    notice_period_months: "",
    sla_description: "",
    auto_renewal: false,
  })
  const [error, setError] = useState("")

  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ["contracts", systemId],
    queryFn: () => getContracts(systemId),
  })

  const createMutation = useMutation({
    mutationFn: (data: ContractCreate) => createContract(systemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", systemId] })
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Avtal skapat")
      setDialogOpen(false)
      setForm({
        supplier_name: "",
        contract_start: "",
        contract_end: "",
        license_model: "",
        annual_license_cost: "",
        annual_operations_cost: "",
        notice_period_months: "",
        sla_description: "",
        auto_renewal: false,
      })
      setError("")
    },
    onError: () => setError("Kunde inte spara avtal. Försök igen."),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteContract(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts", systemId] })
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Avtal borttaget")
      setDeleteTarget(null)
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.supplier_name.trim()) { setError("Leverantör är obligatoriskt"); return }
    const payload: ContractCreate = {
      supplier_name: form.supplier_name.trim(),
      auto_renewal: form.auto_renewal,
    }
    if (form.contract_start) payload.contract_start = form.contract_start
    if (form.contract_end) payload.contract_end = form.contract_end
    if (form.license_model.trim()) payload.license_model = form.license_model.trim()
    if (form.annual_license_cost !== "") payload.annual_license_cost = parseFloat(form.annual_license_cost)
    if (form.annual_operations_cost !== "") payload.annual_operations_cost = parseFloat(form.annual_operations_cost)
    if (form.notice_period_months !== "") payload.notice_period_months = parseInt(form.notice_period_months)
    if (form.sla_description.trim()) payload.sla_description = form.sla_description.trim()
    createMutation.mutate(payload)
  }

  function contractRowClass(contract: Contract): string {
    if (!contract.contract_end) return ""
    const daysLeft = Math.ceil(
      (new Date(contract.contract_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    )
    if (daysLeft < 0) return "bg-red-50 dark:bg-red-950/20"
    if (daysLeft <= 90) return "bg-orange-50 dark:bg-orange-950/20"
    return ""
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Laddar...</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Nytt avtal
        </Button>
      </div>

      {contracts.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga avtal registrerade
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Leverantör</TableHead>
                <TableHead>Start</TableHead>
                <TableHead>Slut</TableHead>
                <TableHead>Licenskostnad/år</TableHead>
                <TableHead>Driftskostnad/år</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {contracts.map((c) => (
                <TableRow key={c.id} className={contractRowClass(c)}>
                  <TableCell className="font-medium">{c.supplier_name}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {c.contract_start ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {c.contract_end ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {c.annual_license_cost != null
                      ? `${c.annual_license_cost.toLocaleString("sv-SE")} kr`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {c.annual_operations_cost != null
                      ? `${c.annual_operations_cost.toLocaleString("sv-SE")} kr`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Ta bort avtal ${c.supplier_name}`}
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteTarget(c)}
                    >
                      <TrashIcon className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Nytt avtal</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <FormField label="Leverantör" required>
              <Input
                value={form.supplier_name}
                onChange={(e) => setForm((f) => ({ ...f, supplier_name: e.target.value }))}
                placeholder="Leverantörens namn"
              />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Startdatum">
                <Input
                  type="date"
                  value={form.contract_start}
                  onChange={(e) => setForm((f) => ({ ...f, contract_start: e.target.value }))}
                />
              </FormField>
              <FormField label="Slutdatum">
                <Input
                  type="date"
                  value={form.contract_end}
                  onChange={(e) => setForm((f) => ({ ...f, contract_end: e.target.value }))}
                />
              </FormField>
            </div>
            <FormField label="Licensmodell">
              <Input
                value={form.license_model}
                onChange={(e) => setForm((f) => ({ ...f, license_model: e.target.value }))}
                placeholder="t.ex. Per användare, Namngivna licenser"
              />
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Årlig licenskostnad (kr)">
                <Input
                  type="number"
                  min={0}
                  value={form.annual_license_cost}
                  onChange={(e) => setForm((f) => ({ ...f, annual_license_cost: e.target.value }))}
                  placeholder="0"
                />
              </FormField>
              <FormField label="Årlig driftskostnad (kr)">
                <Input
                  type="number"
                  min={0}
                  value={form.annual_operations_cost}
                  onChange={(e) => setForm((f) => ({ ...f, annual_operations_cost: e.target.value }))}
                  placeholder="0"
                />
              </FormField>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Uppsägningstid (månader)">
                <Input
                  type="number"
                  min={0}
                  value={form.notice_period_months}
                  onChange={(e) => setForm((f) => ({ ...f, notice_period_months: e.target.value }))}
                  placeholder="0"
                />
              </FormField>
              <FormField label="SLA-nivå">
                <Input
                  value={form.sla_description}
                  onChange={(e) => setForm((f) => ({ ...f, sla_description: e.target.value }))}
                  placeholder="t.ex. 99.9%"
                />
              </FormField>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.auto_renewal}
                onChange={(e) => setForm((f) => ({ ...f, auto_renewal: e.target.checked }))}
                className="rounded border-input"
              />
              Automatisk förlängning
            </label>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort avtal"
        description={`Är du säker på att du vill ta bort avtalet med ${deleteTarget?.supplier_name ?? ""}?`}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
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
                    <span>-&gt;</span>
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

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name])
  )

  const deleteMutation = useMutation({
    mutationFn: () => deleteSystem(system!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["systems"] })
      toast.success("System borttaget")
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
          <TabsTrigger value="gdpr">GDPR</TabsTrigger>
          <TabsTrigger value="avtal">Avtal</TabsTrigger>
          <TabsTrigger value="ovrigt">Övrig data</TabsTrigger>
          <TabsTrigger value="andringslogg">Ändringslogg</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-4">
          <OversiktTab system={system} />
        </TabsContent>

        <TabsContent value="klassning" className="mt-4">
          <KlassningTab classifications={system.classifications} systemId={system.id} />
        </TabsContent>

        <TabsContent value="agare" className="mt-4">
          <AgareTab owners={system.owners} orgNameMap={orgNameMap} systemId={system.id} />
        </TabsContent>

        <TabsContent value="integrationer" className="mt-4">
          <IntegrationerTab integrations={system.integrations ?? []} systemId={system.id} />
        </TabsContent>

        <TabsContent value="gdpr" className="mt-4">
          <GdprTab systemId={system.id} />
        </TabsContent>

        <TabsContent value="avtal" className="mt-4">
          <AvtalTab systemId={system.id} />
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
