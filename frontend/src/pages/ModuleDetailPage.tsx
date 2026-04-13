import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"

import { AIRiskClass } from "@/types"
import { getModule, deleteModule, updateModule, getSystems, getOrganizations, linkModuleToSystem } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { lifecycleLabels, aiRiskClassLabels, aiRiskBadgeClass } from "@/lib/labels"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export default function ModuleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [linkOpen, setLinkOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: "", description: "" })

  const { data: mod, isLoading, isError, refetch } = useQuery({
    queryKey: ["module", id],
    queryFn: () => getModule(id!),
    enabled: !!id,
  })

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  const deleteMut = useMutation({
    mutationFn: () => deleteModule(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modules"] })
      toast.success("Modul borttagen")
      navigate("/modules")
    },
    onError: () => toast.error("Kunde inte ta bort modul"),
  })

  const updateMut = useMutation({
    mutationFn: (data: typeof editForm) => updateModule(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["module", id] })
      setEditOpen(false)
      toast.success("Modul uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera modul"),
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

  if (isError || !mod) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/modules")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hamta modul.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Forsok igen</Button>
        </div>
      </div>
    )
  }

  function openEdit() {
    setEditForm({
      name: mod!.name,
      description: mod!.description ?? "",
    })
    setEditOpen(true)
  }

  async function handleLinkSystems(ids: string[]) {
    for (const sysId of ids) {
      await linkModuleToSystem(id!, sysId)
    }
    queryClient.invalidateQueries({ queryKey: ["module", id] })
    queryClient.invalidateQueries({ queryKey: ["systems"] })
    toast.success(`${ids.length} system lankade`)
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Moduler", href: "/modules" }, { label: mod.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/modules")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{mod.name}</h1>
            {mod.uses_ai && <Badge variant="default">AI</Badge>}
          </div>
          {mod.description && (
            <p className="text-sm text-muted-foreground max-w-xl">{mod.description}</p>
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
        title="Ta bort modul"
        description={`Ar du saker pa att du vill ta bort "${mod.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Tabs defaultValue="oversikt" className="mt-2">
        <TabsList>
          <TabsTrigger value="oversikt">Oversikt</TabsTrigger>
          {mod.uses_ai && <TabsTrigger value="ai">AI-information</TabsTrigger>}
          <TabsTrigger value="system">Lankade system</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Grundinformation</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Organisation" value={orgNameMap[mod.organization_id] ?? mod.organization_id} />
                <InfoRow label="Beskrivning" value={mod.description} />
                <InfoRow label="Livscykelstatus" value={mod.lifecycle_status ? lifecycleLabels[mod.lifecycle_status] ?? mod.lifecycle_status : null} />
                <InfoRow label="Driftmodell" value={mod.hosting_model} />
                <InfoRow label="Skapad" value={formatDate(mod.created_at)} />
                <InfoRow label="Uppdaterad" value={formatDate(mod.updated_at)} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Produkt</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Produktnamn" value={mod.product_name} />
                <InfoRow label="Version" value={mod.product_version} />
                <InfoRow label="Leverantor" value={mod.supplier} />
                <InfoRow label="Licens" value={mod.license_id} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {mod.uses_ai && (
          <TabsContent value="ai" className="mt-6">
            <Card>
              <CardHeader><CardTitle>AI-information</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Anvander AI" value={mod.uses_ai ? "Ja" : "Nej"} />
                <InfoRow
                  label="AI-riskklass"
                  value={
                    mod.ai_risk_class ? (
                      <span className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${aiRiskBadgeClass[mod.ai_risk_class as AIRiskClass] ?? ""}`}>
                        {aiRiskClassLabels[mod.ai_risk_class as AIRiskClass] ?? mod.ai_risk_class}
                      </span>
                    ) : null
                  }
                />
                <InfoRow label="AI-anvandning" value={mod.ai_usage_description} />
              </CardContent>
            </Card>
          </TabsContent>
        )}

        <TabsContent value="system" className="mt-6">
          <div className="flex flex-col gap-4">
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setLinkOpen(true)}>
                Lanka system
              </Button>
            </div>
            <p className="text-sm text-muted-foreground py-4">
              System som anvander denna modul visas har. Lank system via knappen ovan.
            </p>

            <EntityLinkDialog
              open={linkOpen}
              onOpenChange={setLinkOpen}
              title="Lanka system"
              description="Valj system att koppla till modulen"
              queryKey={["systems", "link-dialog-module"]}
              queryFn={() => getSystems({ limit: 200 })}
              renderOption={(item) => <span className="font-medium">{item.name}</span>}
              onSelect={handleLinkSystems}
              submitLabel="Lanka"
            />
          </div>
        </TabsContent>
      </Tabs>

      {/* Redigera-dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera modul</DialogTitle>
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
