import { useState, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  DownloadIcon,
  ClipboardIcon,
  Loader2Icon,
  NetworkIcon,
} from "lucide-react"

import {
  getMermaidDiagram,
  getOrganizations,
  archimateExportUrl,
  twoseightPackageUrl,
} from "@/lib/api"
import { getProcesses, getValueStreams, getSystems } from "@/lib/api"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type DiagramType =
  | "capability-map"
  | "system-landscape"
  | "process-flow"
  | "value-stream"
  | "system-context"

const DIAGRAM_LABELS: Record<DiagramType, string> = {
  "capability-map": "Förmågekarta",
  "system-landscape": "Systemlandskap",
  "process-flow": "Process-flöde",
  "value-stream": "Värdeström",
  "system-context": "System-context",
}

function buildDiagramPath(
  type: DiagramType,
  orgId: string,
  subId: string,
): string | null {
  if (type === "capability-map") {
    if (!orgId) return null
    return `/diagrams/capability-map.mmd?organization_id=${orgId}`
  }
  if (type === "system-landscape") {
    if (!orgId) return null
    return `/diagrams/system-landscape.mmd?organization_id=${orgId}`
  }
  if (type === "process-flow") {
    if (!subId) return null
    return `/diagrams/process-flow/${subId}.mmd`
  }
  if (type === "value-stream") {
    if (!subId) return null
    return `/diagrams/value-stream/${subId}.mmd`
  }
  if (type === "system-context") {
    if (!subId) return null
    return `/diagrams/context/${subId}.mmd`
  }
  return null
}

export default function DiagramsPage() {
  const [diagramType, setDiagramType] = useState<DiagramType>("capability-map")
  const [orgId, setOrgId] = useState("")
  const [subId, setSubId] = useState("")
  const [mermaidText, setMermaidText] = useState<string | null>(null)
  const [svg, setSvg] = useState<string | null>(null)
  const mermaidReady = useRef(false)

  useEffect(() => {
    import("mermaid").then((m) => {
      m.default.initialize({ startOnLoad: false, theme: "default" })
      mermaidReady.current = true
    })
  }, [])

  // Sub-id dropdowns
  const needsProcess = diagramType === "process-flow"
  const needsValueStream = diagramType === "value-stream"
  const needsSystem = diagramType === "system-context"
  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const { data: processes } = useQuery({
    queryKey: ["processes", "diagram"],
    queryFn: () => getProcesses({ limit: 200 }),
    enabled: needsProcess,
  })

  const { data: valueStreams } = useQuery({
    queryKey: ["value-streams", "diagram"],
    queryFn: () => getValueStreams({ limit: 200 }),
    enabled: needsValueStream,
  })

  const { data: systems } = useQuery({
    queryKey: ["systems", "diagram"],
    queryFn: () => getSystems({ limit: 200 }),
    enabled: needsSystem,
  })

  const path = buildDiagramPath(diagramType, orgId, subId)

  const { isFetching, isError, refetch } = useQuery({
    queryKey: ["diagram", path],
    queryFn: async () => {
      const text = await getMermaidDiagram(path!)
      setMermaidText(text)
      return text
    },
    enabled: !!path,
    retry: false,
  })

  useEffect(() => {
    if (!mermaidText) {
      setSvg(null)
      return
    }
    let cancelled = false
    import("mermaid").then((m) => {
      m.default
        .render("mermaid-preview-" + Date.now(), mermaidText)
        .then(({ svg: rendered }) => {
          if (!cancelled) setSvg(rendered)
        })
        .catch(() => {
          if (!cancelled) setSvg(null)
        })
    })
    return () => {
      cancelled = true
    }
  }, [mermaidText])

  function handleCopy() {
    if (!mermaidText) return
    navigator.clipboard.writeText(mermaidText).then(() => {
      toast.success("Kopierat till urklipp")
    })
  }

  function handleDownloadSvg() {
    if (!svg) return
    const blob = new Blob([svg], { type: "image/svg+xml" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${diagramType}.svg`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleTypeChange(val: DiagramType) {
    setDiagramType(val)
    setSubId("")
    setMermaidText(null)
    setSvg(null)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <NetworkIcon className="size-6 text-muted-foreground" />
            Diagram
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generera och exportera arkitekturdiagram
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3">
        <Select
          value={diagramType}
          onValueChange={(v) => handleTypeChange(v as DiagramType)}
        >
          <SelectTrigger className="w-52" aria-label="Välj diagramtyp">
            <SelectValue placeholder="Diagramtyp">
              {diagramType ? DIAGRAM_LABELS[diagramType] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(DIAGRAM_LABELS) as DiagramType[]).map((t) => (
              <SelectItem key={t} value={t}>
                {DIAGRAM_LABELS[t]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Org dropdown — always visible */}
        <Select
          value={orgId || undefined}
          onValueChange={(v) => setOrgId(v ?? "")}
        >
          <SelectTrigger className="w-52" aria-label="Välj organisation">
            <SelectValue placeholder="Organisation">
              {orgId
                ? (orgs ?? []).find((o) => o.id === orgId)?.name
                : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla organisationer</SelectItem>
            {(orgs ?? []).map((org) => (
              <SelectItem key={org.id} value={org.id}>
                {org.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {needsProcess && (
          <Select
            value={subId || undefined}
            onValueChange={(v) => setSubId(v ?? "")}
          >
            <SelectTrigger className="w-64" aria-label="Välj process">
              <SelectValue placeholder="Välj process">
                {subId
                  ? (processes?.items ?? []).find((p) => p.id === subId)?.name
                  : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(processes?.items ?? []).map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {needsValueStream && (
          <Select
            value={subId || undefined}
            onValueChange={(v) => setSubId(v ?? "")}
          >
            <SelectTrigger className="w-64" aria-label="Välj värdeström">
              <SelectValue placeholder="Välj värdeström">
                {subId
                  ? (valueStreams?.items ?? []).find((vs) => vs.id === subId)?.name
                  : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(valueStreams?.items ?? []).map((vs) => (
                <SelectItem key={vs.id} value={vs.id}>
                  {vs.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {needsSystem && (
          <Select
            value={subId || undefined}
            onValueChange={(v) => setSubId(v ?? "")}
          >
            <SelectTrigger className="w-64" aria-label="Välj system">
              <SelectValue placeholder="Välj system">
                {subId
                  ? (systems?.items ?? []).find((s) => s.id === subId)?.name
                  : undefined}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(systems?.items ?? []).map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={!path || isFetching}
          aria-label="Hämta diagram"
        >
          {isFetching ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            "Hämta diagram"
          )}
        </Button>
      </div>

      {/* Error */}
      {isError && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta diagramdata.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      )}

      {/* Diagram preview */}
      {svg && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{DIAGRAM_LABELS[diagramType]}</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  aria-label="Kopiera Mermaid-kod"
                >
                  <ClipboardIcon className="mr-1 size-4" />
                  Kopiera Mermaid-kod
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadSvg}
                  aria-label="Ladda ner SVG"
                >
                  <DownloadIcon className="mr-1 size-4" />
                  Ladda ner SVG
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div
              className="overflow-auto rounded border bg-white p-4"
              // Safe: SVG generated by our own backend via mermaid
              dangerouslySetInnerHTML={{ __html: svg }}
              aria-label="Diagramförhandsvisning"
            />
          </CardContent>
        </Card>
      )}

      {/* Mermaid source */}
      {mermaidText && !svg && !isFetching && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Mermaid-kod</CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                aria-label="Kopiera Mermaid-kod"
              >
                <ClipboardIcon className="mr-1 size-4" />
                Kopiera
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="overflow-auto rounded bg-muted p-4 text-xs">{mermaidText}</pre>
          </CardContent>
        </Card>
      )}

      {/* Export section */}
      <Card>
        <CardHeader>
          <CardTitle>Exportera till verktyg</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-3 items-start">
            <a
              href={archimateExportUrl(orgId)}
              download="archimate-export.xml"
              aria-label="Ladda ner ArchiMate XML"
            >
              <Button variant="outline" size="sm" disabled={!orgId}>
                <DownloadIcon className="mr-1 size-4" />
                Ladda ner ArchiMate XML
              </Button>
            </a>
            <div className="flex flex-col gap-1">
              <a
                href={twoseightPackageUrl(orgId)}
                download="2c8-package.zip"
                aria-label="Ladda ner 2C8-paket"
              >
                <Button variant="outline" size="sm" disabled={!orgId}>
                  <DownloadIcon className="mr-1 size-4" />
                  Ladda ner 2C8-paket (zip)
                </Button>
              </a>
              <p className="text-xs text-muted-foreground">
                Importera zip-filen i 2C8 via Arkiv → Importera paket.
              </p>
            </div>
          </div>
          {!orgId && (
            <p className="text-xs text-muted-foreground">
              Välj en organisation för att aktivera exportknappar.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
