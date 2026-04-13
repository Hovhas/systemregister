import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { PlusIcon, TrashIcon, ExternalLinkIcon } from "lucide-react"

import type { SystemDetail, ComponentCreate } from "@/types"
import { getComponents, createComponent, deleteComponent } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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

export function KomponenterTab({ system }: { system: SystemDetail }) {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null)

  const emptyForm: Omit<ComponentCreate, "system_id" | "organization_id"> = {
    name: "",
    description: "",
    component_type: "",
    url: "",
    business_area: "",
  }
  const [form, setForm] = useState(emptyForm)

  const { data, isLoading } = useQuery({
    queryKey: ["components", "system", system.id],
    queryFn: () => getComponents({ system_id: system.id, limit: 200 }),
  })

  const components = data?.items ?? []

  const createMut = useMutation({
    mutationFn: (d: ComponentCreate) => createComponent(d),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["components", "system", system.id] })
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      setCreateOpen(false)
      setForm(emptyForm)
      toast.success("Komponent skapad")
    },
    onError: () => toast.error("Kunde inte skapa komponent"),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteComponent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["components", "system", system.id] })
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      setDeleteTarget(null)
      toast.success("Komponent borttagen")
    },
    onError: () => toast.error("Kunde inte ta bort komponent"),
  })

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    createMut.mutate({
      system_id: system.id,
      organization_id: system.organization_id,
      name: form.name,
      description: form.description || undefined,
      component_type: form.component_type || undefined,
      url: form.url || undefined,
      business_area: form.business_area || undefined,
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 size-4" />
          Ny komponent
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-10 rounded" />
          ))}
        </div>
      ) : components.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga komponenter registrerade for detta system.
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Namn</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Verksamhetsomrade</TableHead>
                <TableHead>URL</TableHead>
                <TableHead>Skapad</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {components.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.component_type ?? "\u2014"}</TableCell>
                  <TableCell>{c.business_area ?? "\u2014"}</TableCell>
                  <TableCell>
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Lank <ExternalLinkIcon className="size-3" />
                      </a>
                    ) : (
                      "\u2014"
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(c.created_at)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      aria-label={`Ta bort ${c.name}`}
                      onClick={() => setDeleteTarget({ id: c.id, name: c.name })}
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

      {/* Skapa-dialog */}
      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) { setCreateOpen(false); setForm(emptyForm) } else setCreateOpen(true) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny komponent</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input
                required
                placeholder="Komponentnamn"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Typ</label>
              <Input
                placeholder="t.ex. webbsida, kartvy, instans"
                value={form.component_type ?? ""}
                onChange={(e) => setForm({ ...form, component_type: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">URL</label>
              <Input
                placeholder="https://..."
                value={form.url ?? ""}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Verksamhetsomrade</label>
              <Input
                placeholder="Verksamhetsomrade"
                value={form.business_area ?? ""}
                onChange={(e) => setForm({ ...form, business_area: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input
                placeholder="Beskrivning"
                value={form.description ?? ""}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setCreateOpen(false); setForm(emptyForm) }}>
                Avbryt
              </Button>
              <Button type="submit" disabled={createMut.isPending || !form.name}>
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort komponent"
        description={`Ar du saker pa att du vill ta bort "${deleteTarget?.name ?? ""}"?`}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
        loading={deleteMut.isPending}
      />
    </div>
  )
}
