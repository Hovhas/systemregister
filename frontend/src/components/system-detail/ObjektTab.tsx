import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { LinkIcon, XIcon, ExternalLinkIcon } from "lucide-react"

import type { SystemDetail } from "@/types"
import { updateSystem, getObjekt } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { EntityLinkDialog } from "@/components/shared/EntityLinkDialog"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { InfoRow } from "./helpers"

export function ObjektTab({ system }: { system: SystemDetail }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [linkOpen, setLinkOpen] = useState(false)

  const objekt = system.objekt

  const unlinkMutation = useMutation({
    mutationFn: () => updateSystem(system.id, { objekt_id: null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      toast.success("Objekt bortkopplat")
    },
    onError: () => toast.error("Kunde inte koppla bort objekt"),
  })

  const linkMutation = useMutation({
    mutationFn: (objektId: string) => updateSystem(system.id, { objekt_id: objektId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      toast.success("Objekt kopplat")
    },
    onError: () => toast.error("Kunde inte koppla objekt"),
  })

  if (!objekt) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <p className="text-sm text-muted-foreground">
          Systemet tillhor inget objekt.
        </p>
        <Button size="sm" onClick={() => setLinkOpen(true)}>
          <LinkIcon className="mr-1 size-4" />
          Valj objekt
        </Button>

        <EntityLinkDialog
          open={linkOpen}
          onOpenChange={setLinkOpen}
          title="Valj objekt"
          description="Koppla systemet till ett forvaltningsobjekt"
          queryKey={["objekt", "link-dialog", system.organization_id]}
          queryFn={() => getObjekt({ organization_id: system.organization_id, limit: 200 })}
          renderOption={(item) => (
            <div>
              <span className="font-medium">{item.name}</span>
              {item.object_owner && (
                <span className="ml-2 text-xs text-muted-foreground">({item.object_owner})</span>
              )}
            </div>
          )}
          onSelect={async (ids) => {
            if (ids.length > 0) {
              await linkMutation.mutateAsync(ids[0])
            }
          }}
          submitLabel="Koppla"
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLinkOpen(true)}
        >
          <LinkIcon className="mr-1 size-4" />
          Andra objekt
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => unlinkMutation.mutate()}
          disabled={unlinkMutation.isPending}
        >
          <XIcon className="mr-1 size-4" />
          Koppla bort
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {objekt.name}
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => navigate(`/objekt/${objekt.id}`)}
              aria-label="Ga till objektsida"
            >
              <ExternalLinkIcon className="size-3.5" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Beskrivning" value={objekt.description} />
          <InfoRow label="Objektagare" value={objekt.object_owner} />
          <InfoRow label="Objektledare" value={objekt.object_leader} />
          <InfoRow label="Skapad" value={formatDate(objekt.created_at)} />
          <InfoRow label="Uppdaterad" value={formatDate(objekt.updated_at)} />
        </CardContent>
      </Card>

      <EntityLinkDialog
        open={linkOpen}
        onOpenChange={setLinkOpen}
        title="Valj objekt"
        description="Byt forvaltningsobjekt for systemet"
        queryKey={["objekt", "link-dialog", system.organization_id]}
        queryFn={() => getObjekt({ organization_id: system.organization_id, limit: 200 })}
        renderOption={(item) => (
          <div>
            <span className="font-medium">{item.name}</span>
            {item.object_owner && (
              <span className="ml-2 text-xs text-muted-foreground">({item.object_owner})</span>
            )}
          </div>
        )}
        excludeIds={objekt ? [objekt.id] : []}
        onSelect={async (ids) => {
          if (ids.length > 0) {
            await linkMutation.mutateAsync(ids[0])
          }
        }}
        submitLabel="Koppla"
      />
    </div>
  )
}
