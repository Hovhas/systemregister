import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon, PlusIcon, GripVerticalIcon } from "lucide-react"
import { toast } from "sonner"

import { getValueStream, deleteValueStream, updateValueStream } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { ValueStreamStage, ValueStreamUpdate } from "@/types"

function StageDialog({
  open,
  onOpenChange,
  initial,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  initial: Partial<ValueStreamStage>
  onSave: (stage: ValueStreamStage) => void
}) {
  const [name, setName] = useState(initial.name ?? "")
  const [description, setDescription] = useState(initial.description ?? "")

  function handleOpen(v: boolean) {
    if (v) {
      setName(initial.name ?? "")
      setDescription(initial.description ?? "")
    }
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial.name ? "Redigera steg" : "Lägg till steg"}</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            onSave({ name, description: description || null, order: initial.order ?? 0 })
          }}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Namn *</label>
            <Input required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Beskrivning</label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Avbryt</Button>
            <Button type="submit" disabled={!name}>Spara</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function ValueStreamDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [stageDialogOpen, setStageDialogOpen] = useState(false)
  const [editingStageIdx, setEditingStageIdx] = useState<number | null>(null)
  const [deleteStageIdx, setDeleteStageIdx] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ name: "", description: "" })

  const { data: vs, isLoading, isError, refetch } = useQuery({
    queryKey: ["value-stream", id],
    queryFn: () => getValueStream(id!),
    enabled: !!id,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteValueStream(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["value-streams"] })
      toast.success("Värdeström borttagen")
      navigate("/value-streams")
    },
    onError: () => toast.error("Kunde inte ta bort värdeström"),
  })

  const updateMut = useMutation({
    mutationFn: (data: ValueStreamUpdate) => updateValueStream(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["value-stream", id] })
      setEditOpen(false)
      toast.success("Värdeström uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera värdeström"),
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="skeleton h-6 w-48" />
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-48 rounded-xl" />
      </div>
    )
  }

  if (isError || !vs) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/value-streams")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta värdeström.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      </div>
    )
  }

  const stages = [...(vs.stages ?? [])].sort((a, b) => a.order - b.order)

  function handleSaveStage(stage: ValueStreamStage) {
    const updated = [...stages]
    if (editingStageIdx !== null) {
      updated[editingStageIdx] = { ...stage, order: stages[editingStageIdx].order }
    } else {
      updated.push({ ...stage, order: stages.length })
    }
    updateMut.mutate({ stages: updated })
    setStageDialogOpen(false)
    setEditingStageIdx(null)
  }

  function handleDeleteStage(idx: number) {
    const updated = stages.filter((_, i) => i !== idx).map((s, i) => ({ ...s, order: i }))
    updateMut.mutate({ stages: updated })
    setDeleteStageIdx(null)
  }

  function openAddStage() {
    setEditingStageIdx(null)
    setStageDialogOpen(true)
  }

  function openEditStage(idx: number) {
    setEditingStageIdx(idx)
    setStageDialogOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Värdeströmmar", href: "/value-streams" }, { label: vs.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/value-streams")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{vs.name}</h1>
          {vs.description && <p className="text-sm text-muted-foreground max-w-xl">{vs.description}</p>}
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={() => { setEditForm({ name: vs.name, description: vs.description ?? "" }); setEditOpen(true) }}>
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
        title="Ta bort värdeström"
        description={`Är du säker på att du vill ta bort "${vs.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Card>
        <CardHeader><CardTitle>Grundinformation</CardTitle></CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Skapad" value={formatDate(vs.created_at)} />
          <InfoRow label="Uppdaterad" value={formatDate(vs.updated_at)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Steg ({stages.length})</CardTitle>
            <Button size="sm" variant="outline" onClick={openAddStage} aria-label="Lägg till steg">
              <PlusIcon className="mr-1 size-4" /> Lägg till steg
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {stages.length === 0 ? (
            <p className="text-sm text-muted-foreground">Inga steg definierade ännu</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {stages.map((stage, idx) => (
                <li key={idx} className="flex items-start gap-3 rounded-lg border p-3">
                  <GripVerticalIcon className="size-4 mt-0.5 text-muted-foreground shrink-0" aria-hidden="true" />
                  <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                    <span className="text-xs text-muted-foreground">Steg {idx + 1}</span>
                    <span className="font-medium">{stage.name}</span>
                    {stage.description && <span className="text-sm text-muted-foreground">{stage.description}</span>}
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => openEditStage(idx)} aria-label={`Redigera steg ${stage.name}`}>
                      <PencilIcon className="size-3" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 px-2 text-destructive hover:text-destructive" onClick={() => setDeleteStageIdx(idx)} aria-label={`Ta bort steg ${stage.name}`}>
                      <TrashIcon className="size-3" />
                    </Button>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <StageDialog
        open={stageDialogOpen}
        onOpenChange={setStageDialogOpen}
        initial={editingStageIdx !== null ? stages[editingStageIdx] : { order: stages.length }}
        onSave={handleSaveStage}
      />

      <ConfirmDialog
        open={deleteStageIdx !== null}
        onOpenChange={(open) => { if (!open) setDeleteStageIdx(null) }}
        title="Ta bort steg"
        description={deleteStageIdx !== null ? `Ta bort steget "${stages[deleteStageIdx]?.name}"?` : ""}
        onConfirm={() => { if (deleteStageIdx !== null) handleDeleteStage(deleteStageIdx) }}
        loading={updateMut.isPending}
      />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera värdeström</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); updateMut.mutate({ name: editForm.name, description: editForm.description || null }) }} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
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
