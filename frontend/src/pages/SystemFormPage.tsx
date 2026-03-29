import { useState, useEffect } from "react"
import { useParams, useNavigate, useBlocker } from "react-router-dom"
import { useQuery, useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import axios from "axios"

import { SystemCategory, LifecycleStatus, Criticality, NIS2Classification } from "@/types"
import type { SystemCreate, SystemUpdate } from "@/types"
import { createSystem, updateSystem, getSystem, getOrganizations } from "@/lib/api"
import { categoryLabels, lifecycleLabels, criticalityLabels, nis2ClassificationLabels } from "@/lib/labels"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
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
import { Breadcrumb } from "@/components/Breadcrumb"
import { FormField } from "@/components/FormField"

// --- Formulärtillstånd ---

interface FormState {
  // Grundinformation
  name: string
  organization_id: string
  description: string
  system_category: SystemCategory
  business_area: string
  aliases: string
  // Status och kritikalitet
  lifecycle_status: LifecycleStatus
  criticality: Criticality
  // Driftmiljö
  hosting_model: string
  cloud_provider: string
  data_location_country: string
  product_name: string
  product_version: string
  // Livscykel
  deployment_date: string
  planned_decommission_date: string
  end_of_support_date: string
  // Backup och DR
  backup_frequency: string
  rpo: string
  rto: string
  dr_plan_exists: boolean
  // Compliance
  nis2_applicable: boolean
  nis2_classification: NIS2Classification | ""
  treats_personal_data: boolean
  treats_sensitive_data: boolean
  third_country_transfer: boolean
  has_elevated_protection: boolean
  security_protection: boolean
  last_risk_assessment_date: string
  klassa_reference_id: string
}

const defaultForm: FormState = {
  name: "",
  organization_id: "",
  description: "",
  system_category: SystemCategory.VERKSAMHETSSYSTEM,
  lifecycle_status: LifecycleStatus.ACTIVE,
  criticality: Criticality.MEDIUM,
  business_area: "",
  aliases: "",
  hosting_model: "",
  cloud_provider: "",
  data_location_country: "Sverige",
  product_name: "",
  product_version: "",
  deployment_date: "",
  planned_decommission_date: "",
  end_of_support_date: "",
  backup_frequency: "",
  rpo: "",
  rto: "",
  dr_plan_exists: false,
  nis2_applicable: false,
  nis2_classification: "",
  treats_personal_data: false,
  treats_sensitive_data: false,
  third_country_transfer: false,
  has_elevated_protection: false,
  security_protection: false,
  last_risk_assessment_date: "",
  klassa_reference_id: "",
}

// --- Huvudkomponent ---

export default function SystemFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [form, setForm] = useState<FormState>(defaultForm)
  const [apiError, setApiError] = useState<string | null>(null)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [submitted, setSubmitted] = useState(false)

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
        aliases: existingSystem.aliases ?? "",
        hosting_model: existingSystem.hosting_model ?? "",
        cloud_provider: existingSystem.cloud_provider ?? "",
        data_location_country: existingSystem.data_location_country ?? "Sverige",
        product_name: existingSystem.product_name ?? "",
        product_version: existingSystem.product_version ?? "",
        deployment_date: existingSystem.deployment_date ?? "",
        planned_decommission_date: existingSystem.planned_decommission_date ?? "",
        end_of_support_date: existingSystem.end_of_support_date ?? "",
        backup_frequency: existingSystem.backup_frequency ?? "",
        rpo: existingSystem.rpo ?? "",
        rto: existingSystem.rto ?? "",
        dr_plan_exists: existingSystem.dr_plan_exists,
        nis2_applicable: existingSystem.nis2_applicable,
        nis2_classification: existingSystem.nis2_classification ?? "",
        treats_personal_data: existingSystem.treats_personal_data,
        treats_sensitive_data: existingSystem.treats_sensitive_data,
        third_country_transfer: existingSystem.third_country_transfer,
        has_elevated_protection: existingSystem.has_elevated_protection,
        security_protection: existingSystem.security_protection,
        last_risk_assessment_date: existingSystem.last_risk_assessment_date ?? "",
        klassa_reference_id: existingSystem.klassa_reference_id ?? "",
      })
    }
  }, [existingSystem])

  // isDirty: formuläret är ändrat om det skiljer sig från defaultForm (nytt) eller prefyllda värden (redigering)
  const baselineForm = isEdit && existingSystem
    ? {
        name: existingSystem.name,
        organization_id: existingSystem.organization_id,
        description: existingSystem.description,
        system_category: existingSystem.system_category,
        lifecycle_status: existingSystem.lifecycle_status,
        criticality: existingSystem.criticality,
        business_area: existingSystem.business_area ?? "",
        aliases: existingSystem.aliases ?? "",
        hosting_model: existingSystem.hosting_model ?? "",
        cloud_provider: existingSystem.cloud_provider ?? "",
        data_location_country: existingSystem.data_location_country ?? "Sverige",
        product_name: existingSystem.product_name ?? "",
        product_version: existingSystem.product_version ?? "",
        deployment_date: existingSystem.deployment_date ?? "",
        planned_decommission_date: existingSystem.planned_decommission_date ?? "",
        end_of_support_date: existingSystem.end_of_support_date ?? "",
        backup_frequency: existingSystem.backup_frequency ?? "",
        rpo: existingSystem.rpo ?? "",
        rto: existingSystem.rto ?? "",
        dr_plan_exists: existingSystem.dr_plan_exists,
        nis2_applicable: existingSystem.nis2_applicable,
        nis2_classification: existingSystem.nis2_classification ?? "" as NIS2Classification | "",
        treats_personal_data: existingSystem.treats_personal_data,
        treats_sensitive_data: existingSystem.treats_sensitive_data,
        third_country_transfer: existingSystem.third_country_transfer,
        has_elevated_protection: existingSystem.has_elevated_protection,
        security_protection: existingSystem.security_protection,
        last_risk_assessment_date: existingSystem.last_risk_assessment_date ?? "",
        klassa_reference_id: existingSystem.klassa_reference_id ?? "",
      }
    : defaultForm

  const isDirty = !submitted && JSON.stringify(form) !== JSON.stringify(baselineForm)

  // Varna vid stängning av flik/webbläsare
  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault() }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [isDirty])

  // Varna vid in-app navigering (kräver data router / createBrowserRouter)
  const blocker = useBlocker(isDirty && !submitted)

  function handleParseError(err: unknown) {
    if (axios.isAxiosError(err) && err.response?.data?.detail) {
      const detail = err.response.data.detail
      if (Array.isArray(detail)) {
        const fieldErrors: Partial<Record<keyof FormState, string>> = {}
        for (const e of detail) {
          const field = e.loc?.[e.loc.length - 1] as keyof FormState | undefined
          if (field) fieldErrors[field] = e.msg
        }
        setErrors(fieldErrors)
        toast.error("Kontrollera fälten och försök igen")
      } else {
        const message = typeof detail === "string" ? detail : "Kunde inte spara systemet"
        setApiError(message)
        toast.error(message)
      }
    } else {
      const message = "Ett oväntat fel uppstod. Försök igen."
      setApiError(message)
      toast.error(message)
    }
  }

  const createMutation = useMutation({
    mutationFn: (data: SystemCreate) => createSystem(data),
    onSuccess: (system) => {
      setSubmitted(true)
      toast.success("System skapat")
      navigate(`/systems/${system.id}`)
    },
    onError: handleParseError,
  })

  const updateMutation = useMutation({
    mutationFn: (data: SystemUpdate) => updateSystem(id!, data),
    onSuccess: (system) => {
      setSubmitted(true)
      toast.success("System uppdaterat")
      navigate(`/systems/${system.id}`)
    },
    onError: handleParseError,
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setApiError(null)

    // Inline-validering
    const newErrors: Partial<Record<keyof FormState, string>> = {}
    if (!form.name.trim()) newErrors.name = "Namn är obligatoriskt"
    if (!form.organization_id) newErrors.organization_id = "Organisation är obligatorisk"
    if (!form.description.trim()) newErrors.description = "Beskrivning är obligatorisk"
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }
    setErrors({})

    const payload = {
      name: form.name,
      organization_id: form.organization_id,
      description: form.description,
      system_category: form.system_category,
      lifecycle_status: form.lifecycle_status,
      criticality: form.criticality,
      business_area: form.business_area || undefined,
      aliases: form.aliases || undefined,
      hosting_model: form.hosting_model || undefined,
      cloud_provider: form.cloud_provider || undefined,
      data_location_country: form.data_location_country || undefined,
      product_name: form.product_name || undefined,
      product_version: form.product_version || undefined,
      deployment_date: form.deployment_date || undefined,
      planned_decommission_date: form.planned_decommission_date || undefined,
      end_of_support_date: form.end_of_support_date || undefined,
      backup_frequency: form.backup_frequency || undefined,
      rpo: form.rpo || undefined,
      rto: form.rto || undefined,
      dr_plan_exists: form.dr_plan_exists,
      nis2_applicable: form.nis2_applicable,
      nis2_classification: form.nis2_classification || undefined,
      treats_personal_data: form.treats_personal_data,
      treats_sensitive_data: form.treats_sensitive_data,
      third_country_transfer: form.third_country_transfer,
      has_elevated_protection: form.has_elevated_protection,
      security_protection: form.security_protection,
      last_risk_assessment_date: form.last_risk_assessment_date || undefined,
      klassa_reference_id: form.klassa_reference_id || undefined,
    }

    if (isEdit) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload as SystemCreate)
    }
  }

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setApiError(null)
  }

  // onBlur-validering för obligatoriska fält
  function validateField(key: keyof FormState) {
    const value = form[key]
    const requiredFields: Partial<Record<keyof FormState, string>> = {
      name: "Namn är obligatoriskt",
      organization_id: "Organisation är obligatorisk",
      description: "Beskrivning är obligatorisk",
    }
    const msg = requiredFields[key]
    if (!msg) return
    if (typeof value === "string" && !value.trim()) {
      setErrors((prev) => ({ ...prev, [key]: msg }))
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-3xl">
      <Breadcrumb
        items={[
          { label: "System", href: "/systems" },
          { label: isEdit ? "Redigera" : "Nytt system" },
        ]}
      />



      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">
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

      <form onSubmit={handleSubmit} className="flex flex-col gap-8">
        {/* Grundinformation */}
        <Card>
          <CardHeader>
            <CardTitle>Grundinformation</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Namn" required error={errors.name}>
              {(id) => (
                <Input
                  id={id}
                  value={form.name}
                  onChange={(e) => { set("name", e.target.value); if (errors.name) setErrors((p) => ({ ...p, name: undefined })) }}
                  onBlur={() => validateField("name")}
                  placeholder="Systemets namn"
                />
              )}
            </FormField>

            <FormField label="Organisation" required error={errors.organization_id}>
              {(id) => (
                <Select
                  value={form.organization_id}
                  onValueChange={(val) => { set("organization_id", val ?? ""); if (errors.organization_id) setErrors((p) => ({ ...p, organization_id: undefined })); }}
                  onOpenChange={(open) => { if (!open) validateField("organization_id") }}
                >
                  <SelectTrigger id={id}>
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
              )}
            </FormField>

            <div className="md:col-span-2">
              <FormField label="Beskrivning" required error={errors.description}>
                {(id) => (
                  <textarea
                    id={id}
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
                    value={form.description}
                    onChange={(e) => { set("description", e.target.value); if (errors.description) setErrors((p) => ({ ...p, description: undefined })) }}
                    onBlur={() => validateField("description")}
                    placeholder="Beskriv systemets syfte och funktion"
                  />
                )}
              </FormField>
            </div>

            <FormField label="Kategori">
              {(id) => (
                <Select
                  value={form.system_category}
                  onValueChange={(val) => set("system_category", val as SystemCategory)}
                >
                  <SelectTrigger id={id}>
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
              )}
            </FormField>

            <FormField label="Verksamhetsområde">
              {(id) => (
                <Input
                  id={id}
                  value={form.business_area}
                  onChange={(e) => set("business_area", e.target.value)}
                  placeholder="t.ex. HR, Ekonomi, Vård"
                />
              )}
            </FormField>

            <div className="md:col-span-2">
              <FormField label="Alternativa namn">
                {(id) => (
                  <Input
                    id={id}
                    value={form.aliases}
                    onChange={(e) => set("aliases", e.target.value)}
                    placeholder="Alternativa namn, kommaseparerat"
                  />
                )}
              </FormField>
            </div>
          </CardContent>
        </Card>

        {/* Status och kritikalitet */}
        <Card>
          <CardHeader>
            <CardTitle>Status och kritikalitet</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Livscykelstatus">
              {(id) => (
                <Select
                  value={form.lifecycle_status}
                  onValueChange={(val) => set("lifecycle_status", val as LifecycleStatus)}
                >
                  <SelectTrigger id={id}>
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
              )}
            </FormField>

            <FormField label="Kritikalitet">
              {(id) => (
                <Select
                  value={form.criticality}
                  onValueChange={(val) => set("criticality", val as Criticality)}
                >
                  <SelectTrigger id={id}>
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
              )}
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
              {(id) => (
                <Input
                  id={id}
                  value={form.hosting_model}
                  onChange={(e) => set("hosting_model", e.target.value)}
                  placeholder="on-premise / cloud / hybrid"
                />
              )}
            </FormField>

            <FormField label="Molnleverantör">
              {(id) => (
                <Input
                  id={id}
                  value={form.cloud_provider}
                  onChange={(e) => set("cloud_provider", e.target.value)}
                  placeholder="t.ex. Azure, AWS, GCP"
                />
              )}
            </FormField>

            <FormField label="Datalagringsland">
              {(id) => (
                <Input
                  id={id}
                  value={form.data_location_country}
                  onChange={(e) => set("data_location_country", e.target.value)}
                  placeholder="t.ex. Sverige, EU"
                />
              )}
            </FormField>

            <FormField label="Produktnamn">
              {(id) => (
                <Input
                  id={id}
                  value={form.product_name}
                  onChange={(e) => set("product_name", e.target.value)}
                  placeholder="t.ex. Visma, SAP, Agresso"
                />
              )}
            </FormField>

            <FormField label="Produktversion">
              {(id) => (
                <Input
                  id={id}
                  value={form.product_version}
                  onChange={(e) => set("product_version", e.target.value)}
                  placeholder="t.ex. 2024.1"
                />
              )}
            </FormField>
          </CardContent>
        </Card>

        {/* Livscykel */}
        <Card>
          <CardHeader>
            <CardTitle>Livscykel</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Driftsättningsdatum">
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  value={form.deployment_date}
                  onChange={(e) => set("deployment_date", e.target.value)}
                />
              )}
            </FormField>

            <FormField label="Planerat avvecklingsdatum">
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  value={form.planned_decommission_date}
                  onChange={(e) => set("planned_decommission_date", e.target.value)}
                />
              )}
            </FormField>

            <FormField label="Slut på support">
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  value={form.end_of_support_date}
                  onChange={(e) => set("end_of_support_date", e.target.value)}
                />
              )}
            </FormField>
          </CardContent>
        </Card>

        {/* Backup och DR */}
        <Card>
          <CardHeader>
            <CardTitle>Backup och DR</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <FormField label="Backupfrekvens">
              {(id) => (
                <Input
                  id={id}
                  value={form.backup_frequency}
                  onChange={(e) => set("backup_frequency", e.target.value)}
                  placeholder="t.ex. Dagligen, Timvis"
                />
              )}
            </FormField>

            <FormField
              label="RPO (Recovery Point Objective)"
              helpText="Recovery Point Objective — hur mycket data som max får förloras"
            >
              {(id) => (
                <Input
                  id={id}
                  value={form.rpo}
                  onChange={(e) => set("rpo", e.target.value)}
                  placeholder="t.ex. 1 timme, 24 timmar"
                />
              )}
            </FormField>

            <FormField
              label="RTO (Recovery Time Objective)"
              helpText="Recovery Time Objective — max tillåten återställningstid"
            >
              {(id) => (
                <Input
                  id={id}
                  value={form.rto}
                  onChange={(e) => set("rto", e.target.value)}
                  placeholder="t.ex. 4 timmar, 1 dygn"
                />
              )}
            </FormField>

            <div className="md:col-span-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input accent-primary"
                  checked={form.dr_plan_exists}
                  onChange={(e) => set("dr_plan_exists", e.target.checked)}
                />
                <span className="text-sm">DR-plan finns</span>
              </label>
              <p className="text-xs text-muted-foreground mt-1 ml-6">Disaster Recovery — plan för återhämtning vid allvarligt avbrott</p>
            </div>
          </CardContent>
        </Card>

        {/* Compliance */}
        <Card>
          <CardHeader>
            <CardTitle>Compliance</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="flex flex-col gap-0.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-input accent-primary"
                    checked={form.nis2_applicable}
                    onChange={(e) => set("nis2_applicable", e.target.checked)}
                  />
                  <span className="text-sm">NIS2-tillämplig</span>
                </label>
                <p className="text-xs text-muted-foreground ml-6">EU-direktiv för cybersäkerhet — gäller samhällsviktiga verksamheter</p>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input accent-primary"
                  checked={form.treats_personal_data}
                  onChange={(e) => set("treats_personal_data", e.target.checked)}
                />
                <span className="text-sm">Behandlar personuppgifter</span>
              </label>

              <div className="flex flex-col gap-0.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-input accent-primary"
                    checked={form.treats_sensitive_data}
                    onChange={(e) => set("treats_sensitive_data", e.target.checked)}
                  />
                  <span className="text-sm">Behandlar känsliga personuppgifter (Art. 9)</span>
                </label>
                <p className="text-xs text-muted-foreground ml-6">Art. 9 GDPR — hälsa, etnicitet, politisk åskådning m.m.</p>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input accent-primary"
                  checked={form.third_country_transfer}
                  onChange={(e) => set("third_country_transfer", e.target.checked)}
                />
                <span className="text-sm">Tredjelandsöverföring</span>
              </label>

              <div className="flex flex-col gap-0.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-input accent-primary"
                    checked={form.has_elevated_protection}
                    onChange={(e) => set("has_elevated_protection", e.target.checked)}
                  />
                  <span className="text-sm">Förhöjt skyddsbehov (MSBFS 2020:7)</span>
                </label>
                <p className="text-xs text-muted-foreground ml-6">MSB:s föreskrifter om informationssäkerhet</p>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input accent-primary"
                  checked={form.security_protection}
                  onChange={(e) => set("security_protection", e.target.checked)}
                />
                <span className="text-sm">Säkerhetsskyddsklassat</span>
              </label>
            </div>

            {form.nis2_applicable && (
              <FormField label="NIS2-klassificering" helpText="EU-direktiv för cybersäkerhet — gäller samhällsviktiga verksamheter">
                {(id) => (
                  <Select
                    value={form.nis2_classification || undefined}
                    onValueChange={(val) => set("nis2_classification", (val as NIS2Classification) || "")}
                  >
                    <SelectTrigger id={id}>
                      <SelectValue placeholder="Välj klassificering">
                        {form.nis2_classification
                          ? nis2ClassificationLabels[form.nis2_classification as NIS2Classification]
                          : undefined}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NIS2Classification.ESSENTIAL}>
                        {nis2ClassificationLabels[NIS2Classification.ESSENTIAL]}
                      </SelectItem>
                      <SelectItem value={NIS2Classification.IMPORTANT}>
                        {nis2ClassificationLabels[NIS2Classification.IMPORTANT]}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </FormField>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Senaste riskbedömning">
                {(id) => (
                  <Input
                    id={id}
                    type="date"
                    value={form.last_risk_assessment_date}
                    onChange={(e) => set("last_risk_assessment_date", e.target.value)}
                  />
                )}
              </FormField>

              <FormField
                label="KLASSA-referens-ID"
                helpText="MSB:s verktyg för att klassificera information"
              >
                {(id) => (
                  <Input
                    id={id}
                    value={form.klassa_reference_id}
                    onChange={(e) => set("klassa_reference_id", e.target.value)}
                    placeholder="KLASSA-referens-ID"
                  />
                )}
              </FormField>
            </div>
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

      {/* Varningsdialog vid in-app navigering med osparade ändringar */}
      <Dialog
        open={blocker.state === "blocked"}
        onOpenChange={(open) => {
          if (!open && blocker.state === "blocked") blocker.reset?.()
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Osparade ändringar</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Du har osparade ändringar. Vill du verkligen lämna sidan?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => blocker.reset?.()}>
              Stanna kvar
            </Button>
            <Button variant="destructive" onClick={() => blocker.proceed?.()}>
              Lämna utan att spara
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
