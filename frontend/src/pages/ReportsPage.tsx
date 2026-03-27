import { FileTextIcon, DownloadIcon } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

const API_BASE = "/api/v1"

function downloadFile(url: string) {
  window.open(url, "_blank")
}

export default function ReportsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Rapporter</h1>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileTextIcon className="size-4" />
            NIS2-rapport
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/nis2`)}>
            <DownloadIcon className="size-4 mr-1.5" />
            JSON
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/nis2.xlsx`)}>
            <DownloadIcon className="size-4 mr-1.5" />
            Excel
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/nis2.pdf`)}>
            <DownloadIcon className="size-4 mr-1.5" />
            PDF
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/nis2.html`)}>
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
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/compliance-gap`)}>
            <DownloadIcon className="size-4 mr-1.5" />
            JSON
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/reports/compliance-gap.pdf`)}>
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
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/export/systems.xlsx`)}>
            System (Excel)
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/export/systems.csv`)}>
            System (CSV)
          </Button>
          <Button variant="outline" onClick={() => downloadFile(`${API_BASE}/export/systems.json`)}>
            System (JSON)
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
