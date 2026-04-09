from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import (
    SystemCategory, LifecycleStatus, Criticality,
    NIS2Classification, AIRiskClass, FRIAStatus,
)
from app.schemas.base import SafeStringMixin
from app.schemas.classifications import ClassificationResponse
from app.schemas.owners import OwnerResponse
from app.schemas.gdpr import GDPRTreatmentResponse


# --- System ---

class SystemCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    aliases: str | None = None
    description: str
    system_category: SystemCategory
    business_area: str | None = None
    business_processes: str | None = None

    criticality: Criticality = Criticality.MEDIUM
    has_elevated_protection: bool = False
    security_protection: bool = False
    nis2_applicable: bool = False
    nis2_classification: NIS2Classification | None = None
    encryption_at_rest: str | None = Field(None, max_length=255)
    encryption_in_transit: str | None = Field(None, max_length=255)
    access_control_model: str | None = Field(None, max_length=255)

    treats_personal_data: bool = False
    treats_sensitive_data: bool = False
    third_country_transfer: bool = False
    retention_rules: str | None = None

    hosting_model: str | None = None
    cloud_provider: str | None = None
    data_location_country: str | None = "Sverige"
    product_name: str | None = None
    product_version: str | None = None
    architecture_type: str | None = Field(None, max_length=100)
    environments: str | None = Field(None, max_length=255)

    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    deployment_date: date | None = None
    planned_decommission_date: date | None = None
    end_of_support_date: date | None = None
    last_major_upgrade: str | None = Field(None, max_length=255)
    next_planned_review: date | None = None

    backup_frequency: str | None = None
    rpo: str | None = None
    rto: str | None = None
    dr_plan_exists: bool = False
    backup_storage_location: str | None = Field(None, max_length=255)
    last_restore_test: str | None = Field(None, max_length=255)

    cost_center: str | None = Field(None, max_length=255)
    total_cost_of_ownership: int | None = Field(None, ge=0)

    documentation_links: list[str] | None = None

    last_risk_assessment_date: date | None = None
    klassa_reference_id: str | None = None
    linked_risks: str | None = None
    incident_history: str | None = None

    # Kategori 13: AI-förordningen
    uses_ai: bool = False
    ai_risk_class: AIRiskClass | None = None
    ai_usage_description: str | None = None
    fria_status: FRIAStatus | None = None
    fria_date: date | None = None
    fria_link: str | None = None
    ai_human_oversight: str | None = Field(None, max_length=255)
    ai_supplier: str | None = Field(None, max_length=255)
    ai_transparency_fulfilled: bool = False
    ai_model_version: str | None = Field(None, max_length=255)
    ai_last_review_date: date | None = None

    # Entitetshierarki
    objekt_id: UUID | None = None

    extended_attributes: dict | None = None

    # SBOM
    license_id: str | None = Field(None, max_length=100)
    cpe: str | None = Field(None, max_length=500)
    purl: str | None = Field(None, max_length=500)

    # Metakatalog
    metakatalog_id: str | None = None
    metakatalog_synced_at: datetime | None = None


class SystemUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    aliases: str | None = None
    description: str | None = None
    system_category: SystemCategory | None = None
    business_area: str | None = None
    business_processes: str | None = None
    criticality: Criticality | None = None
    has_elevated_protection: bool | None = None
    security_protection: bool | None = None
    nis2_applicable: bool | None = None
    nis2_classification: NIS2Classification | None = None
    encryption_at_rest: str | None = Field(None, max_length=255)
    encryption_in_transit: str | None = Field(None, max_length=255)
    access_control_model: str | None = Field(None, max_length=255)
    treats_personal_data: bool | None = None
    treats_sensitive_data: bool | None = None
    third_country_transfer: bool | None = None
    retention_rules: str | None = None
    hosting_model: str | None = None
    cloud_provider: str | None = None
    data_location_country: str | None = None
    product_name: str | None = None
    product_version: str | None = None
    architecture_type: str | None = Field(None, max_length=100)
    environments: str | None = Field(None, max_length=255)
    lifecycle_status: LifecycleStatus | None = None
    deployment_date: date | None = None
    planned_decommission_date: date | None = None
    end_of_support_date: date | None = None
    last_major_upgrade: str | None = Field(None, max_length=255)
    next_planned_review: date | None = None
    backup_frequency: str | None = None
    rpo: str | None = None
    rto: str | None = None
    dr_plan_exists: bool | None = None
    backup_storage_location: str | None = Field(None, max_length=255)
    last_restore_test: str | None = Field(None, max_length=255)
    cost_center: str | None = Field(None, max_length=255)
    total_cost_of_ownership: int | None = Field(None, ge=0)
    documentation_links: list[str] | None = None
    last_risk_assessment_date: date | None = None
    klassa_reference_id: str | None = None
    linked_risks: str | None = None
    incident_history: str | None = None
    # Kategori 13: AI-förordningen
    uses_ai: bool | None = None
    ai_risk_class: AIRiskClass | None = None
    ai_usage_description: str | None = None
    fria_status: FRIAStatus | None = None
    fria_date: date | None = None
    fria_link: str | None = None
    ai_human_oversight: str | None = Field(None, max_length=255)
    ai_supplier: str | None = Field(None, max_length=255)
    ai_transparency_fulfilled: bool | None = None
    ai_model_version: str | None = Field(None, max_length=255)
    ai_last_review_date: date | None = None
    # Entitetshierarki
    objekt_id: UUID | None = None
    extended_attributes: dict | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: datetime | None = None
    # SBOM
    license_id: str | None = Field(None, max_length=100)
    cpe: str | None = Field(None, max_length=500)
    purl: str | None = Field(None, max_length=500)

    # Metakatalog
    metakatalog_id: str | None = None
    metakatalog_synced_at: datetime | None = None


class SystemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    aliases: str | None
    description: str
    system_category: SystemCategory
    business_area: str | None
    business_processes: str | None

    criticality: Criticality
    has_elevated_protection: bool
    security_protection: bool
    nis2_applicable: bool
    nis2_classification: NIS2Classification | None
    encryption_at_rest: str | None
    encryption_in_transit: str | None
    access_control_model: str | None

    treats_personal_data: bool
    treats_sensitive_data: bool
    third_country_transfer: bool
    retention_rules: str | None

    hosting_model: str | None
    cloud_provider: str | None
    data_location_country: str | None
    product_name: str | None
    product_version: str | None
    architecture_type: str | None
    environments: str | None

    lifecycle_status: LifecycleStatus
    deployment_date: date | None
    planned_decommission_date: date | None
    end_of_support_date: date | None
    last_major_upgrade: str | None
    next_planned_review: date | None

    backup_frequency: str | None
    rpo: str | None
    rto: str | None
    dr_plan_exists: bool
    backup_storage_location: str | None
    last_restore_test: str | None

    cost_center: str | None
    total_cost_of_ownership: int | None

    documentation_links: list[str] | None

    last_risk_assessment_date: date | None
    klassa_reference_id: str | None
    linked_risks: str | None
    incident_history: str | None

    # Kategori 13: AI-förordningen
    uses_ai: bool
    ai_risk_class: AIRiskClass | None
    ai_usage_description: str | None
    fria_status: FRIAStatus | None
    fria_date: date | None
    fria_link: str | None
    ai_human_oversight: str | None
    ai_supplier: str | None
    ai_transparency_fulfilled: bool
    ai_model_version: str | None
    ai_last_review_date: date | None

    # Entitetshierarki
    objekt_id: UUID | None

    extended_attributes: dict | None

    # SBOM
    license_id: str | None
    cpe: str | None
    purl: str | None

    # Metakatalog
    metakatalog_id: str | None
    metakatalog_synced_at: datetime | None

    created_at: datetime
    updated_at: datetime
    last_reviewed_at: datetime | None
    last_reviewed_by: str | None


class SystemDetailResponse(SystemResponse):
    """Systemrespons med inkluderade relationer."""
    classifications: list[ClassificationResponse] = []
    owners: list[OwnerResponse] = []
    gdpr_treatments: list[GDPRTreatmentResponse] = []
