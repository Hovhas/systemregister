import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeftIcon, TrashIcon, CheckIcon, XCircleIcon } from "lucide-react"
import { toast } from "sonner"

import { ApprovalStatus, ApprovalType } from "@/types"
import { getApproval, deleteApproval, reviewApproval, getSystem } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { approvalStatusLabels, approvalTypeLabels, approvalStatusBadgeClass } from "@/lib/labels"
import { Breadcrumb } from "@/components/Breadcrumb"
import { ConfirmDialog } from "@/components/ConfirmDialog"
import { InfoRow } from "@/components/system-detail/helpers"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export default function ApprovalDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [reviewDialog, setReviewDialog] = useState<{
    open: boolean
    action: "godkänd" | "avvisad"
  }>({ open: false, action: "godkänd" })
  const [reviewedBy, setReviewedBy] = useState("")
  const [reviewComment, setReviewComment] = useState("")

  const { data: approval, isLoading, isError, refetch } = useQuery({
    queryKey: ["approval", id],
    queryFn: () => getApproval(id!),
    enabled: !!id,
  })

  // If approval targets a system, fetch it for context
  const { data: targetSystem } = useQuery({
    queryKey: ["system", approval?.target_record_id],
    queryFn: () => getSystem(approval!.target_record_id!),
    enabled: !!approval?.target_record_id && approval?.target_table === "systems",
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteApproval(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] })
      toast.success("Arende borttaget")
      navigate("/approvals")
    },
    onError: () => toast.error("Kunde inte ta bort arende"),
  })

  const reviewMut = useMutation({
    mutationFn: ({ status, reviewed_by, review_comment }: {
      status: ApprovalStatus
      reviewed_by: string
      review_comment?: string
    }) => reviewApproval(id!, { status, reviewed_by, review_comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", id] })
      queryClient.invalidateQueries({ queryKey: ["approvals"] })
      toast.success("Godkannande uppdaterat")
      closeReviewDialog()
    },
  })

  function openReviewDialog(action: "godkänd" | "avvisad") {
    setReviewDialog({ open: true, action })
    setReviewedBy("")
    setReviewComment("")
  }

  function closeReviewDialog() {
    setReviewDialog({ open: false, action: "godkänd" })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="skeleton h-6 w-48" />
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-48 rounded-xl" />
      </div>
    )
  }

  if (isError || !approval) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/approvals")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex items-center gap-3 text-sm text-destructive">
          <p>Kunde inte hamta arende.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Forsok igen</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Godkannanden", href: "/approvals" }, { label: approval.title }]} />

      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <Button variant="ghost" size="sm" className="mt-0.5 shrink-0 w-fit" onClick={() => navigate("/approvals")}>
          <ArrowLeftIcon className="mr-1 size-4" /> Tillbaka
        </Button>
        <div className="flex flex-col gap-1 flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{approval.title}</h1>
            <span className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${approvalStatusBadgeClass[approval.status as ApprovalStatus] ?? ""}`}>
              {approvalStatusLabels[approval.status as ApprovalStatus] ?? approval.status}
            </span>
          </div>
          {approval.description && (
            <p className="text-sm text-muted-foreground max-w-xl">{approval.description}</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {approval.status === ApprovalStatus.PENDING && (
            <>
              <Button variant="outline" size="sm" onClick={() => openReviewDialog("godkänd")}>
                <CheckIcon className="mr-1 size-4" /> Godkann
              </Button>
              <Button variant="outline" size="sm" onClick={() => openReviewDialog("avvisad")}>
                <XCircleIcon className="mr-1 size-4" /> Avvisa
              </Button>
            </>
          )}
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
            <TrashIcon className="mr-1 size-4" /> Ta bort
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Ta bort arende"
        description={`Ar du saker pa att du vill ta bort "${approval.title}"?`}
        onConfirm={() => deleteMut.mutate()}
        loading={deleteMut.isPending}
      />

      <Tabs defaultValue="oversikt" className="mt-2">
        <TabsList>
          <TabsTrigger value="oversikt">Oversikt</TabsTrigger>
          <TabsTrigger value="granskning">Granskning</TabsTrigger>
        </TabsList>

        <TabsContent value="oversikt" className="mt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Arendeinformation</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Typ" value={approvalTypeLabels[approval.approval_type as ApprovalType] ?? approval.approval_type} />
                <InfoRow
                  label="Status"
                  value={
                    <span className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${approvalStatusBadgeClass[approval.status as ApprovalStatus] ?? ""}`}>
                      {approvalStatusLabels[approval.status as ApprovalStatus] ?? approval.status}
                    </span>
                  }
                />
                <InfoRow label="Beskrivning" value={approval.description} />
                <InfoRow label="Begard av" value={approval.requested_by} />
                <InfoRow label="Skapad" value={formatDateTime(approval.created_at)} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Kopplad resurs</CardTitle></CardHeader>
              <CardContent className="flex flex-col">
                <InfoRow label="Tabell" value={approval.target_table} />
                <InfoRow label="Post-ID" value={approval.target_record_id} />
                {targetSystem && (
                  <InfoRow
                    label="System"
                    value={
                      <button
                        className="text-primary hover:underline text-left"
                        onClick={() => navigate(`/systems/${targetSystem.id}`)}
                      >
                        {targetSystem.name}
                      </button>
                    }
                  />
                )}
                {approval.proposed_changes && Object.keys(approval.proposed_changes).length > 0 && (
                  <InfoRow
                    label="Foreslagna andringar"
                    value={
                      <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(approval.proposed_changes, null, 2)}
                      </pre>
                    }
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="granskning" className="mt-6">
          <Card>
            <CardHeader><CardTitle>Granskningsinformation</CardTitle></CardHeader>
            <CardContent className="flex flex-col">
              <InfoRow label="Granskad av" value={approval.reviewed_by} />
              <InfoRow label="Granskad" value={formatDateTime(approval.reviewed_at)} />
              <InfoRow label="Kommentar" value={approval.review_comment} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Granskningsdialog */}
      <Dialog open={reviewDialog.open} onOpenChange={(open) => { if (!open) closeReviewDialog() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {reviewDialog.action === "godkänd" ? "Godkann" : "Avvisa"} arende
            </DialogTitle>
            <DialogDescription>
              Ange ditt namn och en valfri kommentar.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Granskad av *</label>
              <Input
                placeholder="Ditt namn"
                value={reviewedBy}
                onChange={(e) => setReviewedBy(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Kommentar</label>
              <Input
                placeholder="Valfri kommentar"
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeReviewDialog}>Avbryt</Button>
            <Button
              variant={reviewDialog.action === "godkänd" ? "default" : "destructive"}
              disabled={!reviewedBy.trim() || reviewMut.isPending}
              onClick={() => reviewMut.mutate({
                status: reviewDialog.action as ApprovalStatus,
                reviewed_by: reviewedBy.trim(),
                review_comment: reviewComment.trim() || undefined,
              })}
            >
              {reviewMut.isPending
                ? (reviewDialog.action === "godkänd" ? "Godkanner..." : "Avvisar...")
                : (reviewDialog.action === "godkänd" ? "Godkann" : "Avvisa")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
