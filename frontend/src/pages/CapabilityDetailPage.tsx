import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon, XIcon } from "lucide-react"
import { toast } from "sonner"

import {
  getCapability, deleteCapability, updateCapability,
  getCapabilitySystems, linkCapabilityToSystem, unlinkCapabilityFromSystem,
  getSystems,
} from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { CapabilityUpdate } from "@/types"

export default function CapabilityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [linkOpen, setLinkOpen] = useState(false)
  const [editForm, setEditForm] = useState<{ name: string; description: string; capability_owner: string; maturity_level: string }>({
    name: "", description: "", capability_owner: "", maturity_level: "",
  })

  const { data: cap, isLoading, isError, refetch } = useQuery({
    queryKey: ["capability", id],
    queryFn: () => getCapability(id!),
    enabled: !!id,
  })

  const { data: linkedSystems, refetch: refetchSystems } = useQuery({
    queryKey: ["capability-systems", id],
    queryFn: () => getCapabilitySystems(id!),
    enabled: !!id,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteCapability(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capabilities"] })
      toast.success("Förmåga borttagen")
      navigate("/capabilities")
    },
    onError: () => toast.error("Kunde inte ta bort förmåga"),
  })

  const updateMut = useMutation({
    mutationFn: (data: CapabilityUpdate) => updateCapability(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capability", id] })
      setEditOpen(false)
      toast.success("Förmåga uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera förmåga"),
  })

  const unlinkMut = useMutation({
    mutationFn: (systemId: string) => unlinkCapabilityFromSystem(id!, systemId),
    onSuccess: () => {
      refetchSystems()
      toast.success("System bortkopplat")
    },
    onError: () => toast.error("Kunde inte koppla bort system"),
  })

  async function handleLinkSystems(ids: string[]) {
    for (const sysId of ids) {
      await linkCapabilityToSystem(id!, sysId)
    }
    refetchSystems()
    toast.success(`${ids.length} system länkade`)
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="skeleton h-6 w-48" />
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-48 rounded-xl" />
      </div>
    )
  }

  if (isError || !cap) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/capabilities")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta förmåga.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      </div>
    )
  }

  function openEdit() {
    setEditForm({
      name: cap!.name,
      description: cap!.description ?? "",
      capability_owner: cap!.capability_owner ?? "",
      maturity_level: cap!.maturity_level != null ? String(cap!.maturity_level) : "",
    })
    setEditOpen(true)
  }

  const existingSystemIds = (linkedSystems ?? []).map((s) => s.id)

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Förmågor", href: "/capabilities" }, { label: cap.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/capabilities")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{cap.name}</h1>
          {cap.description && <p className="text-sm text-muted-foreground max-w-xl">{cap.description}</p>}
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={openEdit}>
            <PencilIcon className="mr-1 size-4" /> Redigera
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
            <TrashIcon className="mr-1 size-4" /> Ta bort
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Ta bort förmåga"
        description={`Är du säker på att du vill ta bort "${cap.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Grundinformation</CardTitle></CardHeader>
          <CardContent className="flex flex-col">
            <InfoRow label="Förmågeägare" value={cap.capability_owner} />
            <InfoRow label="Mognadsnivå" value={cap.maturity_level != null ? String(cap.maturity_level) : undefined} />
            <InfoRow label="Skapad" value={formatDate(cap.created_at)} />
            <InfoRow label="Uppdaterad" value={formatDate(cap.updated_at)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Länkade system</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setLinkOpen(true)} aria-label="Länka system till förmåga">
                Länka system
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {(linkedSystems ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Inga länkade system</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {(linkedSystems ?? []).map((sys) => (
                  <li key={sys.id} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                    <span className="font-medium">{sys.name}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-1 text-muted-foreground hover:text-destructive"
                      onClick={() => unlinkMut.mutate(sys.id)}
                      aria-label={`Koppla bort system ${sys.name}`}
                    >
                      <XIcon className="size-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {cap.process_count != null && cap.process_count > 0 && (
        <Card>
          <CardHeader><CardTitle>Länkade processer</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {cap.process_count} process{cap.process_count !== 1 ? "er" : ""} länkad{cap.process_count !== 1 ? "e" : ""} till denna förmåga. Hantera kopplingar från processvyn.
            </p>
          </CardContent>
        </Card>
      )}

      <EntityLinkDialog
        open={linkOpen}
        onOpenChange={setLinkOpen}
        title="Länka system"
        description="Välj system att koppla till förmågan"
        queryKey={["systems", "link-dialog-cap", id]}
        queryFn={() => getSystems({ limit: 200 })}
        renderOption={(item) => <span className="font-medium">{item.name}</span>}
        excludeIds={existingSystemIds}
        onSelect={handleLinkSystems}
        submitLabel="Länka"
      />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera förmåga</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              updateMut.mutate({
                name: editForm.name,
                description: editForm.description || null,
                capability_owner: editForm.capability_owner || null,
                maturity_level: editForm.maturity_level ? Number(editForm.maturity_level) : null,
              })
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Ägare</label>
              <Input value={editForm.capability_owner} onChange={(e) => setEditForm({ ...editForm, capability_owner: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Mognadsnivå (1–5)</label>
              <Select value={editForm.maturity_level ?? ""} onValueChange={(val) => setEditForm({ ...editForm, maturity_level: val ?? "" })}>
                <SelectTrigger><SelectValue placeholder="Välj nivå" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Ingen</SelectItem>
                  {[1, 2, 3, 4, 5].map((v) => <SelectItem key={v} value={String(v)}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditOpen(false)}>Avbryt</Button>
              <Button type="submit" disabled={updateMut.isPending || !editForm.name}>
                {updateMut.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
