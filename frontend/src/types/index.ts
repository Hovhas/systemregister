// Enums — matchar backend/app/models/enums.py

export enum OrganizationType {
  KOMMUN = "kommun",
  BOLAG = "bolag",
  SAMVERKAN = "samverkan",
  DIGIT = "digit",
}

export enum SystemCategory {
  VERKSAMHETSSYSTEM = "verksamhetssystem",
  STODSYSTEM = "stödsystem",
  INFRASTRUKTUR = "infrastruktur",
  PLATTFORM = "plattform",
  IOT = "iot",
}

export enum LifecycleStatus {
  PLANNED = "planerad",
  IMPLEMENTING = "under_inforande",
  ACTIVE = "i_drift",
  DECOMMISSIONING = "under_avveckling",
  DECOMMISSIONED = "avvecklad",
}

export enum Criticality {
  LOW = "låg",
  MEDIUM = "medel",
  HIGH = "hög",
  CRITICAL = "kritisk",
}

export enum OwnerRole {
  SYSTEM_OWNER = "systemägare",
  INFORMATION_OWNER = "informationsägare",
  SYSTEM_ADMINISTRATOR = "systemförvaltare",
  TECHNICAL_ADMINISTRATOR = "teknisk_förvaltare",
  IT_CONTACT = "it_kontakt",
  DPO = "dataskyddsombud",
}

export enum IntegrationType {
  API = "api",
  FILE_TRANSFER = "filöverföring",
  DB_REPLICATION = "databasreplikering",
  EVENT = "event",
  MANUAL = "manuell",
}

export enum NIS2Classification {
  ESSENTIAL = "väsentlig",
  IMPORTANT = "viktig",
  NOT_APPLICABLE = "ej_tillämplig",
}

// --- Modeller ---

export interface Organization {
  id: string
  name: string
  org_number: string | null
  org_type: OrganizationType
  parent_org_id: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface System {
  id: string
  organization_id: string
  name: string
  aliases: string | null
  description: string
  system_category: SystemCategory
  business_area: string | null

  criticality: Criticality
  has_elevated_protection: boolean
  security_protection: boolean
  nis2_applicable: boolean
  nis2_classification: NIS2Classification | null

  treats_personal_data: boolean
  treats_sensitive_data: boolean
  third_country_transfer: boolean

  hosting_model: string | null
  cloud_provider: string | null
  data_location_country: string | null
  product_name: string | null
  product_version: string | null

  lifecycle_status: LifecycleStatus
  deployment_date: string | null
  planned_decommission_date: string | null
  end_of_support_date: string | null

  backup_frequency: string | null
  rpo: string | null
  rto: string | null
  dr_plan_exists: boolean

  last_risk_assessment_date: string | null
  klassa_reference_id: string | null

  extended_attributes: Record<string, unknown> | null

  created_at: string
  updated_at: string
  last_reviewed_at: string | null
  last_reviewed_by: string | null
}

export interface Classification {
  id: string
  system_id: string
  confidentiality: number
  integrity: number
  availability: number
  traceability: number | null
  classified_by: string
  classified_at: string
  valid_until: string | null
  notes: string | null
}

export interface Owner {
  id: string
  system_id: string
  role: OwnerRole
  name: string
  email: string | null
  phone: string | null
  organization_id: string
  created_at: string
}

export interface Integration {
  id: string
  source_system_id: string
  target_system_id: string
  integration_type: IntegrationType
  data_types: string | null
  frequency: string | null
  description: string | null
  criticality: Criticality | null
  is_external: boolean
  external_party: string | null
  created_at: string
}

export interface SystemDetail extends System {
  classifications: Classification[]
  owners: Owner[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface SystemStats {
  total: number
  by_criticality: Record<string, number>
  by_lifecycle_status: Record<string, number>
  by_system_category: Record<string, number>
  nis2_count: number
}

// --- Sökparametrar ---

export interface SystemSearchParams {
  q?: string
  organization_id?: string
  system_category?: SystemCategory
  lifecycle_status?: LifecycleStatus
  criticality?: Criticality
  limit?: number
  offset?: number
}

export interface IntegrationSearchParams {
  system_id?: string
  integration_type?: IntegrationType
}

// --- Skapa-typer ---

export interface ClassificationCreate {
  system_id: string
  confidentiality: number
  integrity: number
  availability: number
  traceability?: number
  classified_by: string
  valid_until?: string
  notes?: string
}

export interface OwnerCreate {
  system_id: string
  organization_id: string
  role: OwnerRole
  name: string
  email?: string
  phone?: string
}
