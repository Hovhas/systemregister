import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { FormField } from "@/components/FormField"
import { getOrganizations, createOwner, deleteOwner } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { OwnerRole } from "@/types"
import type { Owner, OwnerCreate } from "@/types"
import { ownerRoleLabels } from "@/lib/labels"
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

export function AgareTab({
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
    mutationFn: (id: string) => deleteOwner(systemId, id),
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
              {(id) => (
                <Select value={form.role} onValueChange={(v) => setForm((f) => ({ ...f, role: v ?? "" }))}>
                  <SelectTrigger id={id} className="w-full">
                    <SelectValue>
                      {form.role ? ownerRoleLabels[form.role as OwnerRole] ?? form.role : "Välj roll..."}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(ownerRoleLabels).map(([val, label]) => (
                      <SelectItem key={val} value={val}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormField>
            <FormField label="Namn" required>
              {(id) => (
                <Input
                  id={id}
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Fullständigt namn"
                />
              )}
            </FormField>
            <FormField label="E-post" required>
              {(id) => (
                <Input
                  id={id}
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="namn@sundsvall.se"
                />
              )}
            </FormField>
            <FormField label="Telefon">
              {(id) => (
                <Input
                  id={id}
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="Valfritt"
                />
              )}
            </FormField>
            <FormField label="Organisation" required>
              {(id) => (
                <Select value={form.organization_id} onValueChange={(v) => setForm((f) => ({ ...f, organization_id: v ?? "" }))}>
                  <SelectTrigger id={id} className="w-full">
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
