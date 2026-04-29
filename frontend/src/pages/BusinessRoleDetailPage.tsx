import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon, XIcon, PlusIcon } from "lucide-react"
import { toast } from "sonner"

import {
  getBusinessRole,
  deleteBusinessRole,
  updateBusinessRole,
  getRoleSystems,
  createRoleAccess,
  deleteRoleAccess,
  getSystems,
  getOrganizations,
} from "@/lib/api"
import type { BusinessRoleUpdate, RoleSystemAccessCreate } from "@/types"
import { AccessLevel, AccessType } from "@/types"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const emptyAccessForm: Omit<RoleSystemAccessCreate, "business_role_id"> = {
  system_id: "",
  access_level: AccessLevel.READ,
  access_type: AccessType.BIRTHRIGHT,
  justification: null,
}

export default function BusinessRoleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [accessOpen, setAccessOpen] = useState(false)
  const [accessForm, setAccessForm] =
    useState<Omit<RoleSystemAccessCreate, "business_role_id">>({
      ...emptyAccessForm,
    })
  const [editForm, setEditForm] = useState<{
    name: string
    description: string
    role_owner: string
  }>({ name: "", description: "", role_owner: "" })

  const { data: role, isLoading, isError, refetch } = useQuery({
    queryKey: ["business-role", id],
    queryFn: () => getBusinessRole(id!),
    enabled: !!id,
  })

  const { data: roleSystems, refetch: refetchSystems } = useQuery({
    queryKey: ["role-systems", id],
    queryFn: () => getRoleSystems(id!),
    enabled: !!id,
  })

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const { data: allSystems } = useQuery({
    queryKey: ["systems", "role-dialog"],
    queryFn: () => getSystems({ limit: 200 }),
    enabled: accessOpen,
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteBusinessRole(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["business-roles"] })
      toast.success("Verksamhetsroll borttagen")
      navigate("/business-roles")
    },
    onError: () => toast.error("Kunde inte ta bort verksamhetsroll"),
  })

  const updateMut = useMutation({
    mutationFn: (data: BusinessRoleUpdate) => updateBusinessRole(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["business-role", id] })
      setEditOpen(false)
      toast.success("Verksamhetsroll uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera verksamhetsroll"),
  })

  const addAccessMut = useMutation({
    mutationFn: (data: RoleSystemAccessCreate) => createRoleAccess(data),
    onSuccess: () => {
      refetchSystems()
      setAccessOpen(false)
      setAccessForm({ ...emptyAccessForm })
      toast.success("Systemåtkomst tillagd")
    },
    onError: () => toast.error("Kunde inte lägga till systemåtkomst"),
  })

  const removeAccessMut = useMutation({
    mutationFn: (accessId: string) => deleteRoleAccess(accessId),
    onSuccess: () => {
      refetchSystems()
      toast.success("Systemåtkomst borttagen")
    },
    onError: () => toast.error("Kunde inte ta bort systemåtkomst"),
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

  if (isError || !role) {
    return (
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => navigate("/business-roles")}
        >
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta verksamhetsroll.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      </div>
    )
  }

  const orgName =
    (orgs ?? []).find((o) => o.id === role.organization_id)?.name ??
    role.organization_id

  function openEdit() {
    setEditForm({
      name: role!.name,
      description: role!.description ?? "",
      role_owner: role!.role_owner ?? "",
    })
    setEditOpen(true)
  }

  const existingSystemIds = new Set((roleSystems ?? []).map((rs) => rs.system_id))

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        items={[
          { label: "Verksamhetsroller", href: "/business-roles" },
          { label: role.name },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="mt-0.5 shrink-0 w-fit"
          onClick={() => navigate("/business-roles")}
        >
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{role.name}</h1>
          {role.description && (
            <p className="text-sm text-muted-foreground max-w-xl">
              {role.description}
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
        title="Ta bort verksamhetsroll"
        description={`Är du säker på att du vill ta bort "${role.name}"?`}
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
            <InfoRow label="Rollägare" value={role.role_owner} />
            <InfoRow
              label="Giltig från"
              value={role.valid_from ? formatDate(role.valid_from) : undefined}
            />
            <InfoRow
              label="Giltig till"
              value={role.valid_until ? formatDate(role.valid_until) : undefined}
            />
            <InfoRow label="Skapad" value={formatDate(role.created_at)} />
            <InfoRow label="Uppdaterad" value={formatDate(role.updated_at)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Systemåtkomst</CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setAccessOpen(true)}
                aria-label="Lägg till systemåtkomst"
              >
                <PlusIcon className="mr-1 size-4" />
                Lägg till
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {(roleSystems ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Inga systemåtkomster
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>System</TableHead>
                    <TableHead>Nivå</TableHead>
                    <TableHead>Typ</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(roleSystems ?? []).map((rs) => (
                    <TableRow key={rs.access_id}>
                      <TableCell className="font-medium">
                        {rs.system_name}
                      </TableCell>
                      <TableCell>
                        {accessLevelLabels[rs.access_level]}
                      </TableCell>
                      <TableCell>
                        {accessTypeLabels[rs.access_type]}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-1 text-muted-foreground hover:text-destructive"
                          onClick={() =>
                            removeAccessMut.mutate(rs.access_id)
                          }
                          aria-label={`Ta bort åtkomst till ${rs.system_name}`}
                        >
                          <XIcon className="size-3" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add access dialog */}
      <Dialog
        open={accessOpen}
        onOpenChange={(open) => {
          if (!open) setAccessForm({ ...emptyAccessForm })
          setAccessOpen(open)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lägg till systemåtkomst</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              addAccessMut.mutate({ ...accessForm, business_role_id: id! })
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">System *</label>
              <Select
                value={accessForm.system_id || undefined}
                onValueChange={(v) =>
                  setAccessForm({ ...accessForm, system_id: v ?? "" })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Välj system">
                    {accessForm.system_id
                      ? (allSystems?.items ?? []).find((s) => s.id === accessForm.system_id)?.name
                      : undefined}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {(allSystems?.items ?? [])
                    .filter((s) => !existingSystemIds.has(s.id))
                    .map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Åtkomstnivå *</label>
              <Select
                value={accessForm.access_level}
                onValueChange={(v) =>
                  setAccessForm({
                    ...accessForm,
                    access_level: v as AccessLevel,
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(AccessLevel).map((lvl) => (
                    <SelectItem key={lvl} value={lvl}>
                      {accessLevelLabels[lvl]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Åtkomsttyp</label>
              <Select
                value={accessForm.access_type}
                onValueChange={(v) =>
                  setAccessForm({
                    ...accessForm,
                    access_type: v as AccessType,
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(AccessType).map((t) => (
                    <SelectItem key={t} value={t}>
                      {accessTypeLabels[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Motivering</label>
              <Input
                placeholder="Motivering"
                value={accessForm.justification ?? ""}
                onChange={(e) =>
                  setAccessForm({
                    ...accessForm,
                    justification: e.target.value || null,
                  })
                }
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAccessOpen(false)}
              >
                Avbryt
              </Button>
              <Button
                type="submit"
                disabled={
                  addAccessMut.isPending || !accessForm.system_id
                }
              >
                {addAccessMut.isPending ? "Lägger till..." : "Lägg till"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera verksamhetsroll</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              updateMut.mutate({
                name: editForm.name,
                description: editForm.description || null,
                role_owner: editForm.role_owner || null,
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
              <label className="text-sm font-medium">Rollägare</label>
              <Input
                value={editForm.role_owner}
                onChange={(e) =>
                  setEditForm({ ...editForm, role_owner: e.target.value })
                }
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Beskrivning</label>
              <Input
                value={editForm.description}
                onChange={(e) =>
                  setEditForm({ ...editForm, description: e.target.value })
                }
              />
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
