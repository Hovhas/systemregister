import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { XIcon, CheckIcon, XCircleIcon } from "lucide-react"

import { getApprovals, getOrganizations, reviewApproval } from "@/lib/api"
import { ApprovalStatus, ApprovalType } from "@/types"
import { approvalStatusLabels, approvalTypeLabels, approvalStatusBadgeClass } from "@/lib/labels"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

// --- Skeleton ---

function TableRowSkeleton() {
  return (
    <TableRow>
      {Array.from({ length: 7 }).map((_, i) => (
        <TableCell key={i}>
          <div className="skeleton h-4 w-full max-w-[120px]" />
        </TableCell>
      ))}
    </TableRow>
  )
}

// --- Hjälpkomponenter ---

function ApprovalStatusBadge({ value }: { value: ApprovalStatus }) {
  const colorClass = approvalStatusBadgeClass[value]
  return (
    <span
      className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${colorClass}`}
    >
      {approvalStatusLabels[value]}
    </span>
  )
}

const PAGE_SIZE = 50

export default function ApprovalsPage() {
  const queryClient = useQueryClient()
  const [organization, setOrganization] = useState("")
  const [statusFilter, setStatusFilter] = useState<ApprovalStatus | "">("")
  const [offset, setOffset] = useState(0)

  // Review dialog state
  const [reviewDialog, setReviewDialog] = useState<{
    open: boolean
    approvalId: string
    action: "godkänd" | "avvisad"
  }>({ open: false, approvalId: "", action: "godkänd" })
  const [reviewedBy, setReviewedBy] = useState("")
  const [reviewComment, setReviewComment] = useState("")

  const hasFilters = !!(organization || statusFilter)

  function clearFilters() {
    setOrganization("")
    setStatusFilter("")
    setOffset(0)
  }

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  })
  const orgNameMap = Object.fromEntries(
    (orgs ?? []).map((o) => [o.id, o.name])
  )

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["approvals", organization, statusFilter, offset],
    queryFn: () =>
      getApprovals({
        organization_id: organization || undefined,
        status: statusFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, status, reviewed_by, review_comment }: {
      id: string
      status: ApprovalStatus
      reviewed_by: string
      review_comment?: string
    }) => reviewApproval(id, { status, reviewed_by, review_comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] })
      toast.success("Godkännande uppdaterat")
      closeReviewDialog()
    },
    onError: () => {
      // API interceptor shows toast already
    },
  })

  function openReviewDialog(approvalId: string, action: "godkänd" | "avvisad") {
    setReviewDialog({ open: true, approvalId, action })
    setReviewedBy("")
    setReviewComment("")
  }

  function closeReviewDialog() {
    setReviewDialog({ open: false, approvalId: "", action: "godkänd" })
    setReviewedBy("")
    setReviewComment("")
  }

  function handleReviewSubmit() {
    if (!reviewedBy.trim()) return
    reviewMutation.mutate({
      id: reviewDialog.approvalId,
      status: reviewDialog.action as ApprovalStatus,
      reviewed_by: reviewedBy.trim(),
      review_comment: reviewComment.trim() || undefined,
    })
  }

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Godkännanden</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {total > 0 ? `${total} godkännanden totalt` : "Inga godkännanden hittade"}
          </p>
        </div>
      </div>

      {/* Filter-rad */}
      <div className="flex flex-wrap gap-2">
        <Select
          value={organization || undefined}
          onValueChange={(val) => {
            setOrganization(val ?? "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Organisation">
              {organization ? orgNameMap[organization] : undefined}
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

        <Select
          value={statusFilter as string}
          onValueChange={(val) => {
            setStatusFilter(val as ApprovalStatus | "")
            setOffset(0)
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Status">
              {statusFilter ? approvalStatusLabels[statusFilter as ApprovalStatus] : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Alla statusar</SelectItem>
            {Object.values(ApprovalStatus).map((s) => (
              <SelectItem key={s} value={s}>
                {approvalStatusLabels[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <XIcon className="mr-1 size-4" />
            Rensa
          </Button>
        )}
      </div>

      {/* Tabell */}
      {isError ? (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <p>Kunde inte hämta godkännanden. Kontrollera att backend körs.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Försök igen
          </Button>
        </div>
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Titel</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Begärd av</TableHead>
                <TableHead>Skapad</TableHead>
                <TableHead>Granskad av</TableHead>
                <TableHead className="text-right">Åtgärder</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRowSkeleton key={i} />
                ))
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    Inga godkännanden matchar sökningen
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((approval, idx) => (
                  <TableRow
                    key={approval.id}
                    className={`transition-colors hover:bg-muted/50 ${idx % 2 === 1 ? "bg-muted/20" : ""}`}
                  >
                    <TableCell className="font-medium">{approval.title}</TableCell>
                    <TableCell>
                      {approvalTypeLabels[approval.approval_type as ApprovalType] ?? approval.approval_type}
                    </TableCell>
                    <TableCell>
                      <ApprovalStatusBadge value={approval.status as ApprovalStatus} />
                    </TableCell>
                    <TableCell>{approval.requested_by ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(approval.created_at).toLocaleDateString("sv-SE")}
                    </TableCell>
                    <TableCell>{approval.reviewed_by ?? "—"}</TableCell>
                    <TableCell className="text-right">
                      {approval.status === ApprovalStatus.PENDING && (
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openReviewDialog(approval.id, "godkänd")}
                          >
                            <CheckIcon className="mr-1 size-3.5" />
                            Godkänn
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openReviewDialog(approval.id, "avvisad")}
                          >
                            <XCircleIcon className="mr-1 size-3.5" />
                            Avvisa
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Paginering */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-muted-foreground">
            Sida {currentPage} av {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Föregående
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Nästa
            </Button>
          </div>
        </div>
      )}

      {/* Granskningsdialog */}
      <Dialog open={reviewDialog.open} onOpenChange={(open) => { if (!open) closeReviewDialog() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {reviewDialog.action === "godkänd" ? "Godkänn" : "Avvisa"} godkännande
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
            <Button variant="outline" onClick={closeReviewDialog}>
              Avbryt
            </Button>
            <Button
              variant={reviewDialog.action === "godkänd" ? "default" : "destructive"}
              disabled={!reviewedBy.trim() || reviewMutation.isPending}
              onClick={handleReviewSubmit}
            >
              {reviewMutation.isPending
                ? (reviewDialog.action === "godkänd" ? "Godkänner..." : "Avvisar...")
                : (reviewDialog.action === "godkänd" ? "Godkänn" : "Avvisa")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
