import { useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { PlusIcon, TrashIcon } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { getIntegrations, getSystems, deleteIntegration } from "@/lib/api"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import IntegrationDialog from "@/components/IntegrationDialog"
import type { Integration } from "@/types"

// ---------- Typer ----------

type Criticality = "låg" | "medel" | "hög" | "kritisk"
type IntegrationType =
  | "api"
  | "filöverföring"
  | "databasreplikering"
  | "event"
  | "manuell"

interface SystemItem {
  id: string
  name: string
  criticality: Criticality
}

// ---------- Hjälpfunktioner ----------

const criticalityLabel: Record<Criticality, string> = {
  låg: "Låg",
  medel: "Medium",
  hög: "Hög",
  kritisk: "Kritisk",
}

const criticalityVariant: Record<
  Criticality,
  "default" | "secondary" | "destructive" | "outline"
> = {
  låg: "secondary",
  medel: "outline",
  hög: "default",
  kritisk: "destructive",
}

const integrationTypeLabel: Record<string, string> = {
  api: "API",
  filöverföring: "Filöverföring",
  databasreplikering: "Databasreplikering",
  event: "Event",
  manuell: "Manuell",
}

// Färg per kritikalitet — för SVG-noder
const criticalityColor: Record<Criticality, string> = {
  låg: "#86efac",
  medel: "#fcd34d",
  hög: "#fb923c",
  kritisk: "#f87171",
}

const DEFAULT_NODE_COLOR = "#94a3b8"

// ---------- Graf-komponent ----------

interface GraphNode {
  id: string
  label: string
  criticality: Criticality | null
  x: number
  y: number
}

interface GraphEdge {
  source: string
  target: string
  type: IntegrationType
  criticality: Criticality | null
}

interface DependencyGraphProps {
  integrations: Integration[]
  systems: Map<string, SystemItem>
}

function DependencyGraph({ integrations, systems }: DependencyGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{
    x: number
    y: number
    text: string
  } | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null)

  // Bygg unika nod-id:n från integrationer
  const nodeIds = Array.from(
    new Set(
      integrations.flatMap((i) => [i.source_system_id, i.target_system_id])
    )
  )

  const WIDTH = 800
  const HEIGHT = 560
  const CX = WIDTH / 2
  const CY = HEIGHT / 2
  const RADIUS = Math.min(CX, CY) - 80
  const NODE_R = 28

  // Placera noder i cirkel-layout
  const nodes: GraphNode[] = nodeIds.map((id, idx) => {
    const angle = (2 * Math.PI * idx) / nodeIds.length - Math.PI / 2
    const sys = systems.get(id)
    return {
      id,
      label: sys?.name ?? id.slice(0, 8),
      criticality: (sys?.criticality as Criticality) ?? null,
      x: CX + RADIUS * Math.cos(angle),
      y: CY + RADIUS * Math.sin(angle),
    }
  })

  const nodeMap = new Map(nodes.map((n) => [n.id, n]))

  const edges: GraphEdge[] = integrations.map((i) => ({
    source: i.source_system_id,
    target: i.target_system_id,
    type: i.integration_type as IntegrationType,
    criticality: i.criticality as Criticality | null,
  }))

  // Beräkna offset-vektor för pil (undvik överlapp med nod-cirkeln)
  function arrowPoints(
    sx: number,
    sy: number,
    tx: number,
    ty: number
  ): { x1: number; y1: number; x2: number; y2: number } {
    const dx = tx - sx
    const dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy) || 1
    const ux = dx / dist
    const uy = dy / dist
    return {
      x1: sx + ux * NODE_R,
      y1: sy + uy * NODE_R,
      x2: tx - ux * (NODE_R + 6),
      y2: ty - uy * (NODE_R + 6),
    }
  }

  if (nodeIds.length === 0) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        Inga integrationer att visa.
      </p>
    )
  }

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full mx-auto"
        style={{ minHeight: 400, maxWidth: "100%" }}
        role="img"
        aria-label="Beroendevisualisering mellan system"
        onMouseLeave={() => {
          setTooltip(null)
          setHoveredEdge(null)
        }}
      >
        {/* Pil-markör per kritikalitet */}
        <defs>
          {(["låg", "medel", "hög", "kritisk", "DEFAULT"] as const).map(
            (k) => {
              const color =
                k === "DEFAULT"
                  ? "#94a3b8"
                  : criticalityColor[k as Criticality]
              return (
                <marker
                  key={k}
                  id={`arrow-${k}`}
                  viewBox="0 0 10 10"
                  refX="10"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
                </marker>
              )
            }
          )}
        </defs>

        {/* Kanter */}
        {edges.map((edge, idx) => {
          const src = nodeMap.get(edge.source)
          const tgt = nodeMap.get(edge.target)
          if (!src || !tgt) return null
          const { x1, y1, x2, y2 } = arrowPoints(src.x, src.y, tgt.x, tgt.y)
          const edgeKey = `${edge.source}-${edge.target}-${idx}`
          const markerKey = edge.criticality ?? "DEFAULT"
          const strokeColor = edge.criticality
            ? criticalityColor[edge.criticality]
            : DEFAULT_NODE_COLOR
          const isHovered = hoveredEdge === edgeKey
          const mx = (x1 + x2) / 2
          const my = (y1 + y2) / 2

          return (
            <g key={edgeKey}>
              {/* Bred osynlig yta för hover */}
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="transparent"
                strokeWidth={14}
                style={{ cursor: "pointer" }}
                onMouseEnter={(e) => {
                  setHoveredEdge(edgeKey)
                  const rect = svgRef.current?.getBoundingClientRect()
                  if (rect) {
                    setTooltip({
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top - 36,
                      text: integrationTypeLabel[edge.type] ?? edge.type,
                    })
                  }
                }}
                onMouseLeave={() => {
                  setHoveredEdge(null)
                  setTooltip(null)
                }}
              />
              {/* Synlig kant */}
              <line
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={strokeColor}
                strokeWidth={isHovered ? 3 : 1.5}
                strokeOpacity={isHovered ? 1 : 0.65}
                markerEnd={`url(#arrow-${markerKey})`}
                style={{ pointerEvents: "none", transition: "stroke-width 0.1s" }}
              />
              {/* Typ-label på kanten */}
              {isHovered && (
                <text
                  x={mx}
                  y={my - 6}
                  textAnchor="middle"
                  fontSize={11}
                  fill={strokeColor}
                  className="font-medium select-none"
                  style={{ pointerEvents: "none" }}
                >
                  {integrationTypeLabel[edge.type] ?? edge.type}
                </text>
              )}
            </g>
          )
        })}

        {/* Noder */}
        {nodes.map((node) => {
          const color = node.criticality
            ? criticalityColor[node.criticality]
            : DEFAULT_NODE_COLOR
          const words = node.label.split(/\s+/)
          return (
            <g
              key={node.id}
              style={{ cursor: "default" }}
              onMouseEnter={(e) => {
                const rect = svgRef.current?.getBoundingClientRect()
                if (rect) {
                  const sys = systems.get(node.id)
                  const crit = sys
                    ? criticalityLabel[sys.criticality as Criticality]
                    : "Okänd"
                  setTooltip({
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top - 44,
                    text: `${node.label} — ${crit}`,
                  })
                }
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={NODE_R}
                fill={color}
                fillOpacity={0.85}
                stroke={color}
                strokeWidth={2}
              />
              {words.map((word, wi) => (
                <text
                  key={wi}
                  x={node.x}
                  y={node.y + wi * 13 - ((words.length - 1) * 13) / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={10}
                  fontWeight="600"
                  fill="#1e293b"
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {word.length > 10 ? word.slice(0, 9) + "…" : word}
                </text>
              ))}
            </g>
          )
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-md bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}

      {/* Förklaring */}
      <div className="mt-4 flex flex-wrap justify-center gap-3 text-xs text-muted-foreground">
        {(["låg", "medel", "hög", "kritisk"] as Criticality[]).map((c) => (
          <span key={c} className="flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-full border"
              style={{ backgroundColor: criticalityColor[c] }}
            />
            {criticalityLabel[c]}
          </span>
        ))}
      </div>
    </div>
  )
}

// ---------- Tabell-komponent ----------

interface DependencyTableProps {
  integrations: Integration[]
  systems: Map<string, SystemItem>
  onDelete: (integration: Integration) => void
}

function DependencyTable({ integrations, systems, onDelete }: DependencyTableProps) {
  if (integrations.length === 0) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        Inga integrationer registrerade.
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Källsystem</TableHead>
          <TableHead>Målsystem</TableHead>
          <TableHead>Typ</TableHead>
          <TableHead>Kritikalitet</TableHead>
          <TableHead>Frekvens</TableHead>
          <TableHead>Extern part</TableHead>
          <TableHead>Beskrivning</TableHead>
          <TableHead className="w-12"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {integrations.map((i) => {
          const srcName = systems.get(i.source_system_id)?.name ?? i.source_system_id.slice(0, 8)
          const tgtName = systems.get(i.target_system_id)?.name ?? i.target_system_id.slice(0, 8)
          const crit = i.criticality as Criticality | null
          return (
            <TableRow key={i.id}>
              <TableCell className="font-medium">{srcName}</TableCell>
              <TableCell>{tgtName}</TableCell>
              <TableCell>
                <Badge variant="outline">
                  {integrationTypeLabel[i.integration_type] ?? i.integration_type}
                </Badge>
              </TableCell>
              <TableCell>
                {crit ? (
                  <Badge variant={criticalityVariant[crit]}>
                    {criticalityLabel[crit]}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                {i.frequency ?? <span className="text-muted-foreground">—</span>}
              </TableCell>
              <TableCell>
                {i.is_external && i.external_party ? (
                  <Badge variant="secondary">{i.external_party}</Badge>
                ) : i.is_external ? (
                  <Badge variant="secondary">Extern</Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell
                className="max-w-xs truncate text-muted-foreground"
                title={i.description ?? undefined}
              >
                {i.description ?? "—"}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Ta bort integration"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => onDelete(i)}
                >
                  <TrashIcon className="size-4" />
                </Button>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

// ---------- Sida ----------

export default function DependenciesPage() {
  const queryClient = useQueryClient()
  const [newDialogOpen, setNewDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Integration | null>(null)

  const { data: integrationsData = [], isLoading: isLoadingIntegrations, error: integrationsError } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => getIntegrations(),
  })

  // TODO: limit: 500 är en hårdkodad gräns — behöver backend-stöd för paginering
  // eller ett dedikerat endpoint för att hämta alla system-namn/id.
  const { data: systemsData, isLoading: isLoadingSystems } = useQuery({
    queryKey: ["systems", { limit: 500 }],
    queryFn: () => getSystems({ limit: 500 }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] })
      toast.success("Integration borttagen")
      setDeleteTarget(null)
    },
  })

  const loading = isLoadingIntegrations || isLoadingSystems
  const error = integrationsError ? "Kunde inte hämta data. Kontrollera att API:et är tillgängligt." : null

  const systemsList = systemsData?.items ?? []
  const systems = new Map(systemsList.map((s) => [s.id, s as unknown as SystemItem]))

  // Statistik
  const totalSystems = new Set(
    integrationsData.flatMap((i) => [i.source_system_id, i.target_system_id])
  ).size
  const criticalCount = integrationsData.filter(
    (i) => i.criticality === "kritisk"
  ).length
  const externalCount = integrationsData.filter((i) => i.is_external).length

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Beroendekarta</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Visualisering av systemintegrationer och beroenden
          </p>
        </div>
        <Button onClick={() => setNewDialogOpen(true)}>
          <PlusIcon className="mr-2 size-4" />
          Ny integration
        </Button>
      </div>

      {/* KPI-kort */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Integrationer
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {loading ? "—" : integrationsData.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Berörda system
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{loading ? "—" : totalSystems}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Kritiska / Externa
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {loading ? "—" : (
                <span>
                  <span className="text-destructive">{criticalCount}</span>
                  <span className="mx-1 text-muted-foreground">/</span>
                  {externalCount}
                </span>
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Felmeddelande */}
      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Huvud-innehåll */}
      <Card>
        <CardContent className={cn("pt-6", loading && "opacity-50")}>
          {loading ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Laddar integrationer…
            </p>
          ) : (
            <Tabs defaultValue="graf">
              <TabsList>
                <TabsTrigger value="graf">Nätverksgraf</TabsTrigger>
                <TabsTrigger value="tabell">Tabell</TabsTrigger>
              </TabsList>

              <TabsContent value="graf" className="mt-4">
                <DependencyGraph integrations={integrationsData} systems={systems} />
              </TabsContent>

              <TabsContent value="tabell" className="mt-4">
                <DependencyTable
                  integrations={integrationsData}
                  systems={systems}
                  onDelete={setDeleteTarget}
                />
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>

      {/* Ny integration-dialog */}
      <IntegrationDialog
        open={newDialogOpen}
        onOpenChange={setNewDialogOpen}
      />

      {/* Bekräftelsedialog för borttagning */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Ta bort integration"
        description="Är du säker på att du vill ta bort denna integration? Åtgärden kan inte ångras."
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
