import {
  SystemCategory,
  LifecycleStatus,
  Criticality,
  IntegrationType,
  OwnerRole,
  NIS2Classification,
} from "@/types"

// --- Centrala etiketter för enums ---
// Alla svenska UI-etiketter samlade på ett ställe.

export const categoryLabels: Record<SystemCategory, string> = {
  [SystemCategory.VERKSAMHETSSYSTEM]: "Verksamhetssystem",
  [SystemCategory.STODSYSTEM]: "Stödsystem",
  [SystemCategory.INFRASTRUKTUR]: "Infrastruktur",
  [SystemCategory.PLATTFORM]: "Plattform",
  [SystemCategory.IOT]: "IoT",
}

export const lifecycleLabels: Record<LifecycleStatus, string> = {
  [LifecycleStatus.PLANNED]: "Planerad",
  [LifecycleStatus.IMPLEMENTING]: "Under införande",
  [LifecycleStatus.ACTIVE]: "I drift",
  [LifecycleStatus.DECOMMISSIONING]: "Under avveckling",
  [LifecycleStatus.DECOMMISSIONED]: "Avvecklad",
}

export const criticalityLabels: Record<Criticality, string> = {
  [Criticality.LOW]: "Låg",
  [Criticality.MEDIUM]: "Medel",
  [Criticality.HIGH]: "Hög",
  [Criticality.CRITICAL]: "Kritisk",
}

export const integrationTypeLabels: Record<IntegrationType, string> = {
  [IntegrationType.API]: "API",
  [IntegrationType.FILE_TRANSFER]: "Filöverföring",
  [IntegrationType.DB_REPLICATION]: "Databasreplikering",
  [IntegrationType.EVENT]: "Event",
  [IntegrationType.MANUAL]: "Manuell",
}

export const ownerRoleLabels: Record<OwnerRole, string> = {
  [OwnerRole.SYSTEM_OWNER]: "Systemägare",
  [OwnerRole.INFORMATION_OWNER]: "Informationsägare",
  [OwnerRole.SYSTEM_ADMINISTRATOR]: "Systemförvaltare",
  [OwnerRole.TECHNICAL_ADMINISTRATOR]: "Teknisk förvaltare",
  [OwnerRole.IT_CONTACT]: "IT-kontakt",
  [OwnerRole.DPO]: "Dataskyddsombud",
}

export const nis2ClassificationLabels: Record<NIS2Classification, string> = {
  [NIS2Classification.ESSENTIAL]: "Väsentlig",
  [NIS2Classification.IMPORTANT]: "Viktig",
  [NIS2Classification.NOT_APPLICABLE]: "Ej tillämplig",
}

// Badge-varianter för kritikalitet
export const criticalityBadgeClass: Record<Criticality, string> = {
  [Criticality.CRITICAL]: "bg-red-100 text-red-800 border-red-200",
  [Criticality.HIGH]: "bg-orange-100 text-orange-800 border-orange-200",
  [Criticality.MEDIUM]: "bg-yellow-100 text-yellow-800 border-yellow-200",
  [Criticality.LOW]: "bg-green-100 text-green-800 border-green-200",
}

// Badge-varianter (shadcn) för kritikalitet
export const criticalityVariant: Record<
  Criticality,
  "default" | "secondary" | "destructive" | "outline"
> = {
  [Criticality.LOW]: "secondary",
  [Criticality.MEDIUM]: "outline",
  [Criticality.HIGH]: "default",
  [Criticality.CRITICAL]: "destructive",
}

// SVG-färger för kritikalitet (beroendevisualisering)
export const criticalityColor: Record<Criticality, string> = {
  [Criticality.LOW]: "#86efac",
  [Criticality.MEDIUM]: "#fcd34d",
  [Criticality.HIGH]: "#fb923c",
  [Criticality.CRITICAL]: "#f87171",
}
