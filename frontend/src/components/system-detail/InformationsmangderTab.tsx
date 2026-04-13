import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { LinkIcon, XIcon } from "lucide-react"

import type { SystemDetail, InformationAsset } from "@/types"
import { getInformationAssets, linkAssetToSystem, unlinkAssetFromSystem } from "@/lib/api"
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

export function InformationsmangderTab({ system }: { system: SystemDetail }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [linkOpen, setLinkOpen] = useState(false)
  const [unlinkTarget, setUnlinkTarget] = useState<InformationAsset | null>(null)

  const assets = system.information_assets ?? []

  const unlinkMut = useMutation({
    mutationFn: (assetId: string) => unlinkAssetFromSystem(assetId, system.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system", system.id] })
      setUnlinkTarget(null)
      toast.success("Informationsmangd avlankad")
    },
    onError: () => toast.error("Kunde inte avlanka informationsmangd"),
  })

  async function handleLink(ids: string[]) {
    for (const id of ids) {
      await linkAssetToSystem(id, system.id)
    }
    queryClient.invalidateQueries({ queryKey: ["system", system.id] })
    toast.success(`${ids.length} informationsmangd(er) lankade`)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setLinkOpen(true)}>
          <LinkIcon className="mr-1 size-4" />
          Lanka informationsmangd
        </Button>
      </div>

      {assets.length === 0 ? (
        <p className="text-sm text-muted-foreground py-4">
          Inga informationsmangder lankade till detta system.
        </p>
      ) : (
        <div className="rounded-xl ring-1 ring-foreground/10">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Namn</TableHead>
                <TableHead>Informationsagare</TableHead>
                <TableHead className="text-center w-12">K</TableHead>
                <TableHead className="text-center w-12">R</TableHead>
                <TableHead className="text-center w-12">T</TableHead>
                <TableHead>Personuppgifter</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets.map((asset) => (
                <TableRow
                  key={asset.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(`/information-assets/${asset.id}`)}
                >
                  <TableCell className="font-medium">{asset.name}</TableCell>
                  <TableCell>{asset.information_owner ?? "\u2014"}</TableCell>
                  <TableCell className="text-center">{asset.confidentiality ?? "\u2014"}</TableCell>
                  <TableCell className="text-center">{asset.integrity ?? "\u2014"}</TableCell>
                  <TableCell className="text-center">{asset.availability ?? "\u2014"}</TableCell>
                  <TableCell>
                    {asset.contains_personal_data ? (
                      <Badge variant="default">Ja</Badge>
                    ) : (
                      <Badge variant="outline">Nej</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      aria-label={`Avlanka ${asset.name}`}
                      onClick={(e) => { e.stopPropagation(); setUnlinkTarget(asset) }}
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
        title="Lanka informationsmangd"
        description="Valj informationsmangder att koppla till systemet"
        queryKey={["information-assets", "link-dialog", system.organization_id]}
        queryFn={() => getInformationAssets({ organization_id: system.organization_id, limit: 200 })}
        renderOption={(item) => (
          <div className="flex items-center gap-2">
            <span className="font-medium">{item.name}</span>
            {item.contains_personal_data && <Badge variant="default" className="text-[10px] px-1.5 py-0">PU</Badge>}
          </div>
        )}
        excludeIds={assets.map((a) => a.id)}
        onSelect={handleLink}
        submitLabel="Lanka"
      />

      <ConfirmDialog
        open={unlinkTarget !== null}
        onOpenChange={(open) => { if (!open) setUnlinkTarget(null) }}
        title="Avlanka informationsmangd"
        description={`Ar du saker pa att du vill avlanka "${unlinkTarget?.name ?? ""}" fran systemet?`}
        onConfirm={() => unlinkTarget && unlinkMut.mutate(unlinkTarget.id)}
        loading={unlinkMut.isPending}
        confirmLabel="Avlanka"
      />
    </div>
  )
}
