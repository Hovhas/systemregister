import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation } from "@tanstack/react-query"

import { SystemCategory, LifecycleStatus, Criticality } from "@/types"
import type { SystemCreate, SystemUpdate } from "@/types"
import { createSystem, updateSystem, getSystem, getOrganizations } from "@/lib/api"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
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

// --- Formulärtillstånd ---

interface FormState {
  name: string
  organization_id: string
  description: string
  system_category: SystemCategory
  lifecycle_status: LifecycleStatus
  criticality: Criticality
  business_area: string
  hosting_model: string
  cloud_provider: string
  nis2_applicable: boolean
  treats_personal_data: boolean
}

const defaultForm: FormState = {
  name: "",
  organization_id: "",
  description: "",
  system_category: SystemCategory.VERKSAMHETSSYSTEM,
  lifecycle_status: LifecycleStatus.ACTIVE,
  criticality: Criticality.MEDIUM,
  business_area: "",
  hosting_model: "",
  cloud_provider: "",
  nis2_applicable: false,
  treats_personal_data: false,
}

// --- Hjälpkomponent ---

function FormField({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </label>
      {children}
    </div>
  )
}

// --- Huvudkomponent ---

export default function SystemFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [form, setForm] = useState<FormState>(defaultForm)
  const [apiError, setApiError] = useState<string | null>(null)

  // Hämta befintligt system vid redigering
  const { data: existingSystem } = useQuery({
    queryKey: ["system", id],
    queryFn: () => getSystem(id!),
    enabled: isEdit,
  })

  // Hämta organisationer
  const { data: organizations = [] } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  // Prefill formulär vid redigering
  useEffect(() => {
    if (existingSystem) {
      setForm({
        name: existingSystem.name,
        organization_id: existingSystem.organization_id,
        description: existingSystem.description,
        system_category: existingSystem.system_category,
        lifecycle_status: existingSystem.lifecycle_status,
        criticality: existingSystem.criticality,
        business_area: existingSystem.business_area ?? "",
        hosting_model: existingSystem.hosting_model ?? "",
        cloud_provider: existingSystem.cloud_provider ?? "",
        nis2_applicable: existingSystem.nis2_applicable,
        treats_personal_data: existingSystem.treats_personal_data,
      })
    }
  }, [existingSystem])

  const createMutation = useMutation({
    mutationFn: (data: SystemCreate) => createSystem(data),
    onSuccess: (system) => navigate(`/systems/${system.id}`),
    onError: () => setApiError("Kunde inte skapa system. Kontrollera fälten och försök igen."),
  })

  const updateMutation = useMutation({
    mutationFn: (data: SystemUpdate) => updateSystem(id!, data),
    onSuccess: (system) => navigate(`/systems/${system.id}`),
    onError: () => setApiError("Kunde inte uppdatera system. Kontrollera fälten och försök igen."),
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setApiError(null)

    const payload = {
      name: form.name,
      organization_id: form.organization_id,
      description: form.description,
      system_category: form.system_category,
      lifecycle_status: form.lifecycle_status,
      criticality: form.criticality,
      business_area: form.business_area || undefined,
      hosting_model: form.hosting_model || undefined,
      cloud_provider: form.cloud_provider || undefined,
      nis2_applicable: form.nis2_applicable,
      treats_personal_data: form.treats_personal_data,
    }

    if (isEdit) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload as SystemCreate)
    }
  }

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">
          {isEdit ? "Redigera system" : "Nytt system"}
        </h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(isEdit ? `/systems/${id}` : "/systems")}
        >
          Avbryt
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {/* Grundinformation */}
        <Card>
          <CardHeader>
            <CardTitle>Grundinformation</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Namn" required>
              <Input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Systemets namn"
                required
              />
            </FormField>

            <FormField label="Organisation" required>
              <Select
                value={form.organization_id}
                onValueChange={(val) => set("organization_id", val ?? "")}
                required
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj organisation">
                    {organizations.find((o) => o.id === form.organization_id)?.name}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {organizations.map((org) => (
                    <SelectItem key={org.id} value={org.id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <div className="md:col-span-2">
              <FormField label="Beskrivning" required>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                  value={form.description}
                  onChange={(e) => set("description", e.target.value)}
                  placeholder="Beskriv systemets syfte och funktion"
                  required
                />
              </FormField>
            </div>

            <FormField label="Kategori">
              <Select
                value={form.system_category}
                onValueChange={(val) => set("system_category", val as SystemCategory)}
              >
                <SelectTrigger>
                  <SelectValue>
                    {categoryLabels[form.system_category]}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {Object.values(SystemCategory).map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {categoryLabels[cat]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField label="Verksamhetsområde">
              <Input
                value={form.business_area}
                onChange={(e) => set("business_area", e.target.value)}
                placeholder="t.ex. HR, Ekonomi, Vård"
              />
            </FormField>
          </CardContent>
        </Card>

        {/* Status och kritikalitet */}
        <Card>
          <CardHeader>
            <CardTitle>Status och kritikalitet</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Livscykelstatus">
              <Select
                value={form.lifecycle_status}
                onValueChange={(val) => set("lifecycle_status", val as LifecycleStatus)}
              >
                <SelectTrigger>
                  <SelectValue>
                    {lifecycleLabels[form.lifecycle_status]}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {Object.values(LifecycleStatus).map((s) => (
                    <SelectItem key={s} value={s}>
                      {lifecycleLabels[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField label="Kritikalitet">
              <Select
                value={form.criticality}
                onValueChange={(val) => set("criticality", val as Criticality)}
              >
                <SelectTrigger>
                  <SelectValue>
                    {criticalityLabels[form.criticality]}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {Object.values(Criticality).map((c) => (
                    <SelectItem key={c} value={c}>
                      {criticalityLabels[c]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </CardContent>
        </Card>

        {/* Driftmiljö */}
        <Card>
          <CardHeader>
            <CardTitle>Driftmiljö</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Driftsättningsmodell">
              <Input
                value={form.hosting_model}
                onChange={(e) => set("hosting_model", e.target.value)}
                placeholder="on-premise / cloud / hybrid"
              />
            </FormField>

            <FormField label="Molnleverantör">
              <Input
                value={form.cloud_provider}
                onChange={(e) => set("cloud_provider", e.target.value)}
                placeholder="t.ex. Azure, AWS, GCP"
              />
            </FormField>
          </CardContent>
        </Card>

        {/* Compliance */}
        <Card>
          <CardHeader>
            <CardTitle>Compliance</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={form.nis2_applicable}
                onChange={(e) => set("nis2_applicable", e.target.checked)}
              />
              <span className="text-sm">NIS2-tillämplig</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={form.treats_personal_data}
                onChange={(e) => set("treats_personal_data", e.target.checked)}
              />
              <span className="text-sm">Behandlar personuppgifter</span>
            </label>
          </CardContent>
        </Card>

        {apiError && (
          <p className="text-sm text-destructive">{apiError}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(isEdit ? `/systems/${id}` : "/systems")}
          >
            Avbryt
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending
              ? isEdit
                ? "Sparar..."
                : "Skapar..."
              : isEdit
              ? "Spara ändringar"
              : "Skapa system"}
          </Button>
        </div>
      </form>
    </div>
  )
}
