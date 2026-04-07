import {
  SystemCategory,
  LifecycleStatus,
  Criticality,
  IntegrationType,
  OwnerRole,
  NIS2Classification,
  AIRiskClass,
  FRIAStatus,
  ApprovalStatus,
  ApprovalType,
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

// AI-förordningen
export const aiRiskClassLabels: Record<AIRiskClass, string> = {
  [AIRiskClass.FORBIDDEN]: "Förbjuden",
  [AIRiskClass.HIGH_RISK]: "Hög risk",
  [AIRiskClass.LIMITED_RISK]: "Begränsad risk",
  [AIRiskClass.MINIMAL_RISK]: "Minimal risk",
  [AIRiskClass.NOT_APPLICABLE]: "Ej tillämplig",
}

export const friaStatusLabels: Record<FRIAStatus, string> = {
  [FRIAStatus.YES]: "Ja",
  [FRIAStatus.NO]: "Nej",
  [FRIAStatus.NOT_APPLICABLE]: "Ej tillämplig",
}

export const aiRiskBadgeClass: Record<AIRiskClass, string> = {
  [AIRiskClass.FORBIDDEN]: "bg-red-100 text-red-800 border-red-200",
  [AIRiskClass.HIGH_RISK]: "bg-orange-100 text-orange-800 border-orange-200",
  [AIRiskClass.LIMITED_RISK]: "bg-yellow-100 text-yellow-800 border-yellow-200",
  [AIRiskClass.MINIMAL_RISK]: "bg-green-100 text-green-800 border-green-200",
  [AIRiskClass.NOT_APPLICABLE]: "bg-gray-100 text-gray-800 border-gray-200",
}

// Godkännanden (FK-15)
export const approvalStatusLabels: Record<ApprovalStatus, string> = {
  [ApprovalStatus.PENDING]: "Väntande",
  [ApprovalStatus.APPROVED]: "Godkänd",
  [ApprovalStatus.REJECTED]: "Avvisad",
  [ApprovalStatus.CANCELLED]: "Avbruten",
}

export const approvalTypeLabels: Record<ApprovalType, string> = {
  [ApprovalType.SYSTEM_REGISTRATION]: "Systemregistrering",
  [ApprovalType.SYSTEM_DECOMMISSION]: "Avveckling",
  [ApprovalType.CLASSIFICATION_CHANGE]: "Klassningsändring",
  [ApprovalType.GDPR_TREATMENT]: "GDPR-behandling",
  [ApprovalType.DATA_CHANGE]: "Dataändring",
}

export const approvalStatusBadgeClass: Record<ApprovalStatus, string> = {
  [ApprovalStatus.PENDING]: "bg-yellow-100 text-yellow-800 border-yellow-200",
  [ApprovalStatus.APPROVED]: "bg-green-100 text-green-800 border-green-200",
  [ApprovalStatus.REJECTED]: "bg-red-100 text-red-800 border-red-200",
  [ApprovalStatus.CANCELLED]: "bg-gray-100 text-gray-800 border-gray-200",
}

// SVG-färger för kritikalitet (beroendevisualisering)
export const criticalityColor: Record<Criticality, string> = {
  [Criticality.LOW]: "#86efac",
  [Criticality.MEDIUM]: "#fcd34d",
  [Criticality.HIGH]: "#fb923c",
  [Criticality.CRITICAL]: "#f87171",
}
