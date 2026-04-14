import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { FormField } from "@/components/FormField"
import { getContracts, createContract, deleteContract } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import type { Contract, ContractCreate } from "@/types"
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
import { Input } from "@/components/ui/input"

export function AvtalTab({ systemId }: { systemId: string }) {
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
    mutationFn: (id: string) => deleteContract(systemId, id),
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

  const [now] = useState(() => Date.now())

  function contractRowClass(contract: Contract): string {
    if (!contract.contract_end) return ""
    const daysLeft = Math.ceil(
      (new Date(contract.contract_end).getTime() - now) / (1000 * 60 * 60 * 24)
    )
    if (daysLeft < 0) return "bg-red-50 dark:bg-red-950/20"
    if (daysLeft <= 90) return "bg-orange-50 dark:bg-orange-950/20"
    return ""
  }

  function ContractExpiryBadge({ contract }: { contract: Contract }) {
    if (!contract.contract_end) return null
    const daysLeft = Math.ceil(
      (new Date(contract.contract_end).getTime() - now) / (1000 * 60 * 60 * 24)
    )
    if (daysLeft < 0) {
      return (
        <Badge variant="destructive" className="text-xs ml-1">
          Utgånget
        </Badge>
      )
    }
    if (daysLeft <= 30) {
      return (
        <Badge variant="destructive" className="text-xs ml-1">
          Går ut om {daysLeft} dag{daysLeft === 1 ? "" : "ar"}
        </Badge>
      )
    }
    if (daysLeft <= 90) {
      return (
        <Badge
          variant="outline"
          className="text-xs ml-1 text-orange-600 border-orange-300"
        >
          Går ut om {daysLeft} dagar
        </Badge>
      )
    }
    return null
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
        <div className="overflow-x-auto">
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
                  <TableCell className="text-sm">
                    <span className="text-muted-foreground">{c.contract_end ?? "—"}</span>
                    <ContractExpiryBadge contract={c} />
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
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Nytt avtal</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <FormField label="Leverantör" required>
              {(id) => (
                <Input
                  id={id}
                  value={form.supplier_name}
                  onChange={(e) => setForm((f) => ({ ...f, supplier_name: e.target.value }))}
                  placeholder="Leverantörens namn"
                />
              )}
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Startdatum">
                {(id) => (
                  <Input
                    id={id}
                    type="date"
                    value={form.contract_start}
                    onChange={(e) => setForm((f) => ({ ...f, contract_start: e.target.value }))}
                  />
                )}
              </FormField>
              <FormField label="Slutdatum">
                {(id) => (
                  <Input
                    id={id}
                    type="date"
                    value={form.contract_end}
                    onChange={(e) => setForm((f) => ({ ...f, contract_end: e.target.value }))}
                  />
                )}
              </FormField>
            </div>
            <FormField label="Licensmodell">
              {(id) => (
                <Input
                  id={id}
                  value={form.license_model}
                  onChange={(e) => setForm((f) => ({ ...f, license_model: e.target.value }))}
                  placeholder="t.ex. Per användare, Namngivna licenser"
                />
              )}
            </FormField>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Årlig licenskostnad (kr)">
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    value={form.annual_license_cost}
                    onChange={(e) => setForm((f) => ({ ...f, annual_license_cost: e.target.value }))}
                    placeholder="0"
                  />
                )}
              </FormField>
              <FormField label="Årlig driftskostnad (kr)">
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    value={form.annual_operations_cost}
                    onChange={(e) => setForm((f) => ({ ...f, annual_operations_cost: e.target.value }))}
                    placeholder="0"
                  />
                )}
              </FormField>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Uppsägningstid (månader)">
                {(id) => (
                  <Input
                    id={id}
                    type="number"
                    min={0}
                    value={form.notice_period_months}
                    onChange={(e) => setForm((f) => ({ ...f, notice_period_months: e.target.value }))}
                    placeholder="0"
                  />
                )}
              </FormField>
              <FormField label="SLA-nivå">
                {(id) => (
                  <Input
                    id={id}
                    value={form.sla_description}
                    onChange={(e) => setForm((f) => ({ ...f, sla_description: e.target.value }))}
                    placeholder="t.ex. 99.9%"
                  />
                )}
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
