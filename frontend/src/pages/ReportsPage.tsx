import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FileTextIcon, DownloadIcon } from "lucide-react"
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

function downloadFile(url: string) {
  window.open(url, "_blank")
}

export default function ReportsPage() {
  const [selectedOrg, setSelectedOrg] = useState<string>("")

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
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(buildUrl(`${API_BASE}/reports/nis2`, orgId))
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            JSON
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(buildUrl(`${API_BASE}/reports/nis2.xlsx`, orgId))
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            Excel
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(buildUrl(`${API_BASE}/reports/nis2.pdf`, orgId))
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            PDF
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(buildUrl(`${API_BASE}/reports/nis2.html`, orgId))
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            HTML
          </Button>
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
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(`${API_BASE}/reports/compliance-gap`)
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            JSON
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(`${API_BASE}/reports/compliance-gap.pdf`)
            }
          >
            <DownloadIcon className="size-4 mr-1.5" />
            PDF
          </Button>
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
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(`${API_BASE}/export/systems.xlsx`)
            }
          >
            System (Excel)
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(`${API_BASE}/export/systems.csv`)
            }
          >
            System (CSV)
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              downloadFile(`${API_BASE}/export/systems.json`)
            }
          >
            System (JSON)
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
