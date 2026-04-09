from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import NIS2Classification, Criticality


# --- Reports ---

class NIS2SystemEntry(BaseModel):
    """Single system entry in NIS2 report."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    nis2_classification: NIS2Classification | None
    criticality: Criticality
    last_risk_assessment_date: date | None
    has_gdpr_treatment: bool
    owner_names: list[str]


class NIS2ReportSummary(BaseModel):
    total: int
    without_classification: int
    without_risk_assessment: int


class NIS2ReportResponse(BaseModel):
    generated_at: datetime
    summary: NIS2ReportSummary
    systems: list[NIS2SystemEntry]


class ComplianceGaps(BaseModel):
    """Kategoriserade gap-listor — matchar faktisk API-respons från _get_compliance_gap_data."""
    missing_classification: list[dict]
    missing_owner: list[dict]
    personal_data_without_gdpr: list[dict]
    nis2_without_risk_assessment: list[dict]
    expiring_contracts: list[dict]


class ComplianceGapSummary(BaseModel):
    total_gaps: int


class ComplianceGapResponse(BaseModel):
    generated_at: datetime
    gaps: ComplianceGaps
    summary: ComplianceGapSummary


# --- GDPR-rapport ---

class GDPRReportEntry(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    has_pub: bool
    has_dpia: bool
    third_country_transfer: bool
    missing_treatment: bool
    treatment_count: int


class GDPRReportSummary(BaseModel):
    total_personal_data_systems: int
    missing_pub_count: int
    missing_dpia_count: int
    third_country_count: int
    missing_treatment_count: int


class GDPRReportResponse(BaseModel):
    generated_at: datetime
    summary: GDPRReportSummary
    systems: list[GDPRReportEntry]


# --- AI-rapport ---

class AIReportEntry(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    ai_risk_class: str | None
    fria_status: str | None
    ai_transparency_fulfilled: bool
    ai_usage_description: str | None


class AIModuleEntry(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    ai_risk_class: str | None


class AIReportSummary(BaseModel):
    total_ai_systems: int
    by_risk_class: dict[str, int]
    missing_fria_count: int
    missing_transparency_count: int
    ai_modules_count: int


class AIReportResponse(BaseModel):
    generated_at: datetime
    summary: AIReportSummary
    systems: list[AIReportEntry]
    modules: list[AIModuleEntry]


# --- Klassningsstatus-rapport ---

class ClassificationReportEntry(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    has_classification: bool
    most_recent_date: str | None
    is_expired: bool


class ClassificationReportSummary(BaseModel):
    total_systems: int
    without_classification: int
    expired_count: int
    valid_count: int


class ClassificationReportResponse(BaseModel):
    generated_at: datetime
    summary: ClassificationReportSummary
    systems: list[ClassificationReportEntry]


# --- Livscykel-rapport ---

class LifecycleContractEntry(BaseModel):
    id: UUID
    system_id: UUID
    supplier_name: str
    contract_end: str
    days_remaining: int


class LifecycleSystemEntry(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    end_of_support_date: str | None = None
    days_remaining: int | None = None
    planned_decommission_date: str | None = None


class LifecycleReportSummary(BaseModel):
    expiring_contracts_30d: int
    expiring_contracts_90d: int
    expiring_contracts_180d: int
    end_of_support_count: int
    decommission_count: int


class LifecycleReportResponse(BaseModel):
    generated_at: datetime
    summary: LifecycleReportSummary
    contracts: list[LifecycleContractEntry]
    end_of_support_systems: list[LifecycleSystemEntry]
    decommissioning_systems: list[LifecycleSystemEntry]
