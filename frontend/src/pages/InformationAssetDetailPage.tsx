import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"

import { getInformationAsset, deleteInformationAsset, updateInformationAsset, getSystems, getOrganizations, linkAssetToSystem } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { InfoRow, CiaBar } from "@/components/system-detail/helpers"
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

export default function InformationAssetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [linkOpen, setLinkOpen] = useState(false)
  const [editForm, setEditForm] = useState({ name: "", description: "", information_owner: "" })

  const { data: asset, isLoading, isError, refetch } = useQuery({
    queryKey: ["information-asset", id],
    queryFn: () => getInformationAsset(id!),
    enabled: !!id,
  })

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  const deleteMut = useMutation({
    mutationFn: () => deleteInformationAsset(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["information-assets"] })
      toast.success("Informationsmangd borttagen")
      navigate("/information-assets")
    },
    onError: () => toast.error("Kunde inte ta bort informationsmangd"),
  })

  const updateMut = useMutation({
    mutationFn: (data: typeof editForm) => updateInformationAsset(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["information-asset", id] })
      setEditOpen(false)
      toast.success("Informationsmangd uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera informationsmangd"),
  })

  async function handleLinkSystems(ids: string[]) {
    for (const sysId of ids) {
      await linkAssetToSystem(id!, sysId)
    }
    queryClient.invalidateQueries({ queryKey: ["information-asset", id] })
    queryClient.invalidateQueries({ queryKey: ["systems"] })
    toast.success(`${ids.length} system lankade`)
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

  if (isError || !asset) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/information-assets")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hamta informationsmangd.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Forsok igen</Button>
        </div>
      </div>
    )
  }

  function openEdit() {
    setEditForm({
      name: asset!.name,
      description: asset!.description ?? "",
      information_owner: asset!.information_owner ?? "",
    })
    setEditOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Informationsmangder", href: "/information-assets" }, { label: asset.name }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/information-assets")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{asset.name}</h1>
            {asset.contains_personal_data && <Badge variant="default">Personuppgifter</Badge>}
          </div>
          {asset.description && (
            <p className="text-sm text-muted-foreground max-w-xl">{asset.description}</p>
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
        title="Ta bort informationsmangd"
        description={`Ar du saker pa att du vill ta bort "${asset.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Tabs defaultValue="oversikt" className="mt-2">
        <TabsList>
          <TabsTrigger value="oversikt">Oversikt</TabsTrigger>
          <TabsTrigger value="gdpr">GDPR</TabsTrigger>
          <TabsTrigger value="ihp">IHP/arkiv</TabsTrigger>
          <TabsTrigger value="system">Lankade system</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Grundinformation</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Organisation" value={orgNameMap[asset.organization_id] ?? asset.organization_id} />
                <InfoRow label="Informationsagare" value={asset.information_owner} />
                <InfoRow label="Beskrivning" value={asset.description} />
                <InfoRow label="Skapad" value={formatDate(asset.created_at)} />
                <InfoRow label="Uppdaterad" value={formatDate(asset.updated_at)} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Klassning (K/R/T)</CardTitle></CardHeader>
              <CardContent className="flex flex-col gap-3 pt-2">
                {asset.confidentiality != null && (
                  <CiaBar label="K" title="Konfidentialitet" value={asset.confidentiality} />
                )}
                {asset.integrity != null && (
                  <CiaBar label="R" title="Riktighet" value={asset.integrity} />
                )}
                {asset.availability != null && (
                  <CiaBar label="T" title="Tillganglighet" value={asset.availability} />
                )}
                {asset.traceability != null && (
                  <CiaBar label="S" title="Sparbarhet" value={asset.traceability} />
                )}
                {asset.confidentiality == null && asset.integrity == null && asset.availability == null && (
                  <p className="text-sm text-muted-foreground">Ingen klassning satt</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="gdpr" className="mt-6">
          <Card>
            <CardHeader><CardTitle>GDPR</CardTitle></CardHeader>
            <CardContent className="flex flex-col">
              <InfoRow label="Innehaller personuppgifter" value={asset.contains_personal_data ? "Ja" : "Nej"} />
              <InfoRow label="Typ av personuppgifter" value={asset.personal_data_type} />
              <InfoRow label="Allman handling" value={asset.contains_public_records ? "Ja" : "Nej"} />
              <InfoRow label="ROPA-referens" value={asset.ropa_reference_id} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ihp" className="mt-6">
          <Card>
            <CardHeader><CardTitle>Informationshantering och arkiv</CardTitle></CardHeader>
            <CardContent className="flex flex-col">
              <InfoRow label="IHP-referens" value={asset.ihp_reference} />
              <InfoRow label="Bevarandeklass" value={asset.preservation_class} />
              <InfoRow label="Gallringsfrist" value={asset.retention_period} />
              <InfoRow label="Arkivansvarig" value={asset.archive_responsible} />
              <InfoRow label="E-arkivleverans" value={asset.e_archive_delivery} />
              <InfoRow label="Langtidsformat" value={asset.long_term_format} />
              <InfoRow label="Senaste IHP-granskning" value={formatDate(asset.last_ihp_review)} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="mt-6">
          <div className="flex flex-col gap-4">
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setLinkOpen(true)}>
                Lanka system
              </Button>
            </div>
            <p className="text-sm text-muted-foreground py-4">
              System som hanterar denna informationsmangd. Lank system via knappen ovan.
            </p>

            <EntityLinkDialog
              open={linkOpen}
              onOpenChange={setLinkOpen}
              title="Lanka system"
              description="Valj system att koppla till informationsmangden"
              queryKey={["systems", "link-dialog-asset"]}
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
            <DialogTitle>Redigera informationsmangd</DialogTitle>
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
              <label className="text-sm font-medium">Informationsagare</label>
              <Input value={editForm.information_owner} onChange={(e) => setEditForm({ ...editForm, information_owner: e.target.value })} />
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
