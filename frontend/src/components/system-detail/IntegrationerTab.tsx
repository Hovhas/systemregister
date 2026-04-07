import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { getSystems, deleteIntegration } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import IntegrationDialog from "@/components/IntegrationDialog"
import type { Integration } from "@/types"
import { integrationTypeLabels } from "@/lib/labels"
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

export function IntegrationerTab({
  integrations,
  systemId,
}: {
  integrations: Integration[]
  systemId: string
}) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Integration | null>(null)

  const { data: allSystemsData } = useQuery({
    queryKey: ["systems", { limit: 200 }],
    queryFn: () => getSystems({ limit: 200 }),
  })
  const allSystems = allSystemsData?.items ?? []

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", systemId] })
      toast.success("Integration borttagen")
      setDeleteTarget(null)
    },
  })

  const systemNameMap = Object.fromEntries(allSystems.map((s) => [s.id, s.name]))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <PlusIcon className="mr-1 size-4" /> Ny integration
        </Button>
      </div>

      {integrations.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga integrationer registrerade
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Riktning</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Motpart</TableHead>
                <TableHead>Frekvens</TableHead>
                <TableHead>Beskrivning</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {integrations.map((intg) => {
                const isSource = intg.source_system_id === systemId
                const counterpartId = isSource ? intg.target_system_id : intg.source_system_id
                return (
                  <TableRow key={intg.id}>
                    <TableCell>
                      <Badge variant={isSource ? "default" : "secondary"}>
                        {isSource ? "Ut" : "In"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {integrationTypeLabels[intg.integration_type] ?? intg.integration_type}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {systemNameMap[counterpartId] ?? counterpartId}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {intg.frequency ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {intg.description ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Ta bort integration"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => setDeleteTarget(intg)}
                      >
                        <TrashIcon className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <IntegrationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        systemId={systemId}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort integration"
        description="Är du säker på att du vill ta bort denna integration?"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
