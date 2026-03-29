import { useRef, useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { UploadIcon, CheckCircleIcon, AlertCircleIcon, Loader2Icon } from "lucide-react"

import { getOrganizations, importFile } from "@/lib/api"
import type { ImportResult } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"

type ImportType = "systems" | "classifications" | "owners"

interface TabPanelProps {
  type: ImportType
}

function ImportTabPanel({ type }: TabPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [organizationId, setOrganizationId] = useState<string>("")
  const [result, setResult] = useState<ImportResult | null>(null)

  const { data: organizations } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
    enabled: type === "systems",
  })

  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("Ingen fil vald")
      return importFile(type, selectedFile, organizationId || undefined)
    },
    onSuccess: (data) => {
      setResult(data)
    },
  })

  function handleFile(file: File | undefined) {
    if (!file) return
    setSelectedFile(file)
    setResult(null)
    mutation.reset()
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    handleFile(e.target.files?.[0])
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    handleFile(e.dataTransfer.files[0])
  }

  const canImport =
    selectedFile !== null &&
    (type !== "systems" || organizationId !== "")

  return (
    <div className="space-y-4">
      {type === "systems" && (
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Organisation (obligatorisk)</label>
          <Select value={organizationId} onValueChange={(val) => setOrganizationId(val ?? "")}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Välj organisation...">
                {organizations?.find((o) => o.id === organizationId)?.name}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {organizations?.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div
        className="border-2 border-dashed rounded-xl p-10 text-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-all duration-200"
        role="button"
        tabIndex={0}
        aria-label="Välj fil att importera"
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInputRef.current?.click() } }}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
        onDrop={handleDrop}
      >
        <UploadIcon className="mx-auto size-8 text-muted-foreground mb-2" />
        <p className="text-sm">Dra och släpp fil här, eller klicka för att välja</p>
        <p className="text-xs text-muted-foreground mt-1">Stöder .xlsx och .csv</p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.csv"
        className="hidden"
        onChange={handleFileInputChange}
      />

      {selectedFile && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground rounded-md bg-muted px-3 py-2">
          <UploadIcon className="size-4 shrink-0" />
          <span className="truncate">{selectedFile.name}</span>
          <span className="ml-auto shrink-0">
            {(selectedFile.size / 1024).toFixed(1)} KB
          </span>
        </div>
      )}

      <Button
        onClick={() => mutation.mutate()}
        disabled={!canImport || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending ? (
          <>
            <Loader2Icon className="mr-2 size-4 animate-spin" />
            Importerar...
          </>
        ) : (
          "Importera"
        )}
      </Button>

      {mutation.isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" />
          <span>Importerar fil, vänta...</span>
        </div>
      )}

      {result && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-green-700">
            <CheckCircleIcon className="size-4" />
            <span>{result.imported} poster importerade</span>
          </div>
          {result.errors.length > 0 && (
            <div className="space-y-1">
              <p className="text-sm font-medium text-destructive flex items-center gap-1.5">
                <AlertCircleIcon className="size-4" />
                {result.errors.length} fel
              </p>
              <ul className="text-xs space-y-1 max-h-48 overflow-y-auto rounded border p-2">
                {result.errors.map((err, i) => (
                  <li key={i} className="text-muted-foreground">
                    <span className="font-medium text-foreground">Rad {err.row}:</span>{" "}
                    {typeof err.error === "string"
                      ? err.error
                      : (err.error as Record<string, string>)?.field
                        ? `${(err.error as Record<string, string>).field}: ${(err.error as Record<string, string>).msg}`
                        : JSON.stringify(err.error)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {mutation.isError && (
        <p className="text-sm text-destructive flex items-center gap-1.5">
          <AlertCircleIcon className="size-4" />
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Import misslyckades"}
        </p>
      )}
    </div>
  )
}

export default function ImportPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Import</h1>
        <p className="text-sm text-muted-foreground mt-1">Importera system, klassningar och ägare från fil</p>
      </div>

      <Tabs defaultValue="systems">
        <TabsList>
          <TabsTrigger value="systems">System</TabsTrigger>
          <TabsTrigger value="classifications">Klassningar</TabsTrigger>
          <TabsTrigger value="owners">Ägare</TabsTrigger>
        </TabsList>

        <TabsContent value="systems">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Importera system</CardTitle>
            </CardHeader>
            <CardContent>
              <ImportTabPanel type="systems" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="classifications">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Importera klassningar</CardTitle>
            </CardHeader>
            <CardContent>
              <ImportTabPanel type="classifications" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="owners">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Importera ägare</CardTitle>
            </CardHeader>
            <CardContent>
              <ImportTabPanel type="owners" />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
