import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { FormField } from "@/components/FormField"
import { getGDPRTreatments, createGDPRTreatment, deleteGDPRTreatment } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import type { GDPRTreatment, GDPRTreatmentCreate } from "@/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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

const legalBasisLabels: Record<string, string> = {
  samtycke: "Samtycke",
  avtal: "Avtal",
  rättslig_förpliktelse: "Rättslig förpliktelse",
  grundläggande_intresse: "Grundläggande intresse",
  allmänt_intresse: "Allmänt intresse",
  berättigat_intresse: "Berättigat intresse",
}

export function GdprTab({
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
              {(id) => (
                <Input
                  id={id}
                  value={form.data_categories}
                  onChange={(e) => setForm((f) => ({ ...f, data_categories: e.target.value }))}
                  placeholder="Kommaseparerat, t.ex. namn, adress"
                />
              )}
            </FormField>
            <FormField label="Kategorier av registrerade">
              {(id) => (
                <Input
                  id={id}
                  value={form.categories_of_data_subjects}
                  onChange={(e) => setForm((f) => ({ ...f, categories_of_data_subjects: e.target.value }))}
                  placeholder="t.ex. anställda, medborgare"
                />
              )}
            </FormField>
            <FormField label="Rättslig grund">
              {(id) => (
                <Select value={form.legal_basis} onValueChange={(v) => setForm((f) => ({ ...f, legal_basis: v ?? "" }))}>
                  <SelectTrigger id={id} className="w-full">
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
              )}
            </FormField>
            <FormField label="Gallringspolicy">
              {(id) => (
                <Input
                  id={id}
                  value={form.retention_policy}
                  onChange={(e) => setForm((f) => ({ ...f, retention_policy: e.target.value }))}
                  placeholder="t.ex. 7 år efter avslutad tjänst"
                />
              )}
            </FormField>
            <FormField label="RoPA-referens">
              {(id) => (
                <Input
                  id={id}
                  value={form.ropa_reference_id}
                  onChange={(e) => setForm((f) => ({ ...f, ropa_reference_id: e.target.value }))}
                  placeholder="Valfritt referens-ID"
                />
              )}
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
