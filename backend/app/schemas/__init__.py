from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import (
    OrganizationType, SystemCategory, LifecycleStatus, Criticality,
    OwnerRole, IntegrationType, NIS2Classification,
)


# --- Organization ---

class OrganizationCreate(BaseModel):
    name: str = Field(max_length=255)
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

class SystemCreate(BaseModel):
    organization_id: UUID
    name: str = Field(max_length=255)
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


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    confidentiality: int
    integrity: int
    availability: int
    traceability: int | None
    classified_by: str
    classified_at: datetime
    valid_until: date | None


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: OwnerRole
    name: str
    email: str | None
    phone: str | None
    organization_id: UUID


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
