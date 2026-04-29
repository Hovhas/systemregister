import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ChevronRightIcon, ChevronDownIcon, PlusIcon, PencilIcon, TrashIcon } from "lucide-react"

import { getOrgUnitTree, getOrganizations, createOrgUnit, updateOrgUnit, deleteOrgUnit } from "@/lib/api"
import type { OrgUnitCreate, OrgUnitUpdate, OrgUnitTreeNode } from "@/types"
import { OrgUnitType } from "@/types"
import { orgUnitTypeLabels } from "@/lib/labels"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { ConfirmDialog } from "@/components/ConfirmDialog"

const emptyForm: OrgUnitCreate = {
  organization_id: "",
  name: "",
  unit_type: OrgUnitType.ENHET,
  manager_name: null,
  cost_center: null,
  parent_unit_id: null,
}

interface TreeNodeProps {
  node: OrgUnitTreeNode
  depth: number
  onEdit: (node: OrgUnitTreeNode) => void
  onDelete: (node: OrgUnitTreeNode) => void
  onAddChild: (parentId: string) => void
}

function TreeNode({ node, depth, onEdit, onDelete, onAddChild }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children.length > 0

  return (
    <li>
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted/50 group"
        style={{ paddingLeft: `${(depth + 1) * 12}px` }}
      >
        <button
          type="button"
          className="flex size-5 items-center justify-center shrink-0 text-muted-foreground"
          onClick={() => setExpanded((v) => !v)}
          aria-label={expanded ? "Dölj underelement" : "Visa underelement"}
          disabled={!hasChildren}
        >
          {hasChildren ? (
            expanded ? <ChevronDownIcon className="size-4" /> : <ChevronRightIcon className="size-4" />
          ) : (
            <span className="size-4" />
          )}
        </button>

        <span className="font-medium text-sm flex-1">{node.name}</span>
        <Badge variant="outline" className="text-xs">{orgUnitTypeLabels[node.unit_type]}</Badge>
        {node.manager_name && <span className="text-xs text-muted-foreground hidden sm:inline">{node.manager_name}</span>}

        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => onAddChild(node.id)} aria-label={`Lägg till undernod under ${node.name}`}>
            <PlusIcon className="size-3" />
          </Button>
          <Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => onEdit(node)} aria-label={`Redigera ${node.name}`}>
            <PencilIcon className="size-3" />
          </Button>
          <Button variant="ghost" size="sm" className="h-6 px-1 text-destructive hover:text-destructive" onClick={() => onDelete(node)} aria-label={`Ta bort ${node.name}`}>
            <TrashIcon className="size-3" />
          </Button>
        </div>
      </div>

      {hasChildren && expanded && (
        <ul>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} onEdit={onEdit} onDelete={onDelete} onAddChild={onAddChild} />
          ))}
        </ul>
      )}
    </li>
  )
}

export default function OrgUnitsPage() {
  const queryClient = useQueryClient()
  const [organization, setOrganization] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<OrgUnitTreeNode | null>(null)
  const [form, setForm] = useState<OrgUnitCreate>({ ...emptyForm })
  const [editForm, setEditForm] = useState<{ name: string; unit_type: OrgUnitType; manager_name: string; cost_center: string }>({
    name: "", unit_type: OrgUnitType.ENHET, manager_name: "", cost_center: "",
  })
  const [editId, setEditId] = useState<string | null>(null)

  const { data: orgs } = useQuery({ queryKey: ["organizations"], queryFn: getOrganizations })
  const orgNameMap = Object.fromEntries((orgs ?? []).map((o) => [o.id, o.name]))

  const { data: tree, isLoading, isError, refetch } = useQuery({
    queryKey: ["org-unit-tree", organization],
    queryFn: () => (organization ? getOrgUnitTree(organization) : Promise.resolve([])),
    enabled: !!organization,
  })

  const createMut = useMutation({
    mutationFn: (data: OrgUnitCreate) => createOrgUnit(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-unit-tree"] })
      setCreateOpen(false)
      setForm({ ...emptyForm, organization_id: organization })
      toast.success("Organisationsenhet skapad")
    },
    onError: () => toast.error("Kunde inte skapa organisationsenhet"),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: OrgUnitUpdate }) => updateOrgUnit(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-unit-tree"] })
      setEditOpen(false)
      setEditId(null)
      toast.success("Organisationsenhet uppdaterad")
    },
    onError: () => toast.error("Kunde inte uppdatera organisationsenhet"),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteOrgUnit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-unit-tree"] })
      setDeleteTarget(null)
      toast.success("Organisationsenhet borttagen")
    },
    onError: () => toast.error("Kunde inte ta bort organisationsenhet"),
  })

  function openCreate(parentId?: string) {
    setForm({ ...emptyForm, organization_id: organization, parent_unit_id: parentId ?? null })
    setCreateOpen(true)
  }

  function openEdit(node: OrgUnitTreeNode) {
    setEditId(node.id)
    setEditForm({
      name: node.name,
      unit_type: node.unit_type,
      manager_name: node.manager_name ?? "",
      cost_center: node.cost_center ?? "",
    })
    setEditOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Organisationsenheter</h1>
          <p className="text-sm text-muted-foreground mt-1">Hierarkisk vy av organisationens enheter</p>
        </div>
        <Button onClick={() => openCreate()} disabled={!organization} aria-label="Skapa ny organisationsenhet">
          <PlusIcon className="mr-1 size-4" />
          Ny enhet
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select value={organization || undefined} onValueChange={(val) => setOrganization(val ?? "")}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Välj organisation">
              {organization ? orgNameMap[organization] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {(orgs ?? []).map((org) => (
              <SelectItem key={org.id} value={org.id}>{org.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!organization ? (
        <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground text-sm">
          Välj en organisation för att se dess enheter
        </div>
      ) : isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta organisationsenheter.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Försök igen</Button>
        </div>
      ) : isLoading ? (
        <div className="rounded-xl border bg-card p-4 flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-8 rounded-lg" style={{ marginLeft: `${(i % 3) * 12}px` }} />
          ))}
        </div>
      ) : (tree ?? []).length === 0 ? (
        <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground text-sm">
          Inga enheter registrerade för denna organisation.{" "}
          <button type="button" className="underline hover:text-foreground" onClick={() => openCreate()}>Skapa den första.</button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden py-2">
          <ul>
            {(tree ?? []).map((node) => (
              <TreeNode
                key={node.id}
                node={node}
                depth={0}
                onEdit={openEdit}
                onDelete={setDeleteTarget}
                onAddChild={(parentId) => openCreate(parentId)}
              />
            ))}
          </ul>
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort organisationsenhet"
        description={deleteTarget ? `Är du säker på att du vill ta bort "${deleteTarget.name}"? Undernoder kan påverkas.` : ""}
        onConfirm={() => { if (deleteTarget) deleteMut.mutate(deleteTarget.id) }}
        loading={deleteMut.isPending}
      />

      <Dialog open={createOpen} onOpenChange={(open) => { if (!open) setCreateOpen(false) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ny organisationsenhet</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(form) }} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required placeholder="Namn" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Typ *</label>
              <Select value={form.unit_type} onValueChange={(val) => setForm({ ...form, unit_type: val as OrgUnitType })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.values(OrgUnitType).map((t) => (
                    <SelectItem key={t} value={t}>{orgUnitTypeLabels[t]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Chef</label>
              <Input placeholder="Chefens namn" value={form.manager_name ?? ""} onChange={(e) => setForm({ ...form, manager_name: e.target.value || null })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Kostnadsställe</label>
              <Input placeholder="Kostnadsställe" value={form.cost_center ?? ""} onChange={(e) => setForm({ ...form, cost_center: e.target.value || null })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Avbryt</Button>
              <Button type="submit" disabled={createMut.isPending || !form.name}>
                {createMut.isPending ? "Skapar..." : "Skapa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={editOpen} onOpenChange={(open) => { if (!open) { setEditOpen(false); setEditId(null) } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redigera organisationsenhet</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (!editId) return
              updateMut.mutate({
                id: editId,
                data: {
                  name: editForm.name,
                  unit_type: editForm.unit_type,
                  manager_name: editForm.manager_name || null,
                  cost_center: editForm.cost_center || null,
                },
              })
            }}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Namn *</label>
              <Input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Typ *</label>
              <Select value={editForm.unit_type} onValueChange={(val) => setEditForm({ ...editForm, unit_type: val as OrgUnitType })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.values(OrgUnitType).map((t) => (
                    <SelectItem key={t} value={t}>{orgUnitTypeLabels[t]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Chef</label>
              <Input value={editForm.manager_name} onChange={(e) => setEditForm({ ...editForm, manager_name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Kostnadsställe</label>
              <Input value={editForm.cost_center} onChange={(e) => setEditForm({ ...editForm, cost_center: e.target.value })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setEditOpen(false); setEditId(null) }}>Avbryt</Button>
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
