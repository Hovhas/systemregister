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

// AI-förordningen (EU 2024/1689)
export enum AIRiskClass {
  FORBIDDEN = "förbjuden",
  HIGH_RISK = "hög_risk",
  LIMITED_RISK = "begränsad_risk",
  MINIMAL_RISK = "minimal_risk",
  NOT_APPLICABLE = "ej_tillämplig",
}

export enum FRIAStatus {
  YES = "ja",
  NO = "nej",
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
  business_processes: string | null

  criticality: Criticality
  has_elevated_protection: boolean
  security_protection: boolean
  nis2_applicable: boolean
  nis2_classification: NIS2Classification | null
  encryption_at_rest: string | null
  encryption_in_transit: string | null
  access_control_model: string | null

  treats_personal_data: boolean
  treats_sensitive_data: boolean
  third_country_transfer: boolean
  retention_rules: string | null

  hosting_model: string | null
  cloud_provider: string | null
  data_location_country: string | null
  product_name: string | null
  product_version: string | null
  architecture_type: string | null
  environments: string | null

  lifecycle_status: LifecycleStatus
  deployment_date: string | null
  planned_decommission_date: string | null
  end_of_support_date: string | null
  last_major_upgrade: string | null
  next_planned_review: string | null

  backup_frequency: string | null
  rpo: string | null
  rto: string | null
  dr_plan_exists: boolean
  backup_storage_location: string | null
  last_restore_test: string | null

  cost_center: string | null
  total_cost_of_ownership: number | null

  documentation_links: string[] | null

  last_risk_assessment_date: string | null
  klassa_reference_id: string | null
  linked_risks: string | null
  incident_history: string | null

  // Kategori 13: AI-förordningen
  uses_ai: boolean
  ai_risk_class: AIRiskClass | null
  ai_usage_description: string | null
  fria_status: FRIAStatus | null
  fria_date: string | null
  fria_link: string | null
  ai_human_oversight: string | null
  ai_supplier: string | null
  ai_transparency_fulfilled: boolean
  ai_model_version: string | null
  ai_last_review_date: string | null

  // Entitetshierarki
  objekt_id: string | null

  extended_attributes: Record<string, unknown> | null

  // SBOM
  license_id: string | null
  cpe: string | null
  purl: string | null

  // Metakatalog
  metakatalog_id: string | null
  metakatalog_synced_at: string | null

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

// --- GDPR ---

export interface GDPRTreatment {
  id: string
  system_id: string
  ropa_reference_id: string | null
  data_categories: string[] | null
  categories_of_data_subjects: string | null
  legal_basis: string | null
  data_processor: string | null
  processor_agreement_status: string | null
  sub_processors: string[] | null
  third_country_transfer_details: string | null
  retention_policy: string | null
  dpia_conducted: boolean
  dpia_date: string | null
  dpia_link: string | null
  created_at: string
  updated_at: string
}

export interface GDPRTreatmentCreate {
  ropa_reference_id?: string
  data_categories?: string[]
  categories_of_data_subjects?: string
  legal_basis?: string
  data_processor?: string
  processor_agreement_status?: string
  retention_policy?: string
  dpia_conducted?: boolean
  dpia_date?: string
}

// --- Contract ---

export interface Contract {
  id: string
  system_id: string
  supplier_name: string
  supplier_org_number: string | null
  contract_id_external: string | null
  contract_start: string | null
  contract_end: string | null
  auto_renewal: boolean
  notice_period_months: number | null
  sla_description: string | null
  license_model: string | null
  annual_license_cost: number | null
  annual_operations_cost: number | null
  procurement_type: string | null
  support_level: string | null
  created_at: string
  updated_at: string
}

export interface ContractCreate {
  supplier_name: string
  contract_start?: string
  contract_end?: string
  auto_renewal?: boolean
  notice_period_months?: number
  sla_description?: string
  license_model?: string
  annual_license_cost?: number
  annual_operations_cost?: number
}

// --- System Create/Update ---

export interface SystemCreate {
  organization_id: string
  name: string
  description: string
  system_category: SystemCategory
  business_area?: string
  criticality?: Criticality
  lifecycle_status?: LifecycleStatus
  hosting_model?: string
  cloud_provider?: string
  nis2_applicable?: boolean
  treats_personal_data?: boolean
  // Grundinformation
  aliases?: string
  // Driftmiljö
  data_location_country?: string
  product_name?: string
  product_version?: string
  // Livscykel
  deployment_date?: string
  planned_decommission_date?: string
  end_of_support_date?: string
  // Backup och DR
  backup_frequency?: string
  rpo?: string
  rto?: string
  dr_plan_exists?: boolean
  // Compliance
  nis2_classification?: NIS2Classification
  treats_sensitive_data?: boolean
  third_country_transfer?: boolean
  has_elevated_protection?: boolean
  security_protection?: boolean
  last_risk_assessment_date?: string
  klassa_reference_id?: string
  // AI-förordningen
  uses_ai?: boolean
  ai_risk_class?: AIRiskClass
  ai_usage_description?: string
  fria_status?: FRIAStatus
  fria_date?: string
  fria_link?: string
  ai_human_oversight?: string
  ai_supplier?: string
  ai_transparency_fulfilled?: boolean
  ai_model_version?: string
  ai_last_review_date?: string
  // Entitetshierarki
  objekt_id?: string
  // SBOM
  license_id?: string
  cpe?: string
  purl?: string
}

export interface SystemUpdate {
  name?: string
  description?: string
  system_category?: SystemCategory
  business_area?: string
  criticality?: Criticality
  lifecycle_status?: LifecycleStatus
  hosting_model?: string
  cloud_provider?: string
  nis2_applicable?: boolean
  treats_personal_data?: boolean
  // Grundinformation
  aliases?: string
  // Driftmiljö
  data_location_country?: string
  product_name?: string
  product_version?: string
  // Livscykel
  deployment_date?: string
  planned_decommission_date?: string
  end_of_support_date?: string
  // Backup och DR
  backup_frequency?: string
  rpo?: string
  rto?: string
  dr_plan_exists?: boolean
  // Compliance
  nis2_classification?: NIS2Classification
  treats_sensitive_data?: boolean
  third_country_transfer?: boolean
  has_elevated_protection?: boolean
  security_protection?: boolean
  last_risk_assessment_date?: string
  klassa_reference_id?: string
  // AI-förordningen
  uses_ai?: boolean
  ai_risk_class?: AIRiskClass
  ai_usage_description?: string
  fria_status?: FRIAStatus
  fria_date?: string
  fria_link?: string
  ai_human_oversight?: string
  ai_supplier?: string
  ai_transparency_fulfilled?: boolean
  ai_model_version?: string
  ai_last_review_date?: string
  // Entitetshierarki
  objekt_id?: string | null
  // SBOM
  license_id?: string
  cpe?: string
  purl?: string
}

// --- Integration Create ---

export interface IntegrationCreate {
  source_system_id: string
  target_system_id: string
  integration_type: IntegrationType
  description?: string
  criticality?: Criticality
  frequency?: string
}

// --- Import ---

export interface ImportResult {
  imported: number
  errors: Array<{ row: number; error: string | object }>
}

export interface SystemDetail extends System {
  classifications: Classification[]
  owners: Owner[]
  integrations?: Integration[]
  gdpr_treatments?: GDPRTreatment[]
  contracts?: Contract[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface SystemStats {
  total_systems: number
  by_criticality: Record<string, number>
  by_lifecycle_status: Record<string, number>
  nis2_applicable_count: number
  treats_personal_data_count: number
  uses_ai_count: number
  ai_by_risk_class: Record<string, number>
  classification_stats: {
    with_classification: number
    without_classification: number
    expired: number
  }
  gdpr_stats: {
    pub_agreement_count: number
    dpia_count: number
  }
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
  sort_by?: string
  sort_dir?: "asc" | "desc"
}

export interface IntegrationSearchParams {
  system_id?: string
  integration_type?: IntegrationType
}

// --- Notifikationer ---

export interface Notification {
  type: string
  severity: "critical" | "warning" | "info"
  title: string
  description: string
  system_id?: string
  record_id?: string
}

export interface NotificationsResponse {
  items: Notification[]
  total: number
  limit: number
  offset: number
  by_severity: { critical: number; warning: number; info: number }
}

// --- Organisation Create/Update ---

export interface OrganizationCreate {
  name: string
  org_number?: string
  org_type: OrganizationType
  parent_org_id?: string
}

export interface OrganizationUpdate {
  name?: string
  org_number?: string
  org_type?: OrganizationType
  parent_org_id?: string | null
}

// --- Audit ---

export interface AuditEntry {
  id: string
  table_name: string
  record_id: string
  action: "INSERT" | "UPDATE" | "DELETE"
  changed_by: string | null
  changed_at: string
  old_values: Record<string, unknown> | null
  new_values: Record<string, unknown> | null
}

export interface AuditResponse {
  items: AuditEntry[]
  total: number
  limit: number
  offset: number
}

// --- Utgående avtal ---

export interface ExpiringContract {
  id: string
  system_id: string
  system_name: string
  supplier_name: string
  contract_end: string
  days_remaining: number
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

// ============================================================
// Entitetshierarki
// ============================================================

// --- Objekt ---
export interface Objekt {
  id: string
  organization_id: string
  name: string
  description: string | null
  object_owner: string | null
  object_leader: string | null
  created_at: string
  updated_at: string
}
export interface ObjektCreate {
  organization_id: string
  name: string
  description?: string
  object_owner?: string
  object_leader?: string
}
export interface ObjektUpdate {
  name?: string
  description?: string
  object_owner?: string
  object_leader?: string
}

// --- Komponent ---
export interface Component {
  id: string
  system_id: string
  organization_id: string
  name: string
  description: string | null
  component_type: string | null
  url: string | null
  business_area: string | null
  created_at: string
  updated_at: string
}
export interface ComponentCreate {
  system_id: string
  organization_id: string
  name: string
  description?: string
  component_type?: string
  url?: string
  business_area?: string
}

// --- Modul ---
export interface Module {
  id: string
  organization_id: string
  name: string
  description: string | null
  lifecycle_status: LifecycleStatus | null
  hosting_model: string | null
  product_name: string | null
  product_version: string | null
  uses_ai: boolean
  ai_risk_class: AIRiskClass | null
  ai_usage_description: string | null
  // SBOM
  license_id: string | null
  cpe: string | null
  purl: string | null
  supplier: string | null
  created_at: string
  updated_at: string
}
export interface ModuleCreate {
  organization_id: string
  name: string
  description?: string
  lifecycle_status?: LifecycleStatus
  hosting_model?: string
  product_name?: string
  product_version?: string
  uses_ai?: boolean
  ai_risk_class?: AIRiskClass
  ai_usage_description?: string
  // SBOM
  license_id?: string
  cpe?: string
  purl?: string
  supplier?: string
}

// --- Informationsmängd ---
export interface InformationAsset {
  id: string
  organization_id: string
  name: string
  description: string | null
  information_owner: string | null
  confidentiality: number | null
  integrity: number | null
  availability: number | null
  traceability: number | null
  contains_personal_data: boolean
  personal_data_type: string | null
  contains_public_records: boolean
  ropa_reference_id: string | null
  ihp_reference: string | null
  preservation_class: string | null
  retention_period: string | null
  archive_responsible: string | null
  e_archive_delivery: string | null
  long_term_format: string | null
  last_ihp_review: string | null
  created_at: string
  updated_at: string
}
// --- Godkännanden (FK-15) ---

export enum ApprovalStatus {
  PENDING = "väntande",
  APPROVED = "godkänd",
  REJECTED = "avvisad",
  CANCELLED = "avbruten",
}

export enum ApprovalType {
  SYSTEM_REGISTRATION = "systemregistrering",
  SYSTEM_DECOMMISSION = "avveckling",
  CLASSIFICATION_CHANGE = "klassningsändring",
  GDPR_TREATMENT = "gdpr_behandling",
  DATA_CHANGE = "dataändring",
}

export interface Approval {
  id: string
  organization_id: string
  approval_type: ApprovalType
  status: ApprovalStatus
  title: string
  description: string | null
  target_table: string | null
  target_record_id: string | null
  proposed_changes: Record<string, unknown> | null
  requested_by: string | null
  reviewed_by: string | null
  review_comment: string | null
  created_at: string
  updated_at: string
  reviewed_at: string | null
}

export interface ApprovalCreate {
  organization_id: string
  approval_type: ApprovalType
  title: string
  description?: string
  target_table?: string
  target_record_id?: string
  proposed_changes?: Record<string, unknown>
  requested_by?: string
}

export interface ApprovalReview {
  status: ApprovalStatus
  reviewed_by: string
  review_comment?: string
}

export interface InformationAssetCreate {
  organization_id: string
  name: string
  description?: string
  information_owner?: string
  confidentiality?: number
  integrity?: number
  availability?: number
  traceability?: number
  contains_personal_data?: boolean
  personal_data_type?: string
  contains_public_records?: boolean
  ropa_reference_id?: string
  ihp_reference?: string
  preservation_class?: string
  retention_period?: string
  archive_responsible?: string
  e_archive_delivery?: string
  long_term_format?: string
  last_ihp_review?: string
}
