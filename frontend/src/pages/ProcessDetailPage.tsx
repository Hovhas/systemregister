import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon, XIcon } from "lucide-react"
import { toast } from "sonner"

import {
  getProcess, deleteProcess, updateProcess,
  getProcessSystems, linkProcessToSystem, unlinkProcessFromSystem,
  getProcessCapabilities, linkProcessToCapability, unlinkProcessFromCapability,
  getProcessInformationAssets, linkProcessToInformationAsset, unlinkProcessFromInformationAsset,
  getSystems, getCapabilities, getInformationAssets,
} from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Criticality } from "@/types"
import type { ProcessUpdate } from "@/types"
import { criticalityLabels, criticalityVariant } from "@/lib/labels"

export default function ProcessDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [linkSystemOpen, setLinkSystemOpen] = useState(false)
  const [linkCapOpen, setLinkCapOpen] = useState(false)
  const [linkAssetOpen, setLinkAssetOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: "", description: "", process_owner: "", criticality: "" })

  const { data: proc, isLoading, isError, refetch } = useQuery({
    queryKey: ["process", id],
    queryFn: () => getProcess(id!),
    enabled: !!id,
  })

  const { data: linkedSystems, refetch: refetchSystems } = useQuery({
    queryKey: ["process-systems", id],
    queryFn: () => getProcessSystems(id!),
    enabled: !!id,
  })

  const { data: linkedCaps, refetch: refetchCaps } = useQuery({
    queryKey: ["process-capabilities", id],
    queryFn: () => getProcessCapabilities(id!),
    enabled: !!id,
  })

  const { data: linkedAssets, refetch: refetchAssets } = useQuery({
    queryKey: ["process-assets", id],
    queryFn: () => getProcessInformationAssets(id!),
    enabled: !!id,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteProcess(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["processes"] })
      toast.success("Process borttagen")
      navigate("/processes")
    },
    onError: () => toast.error("Kunde inte ta bort process"),
  })

  const updateMut = useMutation({
    mutationFn: (data: ProcessUpdate) => updateProcess(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["process", id] })
      setEditOpen(false)
      toast.success("Process uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera process"),
  })

  const unlinkSystemMut = useMutation({
    mutationFn: (sysId: string) => unlinkProcessFromSystem(id!, sysId),
    onSuccess: () => { refetchSystems(); toast.success("System bortkopplat") },
    onError: () => toast.error("Kunde inte koppla bort system"),
  })

  const unlinkCapMut = useMutation({
    mutationFn: (capId: string) => unlinkProcessFromCapability(id!, capId),
    onSuccess: () => { refetchCaps(); toast.success("Förmåga bortkopplad") },
    onError: () => toast.error("Kunde inte koppla bort förmåga"),
  })

  const unlinkAssetMut = useMutation({
    mutationFn: (assetId: string) => unlinkProcessFromInformationAsset(id!, assetId),
    onSuccess: () => { refetchAssets(); toast.success("Informationsmängd bortkopplad") },
    onError: () => toast.error("Kunde inte koppla bort informationsmängd"),
  })

  async function handleLinkSystems(ids: string[]) {
    for (const sysId of ids) await linkProcessToSystem(id!, sysId)
    refetchSystems()
    toast.success(`${ids.length} system länkade`)
  }

  async function handleLinkCaps(ids: string[]) {
    for (const capId of ids) await linkProcessToCapability(id!, capId)
    refetchCaps()
    toast.success(`${ids.length} förmågor länkade`)
  }

  async function handleLinkAssets(ids: string[]) {
    for (const assetId of ids) await linkProcessToInformationAsset(id!, assetId)
    refetchAssets()
    toast.success(`${ids.length} informationsmängder länkade`)
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

  if (isError || !proc) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/processes")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta process.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      </div>
    )
  }

  function openEdit() {
    setEditForm({
      name: proc!.name,
      description: proc!.description ?? "",
      process_owner: proc!.process_owner ?? "",
      criticality: proc!.criticality ?? "",
    })
    setEditOpen(true)
  }

  const existingSystemIds = (linkedSystems ?? []).map((s) => s.id)
  const existingCapIds = (linkedCaps ?? []).map((c) => c.id)
  const existingAssetIds = (linkedAssets ?? []).map((a) => a.id)

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Processer", href: "/processes" }, { label: proc.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/processes")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{proc.name}</h1>
            {proc.criticality && (
              <Badge variant={criticalityVariant[proc.criticality]}>{criticalityLabels[proc.criticality]}</Badge>
            )}
          </div>
          {proc.description && <p className="text-sm text-muted-foreground max-w-xl">{proc.description}</p>}
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
        title="Ta bort process"
        description={`Är du säker på att du vill ta bort "${proc.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Card>
        <CardHeader><CardTitle>Grundinformation</CardTitle></CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Processägare" value={proc.process_owner} />
          <InfoRow label="Skapad" value={formatDate(proc.created_at)} />
          <InfoRow label="Uppdaterad" value={formatDate(proc.updated_at)} />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>System</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setLinkSystemOpen(true)} aria-label="Länka system">Länka</Button>
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
                    <Button variant="ghost" size="sm" className="h-6 px-1 text-muted-foreground hover:text-destructive" onClick={() => unlinkSystemMut.mutate(sys.id)} aria-label={`Koppla bort ${sys.name}`}>
                      <XIcon className="size-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Förmågor</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setLinkCapOpen(true)} aria-label="Länka förmåga">Länka</Button>
            </div>
          </CardHeader>
          <CardContent>
            {(linkedCaps ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Inga länkade förmågor</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {(linkedCaps ?? []).map((cap) => (
                  <li key={cap.id} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                    <span className="font-medium">{cap.name}</span>
                    <Button variant="ghost" size="sm" className="h-6 px-1 text-muted-foreground hover:text-destructive" onClick={() => unlinkCapMut.mutate(cap.id)} aria-label={`Koppla bort ${cap.name}`}>
                      <XIcon className="size-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Informationsmängder</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setLinkAssetOpen(true)} aria-label="Länka informationsmängd">Länka</Button>
            </div>
          </CardHeader>
          <CardContent>
            {(linkedAssets ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Inga länkade informationsmängder</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {(linkedAssets ?? []).map((asset) => (
                  <li key={asset.id} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                    <span className="font-medium">{asset.name}</span>
                    <Button variant="ghost" size="sm" className="h-6 px-1 text-muted-foreground hover:text-destructive" onClick={() => unlinkAssetMut.mutate(asset.id)} aria-label={`Koppla bort ${asset.name}`}>
                      <XIcon className="size-3" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <EntityLinkDialog
        open={linkSystemOpen}
        onOpenChange={setLinkSystemOpen}
        title="Länka system"
        description="Välj system att koppla till processen"
        queryKey={["systems", "link-dialog-proc-sys", id]}
        queryFn={() => getSystems({ limit: 200 })}
        renderOption={(item) => <span className="font-medium">{item.name}</span>}
        excludeIds={existingSystemIds}
        onSelect={handleLinkSystems}
        submitLabel="Länka"
      />

      <EntityLinkDialog
        open={linkCapOpen}
        onOpenChange={setLinkCapOpen}
        title="Länka förmåga"
        description="Välj förmåga att koppla till processen"
        queryKey={["capabilities", "link-dialog-proc-cap", id]}
        queryFn={() => getCapabilities({ limit: 200 })}
        renderOption={(item) => <span className="font-medium">{item.name}</span>}
        excludeIds={existingCapIds}
        onSelect={handleLinkCaps}
        submitLabel="Länka"
      />

      <EntityLinkDialog
        open={linkAssetOpen}
        onOpenChange={setLinkAssetOpen}
        title="Länka informationsmängd"
        description="Välj informationsmängd att koppla till processen"
        queryKey={["information-assets", "link-dialog-proc-asset", id]}
        queryFn={() => getInformationAssets({ limit: 200 })}
        renderOption={(item) => <span className="font-medium">{item.name}</span>}
        excludeIds={existingAssetIds}
        onSelect={handleLinkAssets}
        submitLabel="Länka"
      />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera process</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              updateMut.mutate({
                name: editForm.name,
                description: editForm.description || null,
                process_owner: editForm.process_owner || null,
                criticality: editForm.criticality ? (editForm.criticality as Criticality) : null,
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
              <label className="text-sm font-medium">Processägare</label>
              <Input value={editForm.process_owner} onChange={(e) => setEditForm({ ...editForm, process_owner: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Kritikalitet</label>
              <Select value={editForm.criticality} onValueChange={(val) => setEditForm({ ...editForm, criticality: val ?? "" })}>
                <SelectTrigger><SelectValue placeholder="Välj kritikalitet" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Ingen</SelectItem>
                  {Object.values(Criticality).map((v) => (
                    <SelectItem key={v} value={v}>{criticalityLabels[v]}</SelectItem>
                  ))}
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
