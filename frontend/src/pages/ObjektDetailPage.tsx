import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"

import { getObjektById, deleteObjekt, updateObjekt, getSystems, getOrganizations } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
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

export default function ObjektDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: "", description: "", object_owner: "", object_leader: "" })

  const { data: objekt, isLoading, isError, refetch } = useQuery({
    queryKey: ["objekt", id],
    queryFn: () => getObjektById(id!),
    enabled: !!id,
  })

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  // Fetch systems belonging to this objekt
  const { data: systemsData } = useQuery({
    queryKey: ["systems", "objekt", id],
    queryFn: () => getSystems({ limit: 200 }),
    enabled: !!id,
  })
  const linkedSystems = (systemsData?.items ?? []).filter((s) => s.objekt_id === id)

  const deleteMut = useMutation({
    mutationFn: () => deleteObjekt(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["objekt"] })
      toast.success("Objekt borttaget")
      navigate("/objekt")
    },
    onError: () => toast.error("Kunde inte ta bort objekt"),
  })

  const updateMut = useMutation({
    mutationFn: (data: typeof editForm) => updateObjekt(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["objekt", id] })
      setEditOpen(false)
      toast.success("Objekt uppdaterat")
    },
    onError: () => toast.error("Kunde inte uppdatera objekt"),
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

  if (isError || !objekt) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/objekt")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hamta objekt.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Forsok igen</Button>
        </div>
      </div>
    )
  }

  function openEdit() {
    setEditForm({
      name: objekt!.name,
      description: objekt!.description ?? "",
      object_owner: objekt!.object_owner ?? "",
      object_leader: objekt!.object_leader ?? "",
    })
    setEditOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Objekt", href: "/objekt" }, { label: objekt.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/objekt")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{objekt.name}</h1>
          {objekt.description && (
            <p className="text-sm text-muted-foreground max-w-xl">{objekt.description}</p>
          )}
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
        title="Ta bort objekt"
        description={`Ar du saker pa att du vill ta bort "${objekt.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Tabs defaultValue="oversikt" className="mt-2">
        <TabsList>
          <TabsTrigger value="oversikt">Oversikt</TabsTrigger>
          <TabsTrigger value="system">
            System
            {linkedSystems.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">({linkedSystems.length})</span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-6">
          <Card>
            <CardHeader><CardTitle>Detaljer</CardTitle></CardHeader>
            <CardContent className="flex flex-col">
              <InfoRow label="Organisation" value={orgNameMap[objekt.organization_id] ?? objekt.organization_id} />
              <InfoRow label="Objektagare" value={objekt.object_owner} />
              <InfoRow label="Objektledare" value={objekt.object_leader} />
              <InfoRow label="Beskrivning" value={objekt.description} />
              <InfoRow label="Skapad" value={formatDate(objekt.created_at)} />
              <InfoRow label="Uppdaterad" value={formatDate(objekt.updated_at)} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="mt-6">
          {linkedSystems.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">Inga system kopplade till detta objekt.</p>
          ) : (
            <div className="rounded-xl ring-1 ring-foreground/10">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Namn</TableHead>
                    <TableHead>Kategori</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Skapad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {linkedSystems.map((sys) => (
                    <TableRow
                      key={sys.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/systems/${sys.id}`)}
                    >
                      <TableCell className="font-medium">{sys.name}</TableCell>
                      <TableCell>{sys.system_category}</TableCell>
                      <TableCell>{sys.lifecycle_status}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(sys.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Redigera-dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera objekt</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); updateMut.mutate(editForm) }} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Objektagare</label>
              <Input value={editForm.object_owner} onChange={(e) => setEditForm({ ...editForm, object_owner: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Objektledare</label>
              <Input value={editForm.object_leader} onChange={(e) => setEditForm({ ...editForm, object_leader: e.target.value })} />
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
