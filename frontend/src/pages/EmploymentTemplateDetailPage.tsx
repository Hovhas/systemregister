import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeftIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  XIcon,
  DownloadIcon,
} from "lucide-react"
import { toast } from "sonner"

import {
  getEmploymentTemplate,
  deleteEmploymentTemplate,
  updateEmploymentTemplate,
  getResolvedAccess,
  resolvedAccessCsvUrl,
  getBusinessRoles,
  addRoleToTemplate,
  removeRoleFromTemplate,
  getOrganizations,
  getPositions,
} from "@/lib/api"
import type { EmploymentTemplateUpdate } from "@/types"
import { formatDate } from "@/lib/format"
import { accessLevelLabels, accessTypeLabels } from "@/lib/labels"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export default function EmploymentTemplateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [addRoleOpen, setAddRoleOpen] = useState(false)
  const [addRoleId, setAddRoleId] = useState("")
  const [editForm, setEditForm] = useState<{
    name: string
    notes: string
    is_active: boolean
  }>({ name: "", notes: "", is_active: true })

  const { data: tmpl, isLoading, isError, refetch } = useQuery({
    queryKey: ["employment-template", id],
    queryFn: () => getEmploymentTemplate(id!),
    enabled: !!id,
  })

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const { data: positions } = useQuery({
    queryKey: ["positions", "detail", tmpl?.organization_id],
    queryFn: () =>
      getPositions({
        organization_id: tmpl?.organization_id || undefined,
        limit: 200,
      }),
    enabled: !!tmpl,
  })

  const { data: resolvedAccess, refetch: refetchResolved } = useQuery({
    queryKey: ["resolved-access", id],
    queryFn: () => getResolvedAccess(id!),
    enabled: !!id,
  })

  const { data: allRoles } = useQuery({
    queryKey: ["business-roles", "for-template", tmpl?.organization_id],
    queryFn: () =>
      getBusinessRoles({
        organization_id: tmpl?.organization_id || undefined,
        limit: 200,
      }),
    enabled: !!tmpl,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteEmploymentTemplate(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employment-templates"] })
      toast.success("Anställningsmall borttagen")
      navigate("/employment-templates")
    },
    onError: () => toast.error("Kunde inte ta bort anställningsmall"),
  })

  const updateMut = useMutation({
    mutationFn: (data: EmploymentTemplateUpdate) =>
      updateEmploymentTemplate(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employment-template", id] })
      setEditOpen(false)
      toast.success("Anställningsmall uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera anställningsmall"),
  })

  const addRoleMut = useMutation({
    mutationFn: (roleId: string) => addRoleToTemplate(id!, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employment-template", id] })
      refetchResolved()
      setAddRoleOpen(false)
      setAddRoleId("")
      toast.success("Roll tillagd")
    },
    onError: () => toast.error("Kunde inte lägga till roll"),
  })

  const removeRoleMut = useMutation({
    mutationFn: (roleId: string) => removeRoleFromTemplate(id!, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employment-template", id] })
      refetchResolved()
      toast.success("Roll borttagen")
    },
    onError: () => toast.error("Kunde inte ta bort roll"),
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

  if (isError || !tmpl) {
    return (
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => navigate("/employment-templates")}
        >
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta anställningsmall.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      </div>
    )
  }

  const orgName =
    (orgs ?? []).find((o) => o.id === tmpl.organization_id)?.name ??
    tmpl.organization_id

  const positionName = tmpl.position_id
    ? ((positions?.items ?? []).find((p) => p.id === tmpl.position_id)?.title ??
      tmpl.position_id)
    : undefined

  function openEdit() {
    setEditForm({
      name: tmpl!.name,
      notes: tmpl!.notes ?? "",
      is_active: tmpl!.is_active,
    })
    setEditOpen(true)
  }

  const roleNameMap = Object.fromEntries(
    (allRoles?.items ?? []).map((r) => [r.id, r.name]),
  )

  const existingRoleIds = new Set(tmpl.role_ids)

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        items={[
          { label: "Anställningsmallar", href: "/employment-templates" },
          { label: tmpl.name },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="mt-0.5 shrink-0 w-fit"
          onClick={() => navigate("/employment-templates")}
        >
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{tmpl.name}</h1>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${tmpl.is_active ? "bg-green-100 text-green-800 border-green-200" : "bg-gray-100 text-gray-600 border-gray-200"}`}
            >
              {tmpl.is_active ? "Aktiv" : "Inaktiv"}
            </span>
          </div>
          {tmpl.notes && (
            <p className="text-sm text-muted-foreground max-w-xl">
              {tmpl.notes}
            </p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={openEdit}>
            <PencilIcon className="mr-1 size-4" /> Redigera
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteOpen(true)}
          >
            <TrashIcon className="mr-1 size-4" /> Ta bort
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Ta bort anställningsmall"
        description={`Är du säker på att du vill ta bort "${tmpl.name}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Grundinformation</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col">
            <InfoRow label="Organisation" value={orgName} />
            <InfoRow label="Befattning" value={positionName} />
            <InfoRow label="Version" value={String(tmpl.version)} />
            <InfoRow label="Godkänd av" value={tmpl.approved_by} />
            <InfoRow
              label="Godkänd"
              value={
                tmpl.approved_at ? formatDate(tmpl.approved_at) : undefined
              }
            />
            <InfoRow label="Skapad" value={formatDate(tmpl.created_at)} />
            <InfoRow label="Uppdaterad" value={formatDate(tmpl.updated_at)} />
          </CardContent>
        </Card>

        {/* Roles card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Roller i mallen</CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setAddRoleOpen(true)}
                aria-label="Lägg till roll"
              >
                <PlusIcon className="mr-1 size-4" />
                Lägg till
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {tmpl.role_ids.length === 0 ? (
              <p className="text-sm text-muted-foreground">Inga roller</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {tmpl.role_ids.map((rid) => (
                  <li
                    key={rid}
                    className="flex items-center justify-between text-sm py-1 border-b last:border-0"
                  >
                    <span className="font-medium">
                      {roleNameMap[rid] ?? rid}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-1 text-muted-foreground hover:text-destructive"
                      onClick={() => removeRoleMut.mutate(rid)}
                      aria-label={`Ta bort roll ${roleNameMap[rid] ?? rid}`}
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

      {/* Resolved access */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Resolved access</CardTitle>
            <a
              href={resolvedAccessCsvUrl(id!)}
              download={`resolved-access-${id}.csv`}
              aria-label="Ladda ner CSV"
            >
              <Button variant="outline" size="sm">
                <DownloadIcon className="mr-1 size-4" />
                Ladda ner CSV
              </Button>
            </a>
          </div>
        </CardHeader>
        <CardContent>
          {(resolvedAccess?.entries ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Inga åtkomsttillstånd beräknade
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>System</TableHead>
                  <TableHead>Nivå</TableHead>
                  <TableHead>Typ</TableHead>
                  <TableHead>Via roller</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(resolvedAccess?.entries ?? []).map((entry, idx) => (
                  <TableRow
                    key={entry.system_id}
                    className={idx % 2 === 1 ? "bg-muted/20" : ""}
                  >
                    <TableCell className="font-medium">
                      {entry.system_name}
                    </TableCell>
                    <TableCell>
                      {accessLevelLabels[entry.access_level]}
                    </TableCell>
                    <TableCell>
                      {accessTypeLabels[entry.access_type]}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {entry.contributing_role_names.join(", ")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add role dialog */}
      <Dialog
        open={addRoleOpen}
        onOpenChange={(open) => {
          if (!open) setAddRoleId("")
          setAddRoleOpen(open)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lägg till roll</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Verksamhetsroll *</label>
              <Select
                value={addRoleId || undefined}
                onValueChange={(v) => setAddRoleId(v ?? "")}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj roll">
                    {addRoleId
                      ? (allRoles?.items ?? []).find((r) => r.id === addRoleId)?.name
                      : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {(allRoles?.items ?? [])
                    .filter((r) => !existingRoleIds.has(r.id))
                    .map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAddRoleOpen(false)}
              >
                Avbryt
              </Button>
              <Button
                onClick={() => {
                  if (addRoleId) addRoleMut.mutate(addRoleId)
                }}
                disabled={addRoleMut.isPending || !addRoleId}
              >
                {addRoleMut.isPending ? "Lägger till..." : "Lägg till"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera anställningsmall</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              updateMut.mutate({
                name: editForm.name,
                notes: editForm.notes || null,
                is_active: editForm.is_active,
              })
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input
                required
                value={editForm.name}
                onChange={(e) =>
                  setEditForm({ ...editForm, name: e.target.value })
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Anteckningar</label>
              <Input
                value={editForm.notes}
                onChange={(e) =>
                  setEditForm({ ...editForm, notes: e.target.value })
                }
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="is-active"
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) =>
                  setEditForm({ ...editForm, is_active: e.target.checked })
                }
                className="rounded"
              />
              <label htmlFor="is-active" className="text-sm font-medium">
                Aktiv
              </label>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditOpen(false)}
              >
                Avbryt
              </Button>
              <Button
                type="submit"
                disabled={updateMut.isPending || !editForm.name}
              >
                {updateMut.isPending ? "Sparar..." : "Spara"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
