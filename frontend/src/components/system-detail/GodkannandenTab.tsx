import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"

import type { SystemDetail } from "@/types"
import { ApprovalStatus, ApprovalType } from "@/types"
import { getApprovals } from "@/lib/api"
import { approvalStatusLabels, approvalTypeLabels, approvalStatusBadgeClass } from "@/lib/labels"
import { formatDate } from "@/lib/format"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export function GodkannandenTab({ system }: { system: SystemDetail }) {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ["approvals", "system", system.id],
    queryFn: () => getApprovals({ organization_id: system.organization_id, limit: 200 }),
  })

  // Filter client-side for approvals targeting this system
  const approvals = (data?.items ?? []).filter(
    (a) => a.target_table === "systems" && a.target_record_id === system.id
  )

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton h-10 rounded" />
        ))}
      </div>
    )
  }

  if (approvals.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        Inga godkannandeaerenden for detta system.
      </p>
    )
  }

  return (
    <div className="rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Titel</TableHead>
            <TableHead>Typ</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Begard av</TableHead>
            <TableHead>Skapad</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {approvals.map((approval) => (
            <TableRow
              key={approval.id}
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => navigate(`/approvals/${approval.id}`)}
            >
              <TableCell className="font-medium">{approval.title}</TableCell>
              <TableCell>
                {approvalTypeLabels[approval.approval_type as ApprovalType] ?? approval.approval_type}
              </TableCell>
              <TableCell>
                <span className={`inline-flex h-6 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${approvalStatusBadgeClass[approval.status as ApprovalStatus] ?? ""}`}>
                  {approvalStatusLabels[approval.status as ApprovalStatus] ?? approval.status}
                </span>
              </TableCell>
              <TableCell>{approval.requested_by ?? "\u2014"}</TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(approval.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
