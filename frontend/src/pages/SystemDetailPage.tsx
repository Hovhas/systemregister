import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, PencilIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { Breadcrumb } from "@/components/Breadcrumb"

import {
  getSystem,
  deleteSystem,
  getOrganizations,
} from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { categoryLabels, lifecycleLabels } from "@/lib/labels"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  OversiktTab,
  KlassningTab,
  AgareTab,
  IntegrationerTab,
  GdprTab,
  AvtalTab,
  ExtendedAttributesTab,
  AuditTimeline,
  ObjektTab,
  KomponenterTab,
  ModulerTab,
  InformationsmangderTab,
  GodkannandenTab,
} from "@/components/system-detail"

// --- Hjälp-hook ---

function useSystemDetail(id: string) {
  return useQuery({
    queryKey: ["system", id],
    queryFn: () => getSystem(id),
    enabled: !!id,
  })
}

// --- Huvudkomponent ---

export default function SystemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data: system, isLoading, isError, refetch } = useSystemDetail(id ?? "")

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name])
  )

  const deleteMutation = useMutation({
    mutationFn: () => deleteSystem(system!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["systems"] })
      toast.success("System borttaget")
      navigate("/systems")
    },
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="skeleton h-6 w-48" />
        <div className="flex gap-4">
          <div className="skeleton h-10 w-32" />
          <div className="flex flex-col gap-2 flex-1">
            <div className="skeleton h-8 w-64" />
            <div className="flex gap-2">
              <div className="skeleton h-6 w-24" />
              <div className="skeleton h-6 w-20" />
            </div>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="skeleton h-48 rounded-xl" />
          <div className="skeleton h-48 rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError || !system) {
    return (
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => navigate("/systems")}
        >
          <ArrowLeftIcon className="mr-1 size-4" />
          Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hämta system.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        items={[
          { label: "System", href: "/systems" },
          { label: system.name },
        ]}
      />

      {/* Sidhuvud */}
      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="mt-0.5 shrink-0 w-fit"
          onClick={() => navigate("/systems")}
        >
          <ArrowLeftIcon className="mr-1 size-4" />
          Tillbaka
        </Button>
        <div className="flex flex-col gap-2 flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{system.name}</h1>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{categoryLabels[system.system_category]}</Badge>
            <Badge variant="outline">{lifecycleLabels[system.lifecycle_status]}</Badge>
            {system.nis2_applicable && (
              <Badge variant="default">NIS2</Badge>
            )}
          </div>
          {system.description && (
            <p className="text-sm text-muted-foreground max-w-xl mt-1">{system.description}</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/systems/${system.id}/edit`)}
          >
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
        title="Ta bort system"
        description={`Är du säker på att du vill ta bort "${system.name}"? Alla kopplingar (klassningar, ägare, integrationer) raderas.`}
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />

      {/* Flikar */}
      <Tabs defaultValue="oversikt" className="mt-2">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="oversikt">Översikt</TabsTrigger>
          <TabsTrigger value="klassning">
            Klassning
            {system.classifications.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.classifications.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="agare">
            Ägare
            {system.owners.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.owners.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="integrationer">Integrationer</TabsTrigger>
          <TabsTrigger value="gdpr">GDPR</TabsTrigger>
          <TabsTrigger value="avtal">Avtal</TabsTrigger>
          <TabsTrigger value="objekt">Objekt</TabsTrigger>
          <TabsTrigger value="komponenter">
            Komponenter
            {(system.components?.length ?? 0) > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.components!.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="moduler">
            Moduler
            {(system.modules_used?.length ?? 0) > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.modules_used!.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="informationsmangder">
            Informationsmängder
            {(system.information_assets?.length ?? 0) > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">
                ({system.information_assets!.length})
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="godkannanden">Godkännanden</TabsTrigger>
          <TabsTrigger value="ovrigt">Övrig data</TabsTrigger>
          <TabsTrigger value="andringslogg">Ändringslogg</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-6">
          <OversiktTab system={system} />
        </TabsContent>

        <TabsContent value="klassning" className="mt-6">
          <KlassningTab classifications={system.classifications} systemId={system.id} />
        </TabsContent>

        <TabsContent value="agare" className="mt-6">
          <AgareTab owners={system.owners} orgNameMap={orgNameMap} systemId={system.id} />
        </TabsContent>

        <TabsContent value="integrationer" className="mt-6">
          <IntegrationerTab integrations={system.integrations ?? []} systemId={system.id} />
        </TabsContent>

        <TabsContent value="gdpr" className="mt-6">
          <GdprTab systemId={system.id} />
        </TabsContent>

        <TabsContent value="avtal" className="mt-6">
          <AvtalTab systemId={system.id} />
        </TabsContent>

        <TabsContent value="objekt" className="mt-6">
          <ObjektTab system={system} />
        </TabsContent>

        <TabsContent value="komponenter" className="mt-6">
          <KomponenterTab system={system} />
        </TabsContent>

        <TabsContent value="moduler" className="mt-6">
          <ModulerTab system={system} />
        </TabsContent>

        <TabsContent value="informationsmangder" className="mt-6">
          <InformationsmangderTab system={system} />
        </TabsContent>

        <TabsContent value="godkannanden" className="mt-6">
          <GodkannandenTab system={system} />
        </TabsContent>

        <TabsContent value="ovrigt" className="mt-6">
          <ExtendedAttributesTab attributes={system.extended_attributes} />
        </TabsContent>

        <TabsContent value="andringslogg" className="mt-6">
          <AuditTimeline systemId={system.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
