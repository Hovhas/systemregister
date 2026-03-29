import { useState } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  AlertCircleIcon,
  AlertTriangleIcon,
  InfoIcon,
  CheckCircleIcon,
  ExternalLinkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "lucide-react"

import { getNotifications } from "@/lib/api"
import type { Notification } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

// --- Hjälpfunktioner ---

const SEVERITY_CONFIG = {
  critical: {
    label: "Kritisk",
    icon: AlertCircleIcon,
    badgeClass: "bg-red-100 text-red-800 border-red-200",
    iconClass: "text-red-500",
    cardClass: "border-red-200",
    statClass: "text-red-600",
    statBg: "bg-red-50",
  },
  warning: {
    label: "Varning",
    icon: AlertTriangleIcon,
    badgeClass: "bg-orange-100 text-orange-800 border-orange-200",
    iconClass: "text-orange-500",
    cardClass: "border-orange-200",
    statClass: "text-orange-600",
    statBg: "bg-orange-50",
  },
  info: {
    label: "Info",
    icon: InfoIcon,
    badgeClass: "bg-blue-100 text-blue-800 border-blue-200",
    iconClass: "text-blue-500",
    cardClass: "border-blue-200",
    statClass: "text-blue-600",
    statBg: "bg-blue-50",
  },
} as const

const typeLabels: Record<string, string> = {
  expiring_contract: "Utgående avtal",
  missing_classification: "Saknar klassning",
  missing_owner: "Saknar ägare",
  missing_gdpr_treatment: "Saknar GDPR-behandling",
  stale_classification: "Klassning behöver uppdateras",
  missing_risk_assessment: "Saknar riskbedömning",
}

const PAGE_SIZE = 25

// --- Statistik-kort ---

function StatCard({
  severity,
  count,
}: {
  severity: "critical" | "warning" | "info"
  count: number
}) {
  const cfg = SEVERITY_CONFIG[severity]
  const Icon = cfg.icon

  return (
    <div className={`rounded-lg border p-4 flex items-center gap-3 ${cfg.statBg}`}>
      <div className={`rounded-full p-2 bg-white`}>
        <Icon className={`size-5 ${cfg.iconClass}`} />
      </div>
      <div>
        <p className={`text-2xl font-bold leading-none ${cfg.statClass}`}>{count}</p>
        <p className="text-sm text-muted-foreground mt-1">{cfg.label}</p>
      </div>
    </div>
  )
}

// --- Notifikationskort ---

function NotificationCard({ notification }: { notification: Notification }) {
  const cfg = SEVERITY_CONFIG[notification.severity]
  const Icon = cfg.icon

  return (
    <Card className={`${cfg.cardClass}`}>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-3">
          <div className="shrink-0 mt-0.5">
            <Icon className={`size-5 ${cfg.iconClass}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <Badge variant="outline" className={`text-xs ${cfg.badgeClass}`}>
                {cfg.label}
              </Badge>
              <span className="text-xs text-muted-foreground font-mono">
                {typeLabels[notification.type] ?? notification.type}
              </span>
            </div>
            <p className="font-medium text-sm">{notification.title}</p>
            <p className="text-sm text-muted-foreground mt-1">{notification.description}</p>
            {notification.system_id && (
              <Link
                to={`/systems/${notification.system_id}`}
                className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
              >
                Gå till system
                <ExternalLinkIcon className="size-3" />
              </Link>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Notifikationsgrupp ---

function NotificationGroup({
  severity,
  notifications,
}: {
  severity: "critical" | "warning" | "info"
  notifications: Notification[]
}) {
  const cfg = SEVERITY_CONFIG[severity]
  const Icon = cfg.icon

  if (notifications.length === 0) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`size-4 ${cfg.iconClass}`} />
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {cfg.label} ({notifications.length})
        </h2>
      </div>
      <div className="flex flex-col gap-2">
        {notifications.map((n, i) => (
          <NotificationCard key={`${n.type}-${n.system_id ?? ""}-${i}`} notification={n} />
        ))}
      </div>
    </div>
  )
}

// --- Tom-vy ---

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="rounded-full bg-green-50 p-4 mb-4">
        <CheckCircleIcon className="size-10 text-green-500" />
      </div>
      <h2 className="text-lg font-semibold">Inga aktiva notifikationer</h2>
      <p className="text-sm text-muted-foreground mt-1">
        Alla system ser bra ut just nu.
      </p>
    </div>
  )
}

// --- Paginering ---

function Pagination({
  offset,
  limit,
  total,
  onPageChange,
}: {
  offset: number
  limit: number
  total: number
  onPageChange: (newOffset: number) => void
}) {
  const currentPage = Math.floor(offset / limit) + 1
  const totalPages = Math.ceil(total / limit)

  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between pt-4">
      <p className="text-sm text-muted-foreground">
        Visar {offset + 1}–{Math.min(offset + limit, total)} av {total}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
        >
          <ChevronLeftIcon className="size-4" />
          Föregående
        </Button>
        <span className="text-sm text-muted-foreground">
          Sida {currentPage} av {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(offset + limit)}
          disabled={offset + limit >= total}
        >
          Nästa
          <ChevronRightIcon className="size-4" />
        </Button>
      </div>
    </div>
  )
}

// --- Sidan ---

export default function NotificationsPage() {
  const [offset, setOffset] = useState(0)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["notifications", offset],
    queryFn: () => getNotifications({ limit: PAGE_SIZE, offset }),
  })

  const bySeverity = data?.by_severity ?? { critical: 0, warning: 0, info: 0 }
  const items = data?.items ?? []
  const total = data?.total ?? 0

  const critical = items.filter((n) => n.severity === "critical")
  const warning = items.filter((n) => n.severity === "warning")
  const info = items.filter((n) => n.severity === "info")

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Notifikationer</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Aktiva varningar och informationsmeddelanden för systemregistret.
        </p>
      </div>

      {/* Statistik-kort */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard severity="critical" count={bySeverity.critical} />
        <StatCard severity="warning" count={bySeverity.warning} />
        <StatCard severity="info" count={bySeverity.info} />
      </div>

      {/* Innehåll */}
      {isLoading && (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
          Laddar notifikationer...
        </div>
      )}

      {isError && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive text-sm">
              Kunde inte hämta notifikationer
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Kontrollera att backend-tjänsten är igång och försök igen.
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && total === 0 && <EmptyState />}

      {!isLoading && !isError && total > 0 && (
        <div className="space-y-6">
          <NotificationGroup severity="critical" notifications={critical} />
          <NotificationGroup severity="warning" notifications={warning} />
          <NotificationGroup severity="info" notifications={info} />

          <Pagination
            offset={offset}
            limit={PAGE_SIZE}
            total={total}
            onPageChange={setOffset}
          />
        </div>
      )}
    </div>
  )
}
