import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createIntegration, getSystems } from "@/lib/api"
import { toast } from "sonner"
import { Criticality, IntegrationType } from "@/types"
import type { IntegrationCreate } from "@/types"
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
import { Input } from "@/components/ui/input"
import { FormField } from "@/components/FormField"

// --- Etiketter ---

const integrationTypeLabels: Record<string, string> = {
  api: "API",
  filöverföring: "Filöverföring",
  databasreplikering: "Databasreplikering",
  event: "Event",
  manuell: "Manuell",
}

const criticalityLabels: Record<Criticality, string> = {
  [Criticality.LOW]: "Låg",
  [Criticality.MEDIUM]: "Medel",
  [Criticality.HIGH]: "Hög",
  [Criticality.CRITICAL]: "Kritisk",
}

// --- Props ---

export interface IntegrationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Pre-fyller källsystem om angivet */
  systemId?: string
  /** Anropas efter lyckad skapning */
  onSuccess?: () => void
}

const EMPTY_FORM = (systemId?: string) => ({
  source_system_id: systemId ?? "",
  target_system_id: "",
  integration_type: "",
  criticality: "",
  frequency: "",
  is_external: false,
  external_party: "",
  description: "",
})

// --- Komponent ---

export default function IntegrationDialog({
  open,
  onOpenChange,
  systemId,
  onSuccess,
}: IntegrationDialogProps) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(EMPTY_FORM(systemId))
  const [error, setError] = useState("")

  const { data: allSystemsData } = useQuery({
    queryKey: ["systems", { limit: 500 }],
    queryFn: () => getSystems({ limit: 500 }),
    enabled: open,
  })
  const allSystems = allSystemsData?.items ?? []
  const systemNameMap = Object.fromEntries(allSystems.map((s) => [s.id, s.name]))

  const createMutation = useMutation({
    mutationFn: (data: IntegrationCreate) => createIntegration(data),
    onSuccess: () => {
      // Invalidera relevanta queries
      queryClient.invalidateQueries({ queryKey: ["integrations"] })
      if (systemId) {
        queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      }
      toast.success("Integration skapad")
      onOpenChange(false)
      setForm(EMPTY_FORM(systemId))
      setError("")
      onSuccess?.()
    },
    onError: () => setError("Kunde inte spara integration. Försök igen."),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.source_system_id) {
      setError("Källsystem är obligatoriskt")
      return
    }
    if (!form.target_system_id) {
      setError("Målsystem är obligatoriskt")
      return
    }
    if (!form.integration_type) {
      setError("Typ är obligatoriskt")
      return
    }
    const payload: IntegrationCreate = {
      source_system_id: form.source_system_id,
      target_system_id: form.target_system_id,
      integration_type: form.integration_type as IntegrationType,
    }
    if (form.criticality) payload.criticality = form.criticality as Criticality
    if (form.frequency.trim()) payload.frequency = form.frequency.trim()
    if (form.description.trim()) payload.description = form.description.trim()
    createMutation.mutate(payload)
  }

  function handleOpenChange(open: boolean) {
    if (!open) {
      setForm(EMPTY_FORM(systemId))
      setError("")
    }
    onOpenChange(open)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ny integration</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <FormField label="Källsystem" required>
            {(id) => (
              <Select
                value={form.source_system_id || undefined}
                onValueChange={(v) => setForm((f) => ({ ...f, source_system_id: v ?? "" }))}
              >
                <SelectTrigger id={id} className="w-full">
                  <SelectValue placeholder="Välj källsystem...">
                    {form.source_system_id
                      ? (systemNameMap[form.source_system_id] ?? form.source_system_id)
                      : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {allSystems
                    .filter((s) => s.id !== form.target_system_id)
                    .map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            )}
          </FormField>

          <FormField label="Målsystem" required>
            {(id) => (
              <Select
                value={form.target_system_id || undefined}
                onValueChange={(v) => setForm((f) => ({ ...f, target_system_id: v ?? "" }))}
              >
                <SelectTrigger id={id} className="w-full">
                  <SelectValue placeholder="Välj målsystem...">
                    {form.target_system_id
                      ? (systemNameMap[form.target_system_id] ?? form.target_system_id)
                      : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {allSystems
                    .filter((s) => s.id !== form.source_system_id)
                    .map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            )}
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Typ" required>
              {(id) => (
                <Select
                  value={form.integration_type || undefined}
                  onValueChange={(v) => setForm((f) => ({ ...f, integration_type: v ?? "" }))}
                >
                  <SelectTrigger id={id} className="w-full">
                    <SelectValue placeholder="Välj typ...">
                      {form.integration_type
                        ? (integrationTypeLabels[form.integration_type] ?? form.integration_type)
                        : undefined}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(integrationTypeLabels).map(([val, label]) => (
                      <SelectItem key={val} value={val}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormField>

            <FormField label="Kritikalitet">
              {(id) => (
                <Select
                  value={form.criticality || undefined}
                  onValueChange={(v) => setForm((f) => ({ ...f, criticality: v ?? "" }))}
                >
                  <SelectTrigger id={id} className="w-full">
                    <SelectValue placeholder="V��lj...">
                      {form.criticality
                        ? (criticalityLabels[form.criticality as Criticality] ?? form.criticality)
                        : undefined}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(criticalityLabels).map(([val, label]) => (
                      <SelectItem key={val} value={val}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormField>
          </div>

          <FormField label="Frekvens">
            {(id) => (
              <Input
                id={id}
                value={form.frequency}
                onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}
                placeholder="t.ex. Realtid, Dagligen"
              />
            )}
          </FormField>

          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.is_external}
              onChange={(e) => setForm((f) => ({ ...f, is_external: e.target.checked }))}
              className="rounded border-input"
            />
            Extern part
          </label>

          {form.is_external && (
            <FormField label="Extern part (namn)">
              {(id) => (
                <Input
                  id={id}
                  value={form.external_party}
                  onChange={(e) => setForm((f) => ({ ...f, external_party: e.target.value }))}
                  placeholder="t.ex. Leverantörens namn"
                />
              )}
            </FormField>
          )}

          <FormField label="Beskrivning">
            {(id) => (
              <textarea
                id={id}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50 placeholder:text-muted-foreground resize-none"
                rows={2}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Valfri beskrivning..."
              />
            )}
          </FormField>

          {error && <p className="text-xs text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Avbryt
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Sparar..." : "Spara"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
