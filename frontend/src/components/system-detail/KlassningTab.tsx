import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon } from "lucide-react"
import { toast } from "sonner"
import { FormField } from "@/components/FormField"
import { createClassification } from "@/lib/api"
import type { Classification, ClassificationCreate } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { CiaBar } from "./helpers"

export function KlassningTab({
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
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    max={4}
                    value={form.confidentiality}
                    onChange={(e) => setForm((f) => ({ ...f, confidentiality: e.target.value }))}
                  />
                )}
              </FormField>
              <FormField label="Riktighet (R)" required>
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    max={4}
                    value={form.integrity}
                    onChange={(e) => setForm((f) => ({ ...f, integrity: e.target.value }))}
                  />
                )}
              </FormField>
              <FormField label="Tillgänglighet (T)" required>
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    max={4}
                    value={form.availability}
                    onChange={(e) => setForm((f) => ({ ...f, availability: e.target.value }))}
                  />
                )}
              </FormField>
              <FormField label="Spårbarhet (S)">
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    max={4}
                    placeholder="Valfritt"
                    value={form.traceability}
                    onChange={(e) => setForm((f) => ({ ...f, traceability: e.target.value }))}
                  />
                )}
              </FormField>
            </div>
            <FormField label="Klassad av" required>
              {(id) => (
                <Input
                  id={id}
                  value={form.classified_by}
                  onChange={(e) => setForm((f) => ({ ...f, classified_by: e.target.value }))}
                  placeholder="Namn eller e-post"
                />
              )}
            </FormField>
            <FormField label="Giltig till">
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  value={form.valid_until}
                  onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))}
                />
              )}
            </FormField>
            <FormField label="Anteckningar">
              {(id) => (
                <textarea
                  id={id}
                  className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50 placeholder:text-muted-foreground resize-none"
                  rows={3}
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="Valfria anteckningar..."
                />
              )}
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
