import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PencilIcon, Trash2Icon, PlusIcon, BuildingIcon } from "lucide-react"
import { toast } from "sonner"

import {
  getOrganizations,
  createOrganization,
  updateOrganization,
  deleteOrganization,
  getSystems,
} from "@/lib/api"
import {
  OrganizationType,
  type Organization,
  type OrganizationCreate,
  type OrganizationUpdate,
} from "@/types"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
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

// --- Hjälpfunktioner ---

const ORG_TYPE_LABELS: Record<OrganizationType, string> = {
  [OrganizationType.KOMMUN]: "Kommun",
  [OrganizationType.BOLAG]: "Bolag",
  [OrganizationType.SAMVERKAN]: "Samverkan",
  [OrganizationType.DIGIT]: "DigIT",
}

// --- Formulär-dialog ---

interface OrgFormDialogProps {
  open: boolean
  onClose: () => void
  organizations: Organization[]
  editing: Organization | null
}

function OrgFormDialog({
  open,
  onClose,
  organizations,
  editing,
}: OrgFormDialogProps) {
  const queryClient = useQueryClient()

  const [name, setName] = useState(editing?.name ?? "")
  const [orgNumber, setOrgNumber] = useState(editing?.org_number ?? "")
  const [orgType, setOrgType] = useState<OrganizationType>(
    editing?.org_type ?? OrganizationType.KOMMUN
  )
  const [parentOrgId, setParentOrgId] = useState<string>(
    editing?.parent_org_id ?? ""
  )
  const [nameError, setNameError] = useState("")

  // Återställ fält när dialogen öppnas eller editing-värde ändras
  const resetForm = () => {
    setName(editing?.name ?? "")
    setOrgNumber(editing?.org_number ?? "")
    setOrgType(editing?.org_type ?? OrganizationType.KOMMUN)
    setParentOrgId(editing?.parent_org_id ?? "")
    setNameError("")
  }

  // Säkerställ att formuläret alltid återställs korrekt vid öppning
  useEffect(() => {
    if (open) {
      resetForm()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editing?.id])

  const createMutation = useMutation({
    mutationFn: (data: OrganizationCreate) => createOrganization(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] })
      toast.success("Organisationen skapades.")
      onClose()
    },
    onError: () => toast.error("Kunde inte skapa organisationen."),
  })

  const updateMutation = useMutation({
    mutationFn: (data: OrganizationUpdate) =>
      updateOrganization(editing!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] })
      toast.success("Organisationen uppdaterades.")
      onClose()
    },
    onError: () => toast.error("Kunde inte uppdatera organisationen."),
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setNameError("Namn är obligatoriskt.")
      return
    }
    setNameError("")

    const payload = {
      name: name.trim(),
      org_number: orgNumber.trim() || undefined,
      org_type: orgType,
      parent_org_id: parentOrgId || undefined,
    }

    if (editing) {
      updateMutation.mutate({
        ...payload,
        parent_org_id: parentOrgId || null,
      })
    } else {
      createMutation.mutate(payload)
    }
  }

  // Filtrera bort den redigerade org från föräldrar-listan
  const parentOptions = organizations.filter(
    (o) => !editing || o.id !== editing.id
  )

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose()
        else resetForm()
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {editing ? "Redigera organisation" : "Ny organisation"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {/* Namn */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="org-name">
              Namn <span className="text-destructive">*</span>
            </label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Organisationsnamn"
              disabled={isPending}
            />
            {nameError && (
              <p className="text-xs text-destructive">{nameError}</p>
            )}
          </div>

          {/* Org-nummer */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="org-number">
              Org-nummer
            </label>
            <Input
              id="org-number"
              value={orgNumber}
              onChange={(e) => setOrgNumber(e.target.value)}
              placeholder="556000-0000"
              disabled={isPending}
            />
          </div>

          {/* Typ */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">
              Typ <span className="text-destructive">*</span>
            </label>
            <Select
              value={orgType}
              onValueChange={(v) => v && setOrgType(v as OrganizationType)}
              disabled={isPending}
            >
              <SelectTrigger>
                <SelectValue>{ORG_TYPE_LABELS[orgType]}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {Object.values(OrganizationType).map((t) => (
                  <SelectItem key={t} value={t}>
                    {ORG_TYPE_LABELS[t]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Moderorganisation */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Moderorganisation</label>
            <Select
              value={parentOrgId || "__none__"}
              onValueChange={(v) =>
                setParentOrgId(!v || v === "__none__" ? "" : v)
              }
              disabled={isPending}
            >
              <SelectTrigger>
                <SelectValue>
                  {parentOrgId
                    ? (organizations.find((o) => o.id === parentOrgId)?.name ??
                      "Okänd")
                    : "Ingen"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">Ingen</SelectItem>
                {parentOptions.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isPending}
            >
              Avbryt
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Sparar..." : editing ? "Spara" : "Skapa"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// --- Bekräftelsedialog för radering ---

interface ConfirmDeleteDialogProps {
  open: boolean
  onClose: () => void
  organization: Organization | null
  systemCount: number
  onConfirm: () => void
  isPending: boolean
}

function ConfirmDeleteDialog({
  open,
  onClose,
  organization,
  systemCount,
  onConfirm,
  isPending,
}: ConfirmDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Ta bort organisation</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {systemCount > 0 ? (
            <p className="text-sm text-destructive">
              Det finns {systemCount} system kopplade till{" "}
              <strong>{organization?.name}</strong>. Ta bort eller flytta dessa
              system innan organisationen kan raderas.
            </p>
          ) : (
            <p className="text-sm">
              Är du säker på att du vill ta bort{" "}
              <strong>{organization?.name}</strong>? Åtgärden kan inte ångras.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>
            Avbryt
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending || systemCount > 0}
          >
            {isPending ? "Tar bort..." : "Ta bort"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// --- Huvudsida ---

export default function OrganizationsPage() {
  const queryClient = useQueryClient()

  const { data: organizations = [], isLoading, isError } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  // Hämta alla system för att beräkna antal per organisation
  const { data: allSystems } = useQuery({
    queryKey: ["systems", { limit: 1000 }],
    queryFn: () => getSystems({ limit: 1000 }),
  })

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Organization | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Organization | null>(null)

  const deleteMutation = useMutation({
    mutationFn: () => deleteOrganization(deleteTarget!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] })
      toast.success("Organisationen togs bort.")
      setDeleteTarget(null)
    },
    onError: () => {
      toast.error("Kunde inte ta bort organisationen.")
      setDeleteTarget(null)
    },
  })

  function getSystemCount(orgId: string): number {
    if (!allSystems?.items) return 0
    return allSystems.items.filter((s) => s.organization_id === orgId).length
  }

  function handleEdit(org: Organization) {
    setEditing(org)
    setFormOpen(true)
  }

  function handleNewClick() {
    setEditing(null)
    setFormOpen(true)
  }

  function handleFormClose() {
    setFormOpen(false)
    setEditing(null)
  }

  function findParentName(parentId: string | null): string {
    if (!parentId) return "—"
    return organizations.find((o) => o.id === parentId)?.name ?? "—"
  }

  return (
    <div className="space-y-6">
      {/* Rubrik + knapp */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BuildingIcon className="size-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold tracking-tight">
            Organisationer
          </h1>
        </div>
        <Button onClick={handleNewClick}>
          <PlusIcon className="size-4 mr-1.5" />
          Ny organisation
        </Button>
      </div>

      {/* Laddning / fel */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">Laddar organisationer...</p>
      )}
      {isError && (
        <p className="text-sm text-destructive">
          Kunde inte hämta organisationer. Försök igen.
        </p>
      )}

      {/* Tabell */}
      {!isLoading && !isError && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Namn</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Org-nummer</TableHead>
                <TableHead>Moderorganisation</TableHead>
                <TableHead className="w-[100px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {organizations.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center text-muted-foreground py-8"
                  >
                    Inga organisationer hittades.
                  </TableCell>
                </TableRow>
              ) : (
                organizations.map((org) => (
                  <TableRow key={org.id}>
                    <TableCell className="font-medium">{org.name}</TableCell>
                    <TableCell>{ORG_TYPE_LABELS[org.org_type]}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {org.org_number ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {findParentName(org.parent_org_id)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 justify-end">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Redigera ${org.name}`}
                          onClick={() => handleEdit(org)}
                        >
                          <PencilIcon className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Ta bort ${org.name}`}
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteTarget(org)}
                        >
                          <Trash2Icon className="size-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Formulär-dialog */}
      {formOpen && (
        <OrgFormDialog
          open={formOpen}
          onClose={handleFormClose}
          organizations={organizations}
          editing={editing}
        />
      )}

      {/* Radera-dialog */}
      {deleteTarget && (
        <ConfirmDeleteDialog
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          organization={deleteTarget}
          systemCount={getSystemCount(deleteTarget.id)}
          onConfirm={() => deleteMutation.mutate()}
          isPending={deleteMutation.isPending}
        />
      )}
    </div>
  )
}
