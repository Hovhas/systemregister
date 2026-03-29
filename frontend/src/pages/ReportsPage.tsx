import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FileTextIcon, DownloadIcon, Loader2Icon } from "lucide-react"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getOrganizations } from "@/lib/api"
import type { Organization } from "@/types"

const API_BASE = "/api/v1"

function buildUrl(base: string, orgId?: string): string {
  if (!orgId) return base
  const sep = base.includes("?") ? "&" : "?"
  return `${base}${sep}organization_id=${encodeURIComponent(orgId)}`
}

/** Hämta fil via fetch och trigga blob-nedladdning med laddningsindikator */
async function downloadFile(url: string, setLoading: (key: string | null) => void, key: string) {
  setLoading(key)
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const blob = await response.blob()
    // Extrahera filnamn från Content-Disposition eller URL
    const disposition = response.headers.get("content-disposition")
    let filename = url.split("/").pop()?.split("?")[0] ?? "rapport"
    if (disposition) {
      const match = disposition.match(/filename="?([^";\n]+)"?/)
      if (match) filename = match[1]
    }
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(objectUrl)
  } catch {
    toast.error("Kunde inte ladda ner filen. Försök igen.")
  } finally {
    setLoading(null)
  }
}

function DownloadButton({ url, label, loadingKey, currentLoading, setLoading }: {
  url: string
  label: string
  loadingKey: string
  currentLoading: string | null
  setLoading: (key: string | null) => void
}) {
  const isLoading = currentLoading === loadingKey
  return (
    <Button
      variant="outline"
      disabled={isLoading}
      onClick={() => downloadFile(url, setLoading, loadingKey)}
    >
      {isLoading ? (
        <Loader2Icon className="size-4 mr-1.5 animate-spin" />
      ) : (
        <DownloadIcon className="size-4 mr-1.5" />
      )}
      {label}
    </Button>
  )
}

export default function ReportsPage() {
  const [selectedOrg, setSelectedOrg] = useState<string>("")
  const [loading, setLoading] = useState<string | null>(null)

  const { data: orgs } = useQuery<Organization[]>({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })

  const orgId = selectedOrg || undefined

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Rapporter</h1>

      {/* Organisations-filter */}
      {orgs && orgs.length > 0 && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground shrink-0">
            Filtrera organisation:
          </span>
          <Select
            value={selectedOrg}
            onValueChange={(v) => setSelectedOrg(v ?? "")}
          >
            <SelectTrigger className="w-60">
              <SelectValue placeholder="Alla organisationer">
                {selectedOrg
                  ? orgs.find((o) => o.id === selectedOrg)?.name ??
                    "Alla organisationer"
                  : "Alla organisationer"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Alla organisationer</SelectItem>
              {orgs.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileTextIcon className="size-4" />
            NIS2-rapport
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <DownloadButton url={buildUrl(`${API_BASE}/reports/nis2`, orgId)} label="JSON" loadingKey="nis2-json" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={buildUrl(`${API_BASE}/reports/nis2.xlsx`, orgId)} label="Excel" loadingKey="nis2-xlsx" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={buildUrl(`${API_BASE}/reports/nis2.pdf`, orgId)} label="PDF" loadingKey="nis2-pdf" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={buildUrl(`${API_BASE}/reports/nis2.html`, orgId)} label="HTML" loadingKey="nis2-html" currentLoading={loading} setLoading={setLoading} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileTextIcon className="size-4" />
            Compliance Gap-analys
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <DownloadButton url={`${API_BASE}/reports/compliance-gap`} label="JSON" loadingKey="gap-json" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={`${API_BASE}/reports/compliance-gap.pdf`} label="PDF" loadingKey="gap-pdf" currentLoading={loading} setLoading={setLoading} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <DownloadIcon className="size-4" />
            Export
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <DownloadButton url={`${API_BASE}/export/systems.xlsx`} label="System (Excel)" loadingKey="export-xlsx" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={`${API_BASE}/export/systems.csv`} label="System (CSV)" loadingKey="export-csv" currentLoading={loading} setLoading={setLoading} />
          <DownloadButton url={`${API_BASE}/export/systems.json`} label="System (JSON)" loadingKey="export-json" currentLoading={loading} setLoading={setLoading} />
        </CardContent>
      </Card>
    </div>
  )
}
