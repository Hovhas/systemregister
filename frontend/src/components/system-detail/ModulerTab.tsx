import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { LinkIcon, XIcon } from "lucide-react"

import type { SystemDetail, Module } from "@/types"
import { AIRiskClass } from "@/types"
import { getModules, linkModuleToSystem, unlinkModuleFromSystem } from "@/lib/api"
import { lifecycleLabels, aiRiskClassLabels, aiRiskBadgeClass } from "@/lib/labels"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function ModulerTab({ system }: { system: SystemDetail }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [linkOpen, setLinkOpen] = useState(false)
  const [unlinkTarget, setUnlinkTarget] = useState<Module | null>(null)

  const modules = system.modules_used ?? []

  const unlinkMut = useMutation({
    mutationFn: (moduleId: string) => unlinkModuleFromSystem(moduleId, system.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      setUnlinkTarget(null)
      toast.success("Modul avlankad")
    },
    onError: () => toast.error("Kunde inte avlanka modul"),
  })

  async function handleLink(ids: string[]) {
    for (const id of ids) {
      await linkModuleToSystem(id, system.id)
    }
    queryClient.invalidateQueries({ queryKey: ["system", system.id] })
    toast.success(`${ids.length} modul(er) lankade`)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setLinkOpen(true)}>
          <LinkIcon className="mr-1 size-4" />
          Lanka modul
        </Button>
      </div>

      {modules.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga moduler lankade till detta system.
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Namn</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>AI</TableHead>
                <TableHead>AI-riskklass</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {modules.map((mod) => (
                <TableRow
                  key={mod.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(`/modules/${mod.id}`)}
                >
                  <TableCell className="font-medium">{mod.name}</TableCell>
                  <TableCell>
                    {mod.lifecycle_status
                      ? lifecycleLabels[mod.lifecycle_status] ?? mod.lifecycle_status
                      : "\u2014"}
                  </TableCell>
                  <TableCell>
                    {mod.uses_ai ? (
                      <Badge variant="default">Ja</Badge>
                    ) : (
                      <Badge variant="outline">Nej</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {mod.ai_risk_class ? (
                      <span className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${aiRiskBadgeClass[mod.ai_risk_class as AIRiskClass] ?? ""}`}>
                        {aiRiskClassLabels[mod.ai_risk_class as AIRiskClass] ?? mod.ai_risk_class}
                      </span>
                    ) : (
                      "\u2014"
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      aria-label={`Avlanka ${mod.name}`}
                      onClick={(e) => { e.stopPropagation(); setUnlinkTarget(mod) }}
                    >
                      <XIcon className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <EntityLinkDialog
        open={linkOpen}
        onOpenChange={setLinkOpen}
        title="Lanka modul"
        description="Valj moduler att koppla till systemet"
        queryKey={["modules", "link-dialog", system.organization_id]}
        queryFn={() => getModules({ organization_id: system.organization_id, limit: 200 })}
        renderOption={(item) => (
          <div className="flex items-center gap-2">
            <span className="font-medium">{item.name}</span>
            {item.uses_ai && <Badge variant="default" className="text-[10px] px-1.5 py-0">AI</Badge>}
          </div>
        )}
        excludeIds={modules.map((m) => m.id)}
        onSelect={handleLink}
        submitLabel="Lanka"
      />

      <ConfirmDialog
        open={unlinkTarget !== null}
        onOpenChange={(open) => { if (!open) setUnlinkTarget(null) }}
        title="Avlanka modul"
        description={`Ar du saker pa att du vill avlanka "${unlinkTarget?.name ?? ""}" fran systemet?`}
        onConfirm={() => unlinkTarget && unlinkMut.mutate(unlinkTarget.id)}
        loading={unlinkMut.isPending}
        confirmLabel="Avlanka"
      />
    </div>
  )
}
