from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from app.models.enums import (
    OrganizationType, SystemCategory, LifecycleStatus, Criticality,
    OwnerRole, IntegrationType, NIS2Classification, ProcessorAgreementStatus,
)


class SafeStringMixin(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_null_bytes_all_fields(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and "\x00" in value:
                    raise ValueError(f"Null-tecken (\\x00) är inte tillåtna i fältet '{key}'")
        return data


# --- Organization ---

class OrganizationCreate(SafeStringMixin):
    name: str = Field(min_length=1, max_length=255)
    org_number: str | None = Field(None, max_length=20)
    org_type: OrganizationType
    parent_org_id: UUID | None = None
    description: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    org_number: str | None = Field(None, max_length=20)
    org_type: OrganizationType | None = None
    parent_org_id: UUID | None = None
    description: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    org_number: str | None
    org_type: OrganizationType
    parent_org_id: UUID | None
    description: str | None
    created_at: datetime
    updated_at: datetime


# --- System ---

class SystemCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    aliases: str | None = None
    description: str
    system_category: SystemCategory
    business_area: str | None = None

    criticality: Criticality = Criticality.MEDIUM
    has_elevated_protection: bool = False
    security_protection: bool = False
    nis2_applicable: bool = False
    nis2_classification: NIS2Classification | None = None

    treats_personal_data: bool = False
    treats_sensitive_data: bool = False
    third_country_transfer: bool = False

    hosting_model: str | None = None
    cloud_provider: str | None = None
    data_location_country: str | None = "Sverige"
    product_name: str | None = None
    product_version: str | None = None

    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    deployment_date: date | None = None
    planned_decommission_date: date | None = None
    end_of_support_date: date | None = None

    backup_frequency: str | None = None
    rpo: str | None = None
    rto: str | None = None
    dr_plan_exists: bool = False

    last_risk_assessment_date: date | None = None
    klassa_reference_id: str | None = None

    extended_attributes: dict | None = None


class SystemUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    aliases: str | None = None
    description: str | None = None
    system_category: SystemCategory | None = None
    business_area: str | None = None
    criticality: Criticality | None = None
    has_elevated_protection: bool | None = None
    security_protection: bool | None = None
    nis2_applicable: bool | None = None
    nis2_classification: NIS2Classification | None = None
    treats_personal_data: bool | None = None
    treats_sensitive_data: bool | None = None
    third_country_transfer: bool | None = None
    hosting_model: str | None = None
    cloud_provider: str | None = None
    data_location_country: str | None = None
    product_name: str | None = None
    product_version: str | None = None
    lifecycle_status: LifecycleStatus | None = None
    deployment_date: date | None = None
    planned_decommission_date: date | None = None
    end_of_support_date: date | None = None
    backup_frequency: str | None = None
    rpo: str | None = None
    rto: str | None = None
    dr_plan_exists: bool | None = None
    last_risk_assessment_date: date | None = None
    klassa_reference_id: str | None = None
    extended_attributes: dict | None = None


class ClassificationCreate(BaseModel):
    system_id: UUID
    confidentiality: int = Field(ge=0, le=4)
    integrity: int = Field(ge=0, le=4)
    availability: int = Field(ge=0, le=4)
    traceability: int | None = Field(None, ge=0, le=4)
    classified_by: str = Field(min_length=1, max_length=255)
    valid_until: date | None = None
    notes: str | None = None


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    confidentiality: int
    integrity: int
    availability: int
    traceability: int | None
    classified_by: str
    classified_at: datetime
    valid_until: date | None
    notes: str | None


class OwnerCreate(SafeStringMixin):
    system_id: UUID
    organization_id: UUID
    role: OwnerRole
    name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_length(cls, v):
        if v is not None and len(v) > 255:
            raise ValueError("Email får inte överstiga 255 tecken")
        return v


class OwnerUpdate(BaseModel):
    role: OwnerRole | None = None
    name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    role: OwnerRole
    name: str
    email: str | None
    phone: str | None
    organization_id: UUID
    created_at: datetime


class IntegrationCreate(BaseModel):
    source_system_id: UUID
    target_system_id: UUID
    integration_type: IntegrationType
    data_types: str | None = None
    frequency: str | None = Field(None, max_length=100)
    description: str | None = None
    criticality: Criticality | None = None
    is_external: bool = False
    external_party: str | None = Field(None, max_length=255)


class IntegrationUpdate(BaseModel):
    integration_type: IntegrationType | None = None
    data_types: str | None = None
    frequency: str | None = Field(None, max_length=100)
    description: str | None = None
    criticality: Criticality | None = None
    is_external: bool | None = None
    external_party: str | None = Field(None, max_length=255)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_system_id: UUID
    target_system_id: UUID
    integration_type: IntegrationType
    data_types: str | None
    frequency: str | None
    description: str | None
    criticality: Criticality | None
    is_external: bool
    external_party: str | None
    created_at: datetime


class SystemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    aliases: str | None
    description: str
    system_category: SystemCategory
    business_area: str | None

    criticality: Criticality
    has_elevated_protection: bool
    security_protection: bool
    nis2_applicable: bool
    nis2_classification: NIS2Classification | None

    treats_personal_data: bool
    treats_sensitive_data: bool
    third_country_transfer: bool

    hosting_model: str | None
    cloud_provider: str | None
    data_location_country: str | None
    product_name: str | None
    product_version: str | None

    lifecycle_status: LifecycleStatus
    deployment_date: date | None
    planned_decommission_date: date | None
    end_of_support_date: date | None

    backup_frequency: str | None
    rpo: str | None
    rto: str | None
    dr_plan_exists: bool

    last_risk_assessment_date: date | None
    klassa_reference_id: str | None

    extended_attributes: dict | None

    created_at: datetime
    updated_at: datetime
    last_reviewed_at: datetime | None
    last_reviewed_by: str | None


class SystemDetailResponse(SystemResponse):
    """Systemrespons med inkluderade relationer."""
    classifications: list[ClassificationResponse] = []
    owners: list[OwnerResponse] = []


# --- Sök/filter ---

class SystemSearchParams(BaseModel):
    q: str | None = None  # Fritext
    organization_id: UUID | None = None
    system_category: SystemCategory | None = None
    lifecycle_status: LifecycleStatus | None = None
    criticality: Criticality | None = None
    nis2_applicable: bool | None = None
    treats_personal_data: bool | None = None
    limit: int = Field(default=50, le=200)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


# --- GDPRTreatment ---

class GDPRTreatmentCreate(BaseModel):
    ropa_reference_id: str | None = Field(None, max_length=100)
    data_categories: list[str] | None = None
    categories_of_data_subjects: str | None = None
    legal_basis: str | None = Field(None, max_length=255)
    data_processor: str | None = Field(None, max_length=255)
    processor_agreement_status: ProcessorAgreementStatus | None = None
    sub_processors: list[str] | None = None
    third_country_transfer_details: str | None = None
    retention_policy: str | None = None
    dpia_conducted: bool = False
    dpia_date: date | None = None
    dpia_link: str | None = None


class GDPRTreatmentUpdate(BaseModel):
    ropa_reference_id: str | None = Field(None, max_length=100)
    data_categories: list[str] | None = None
    categories_of_data_subjects: str | None = None
    legal_basis: str | None = Field(None, max_length=255)
    data_processor: str | None = Field(None, max_length=255)
    processor_agreement_status: ProcessorAgreementStatus | None = None
    sub_processors: list[str] | None = None
    third_country_transfer_details: str | None = None
    retention_policy: str | None = None
    dpia_conducted: bool | None = None
    dpia_date: date | None = None
    dpia_link: str | None = None


class GDPRTreatmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    ropa_reference_id: str | None
    data_categories: list[str] | None
    categories_of_data_subjects: str | None
    legal_basis: str | None
    data_processor: str | None
    processor_agreement_status: ProcessorAgreementStatus | None
    sub_processors: list[str] | None
    third_country_transfer_details: str | None
    retention_policy: str | None
    dpia_conducted: bool
    dpia_date: date | None
    dpia_link: str | None
    created_at: datetime
    updated_at: datetime


# --- Contract ---

class ContractCreate(SafeStringMixin):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_org_number: str | None = Field(None, max_length=20)
    contract_id_external: str | None = Field(None, max_length=100)
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renewal: bool = False
    notice_period_months: int | None = None
    sla_description: str | None = None
    license_model: str | None = Field(None, max_length=100)
    annual_license_cost: int | None = None
    annual_operations_cost: int | None = None
    procurement_type: str | None = Field(None, max_length=100)
    support_level: str | None = Field(None, max_length=255)


class ContractUpdate(BaseModel):
    supplier_name: str | None = Field(None, max_length=255)
    supplier_org_number: str | None = Field(None, max_length=20)
    contract_id_external: str | None = Field(None, max_length=100)
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renewal: bool | None = None
    notice_period_months: int | None = None
    sla_description: str | None = None
    license_model: str | None = Field(None, max_length=100)
    annual_license_cost: int | None = None
    annual_operations_cost: int | None = None
    procurement_type: str | None = Field(None, max_length=100)
    support_level: str | None = Field(None, max_length=255)


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    supplier_name: str
    supplier_org_number: str | None
    contract_id_external: str | None
    contract_start: date | None
    contract_end: date | None
    auto_renewal: bool
    notice_period_months: int | None
    sla_description: str | None
    license_model: str | None
    annual_license_cost: int | None
    annual_operations_cost: int | None
    procurement_type: str | None
    support_level: str | None
    created_at: datetime
    updated_at: datetime


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
    total_applicable: int
    without_classification: int
    without_risk_assessment: int


class NIS2ReportResponse(BaseModel):
    generated_at: datetime
    summary: NIS2ReportSummary
    systems: list[NIS2SystemEntry]


class ComplianceGapResponse(BaseModel):
    generated_at: datetime
    systems_without_classification: list[dict]
    systems_without_owner: list[dict]
    systems_with_personal_data_no_gdpr: list[dict]
    nis2_systems_without_risk_assessment: list[dict]
    contracts_expiring_soon: list[dict]
