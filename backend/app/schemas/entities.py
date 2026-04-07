from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import LifecycleStatus, AIRiskClass
from app.schemas.base import SafeStringMixin


# ============================================================
# Entitetshierarki — Objekt, Komponent, Modul, Informationsmängd
# ============================================================

# --- Objekt ---

class ObjektCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    object_owner: str | None = Field(None, max_length=255)
    object_leader: str | None = Field(None, max_length=255)


class ObjektUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    object_owner: str | None = Field(None, max_length=255)
    object_leader: str | None = Field(None, max_length=255)


class ObjektResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    object_owner: str | None
    object_leader: str | None
    created_at: datetime
    updated_at: datetime


# --- Komponent ---

class ComponentCreate(SafeStringMixin):
    system_id: UUID
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    component_type: str | None = Field(None, max_length=100)
    url: str | None = None
    business_area: str | None = Field(None, max_length=255)


class ComponentUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    component_type: str | None = Field(None, max_length=100)
    url: str | None = None
    business_area: str | None = Field(None, max_length=255)


class ComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    organization_id: UUID
    name: str
    description: str | None
    component_type: str | None
    url: str | None
    business_area: str | None
    created_at: datetime
    updated_at: datetime


# --- Modul ---

class ModuleCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    lifecycle_status: LifecycleStatus | None = None
    hosting_model: str | None = None
    product_name: str | None = Field(None, max_length=255)
    product_version: str | None = Field(None, max_length=100)
    uses_ai: bool = False
    ai_risk_class: AIRiskClass | None = None
    ai_usage_description: str | None = None


class ModuleUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    lifecycle_status: LifecycleStatus | None = None
    hosting_model: str | None = None
    product_name: str | None = Field(None, max_length=255)
    product_version: str | None = Field(None, max_length=100)
    uses_ai: bool | None = None
    ai_risk_class: AIRiskClass | None = None
    ai_usage_description: str | None = None


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    lifecycle_status: LifecycleStatus | None
    hosting_model: str | None
    product_name: str | None
    product_version: str | None
    uses_ai: bool
    ai_risk_class: AIRiskClass | None
    ai_usage_description: str | None
    created_at: datetime
    updated_at: datetime


class ModuleLinkRequest(BaseModel):
    """Koppla/koppla bort modul från system."""
    system_id: UUID


# --- Informationsmängd ---

class InformationAssetCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    information_owner: str | None = Field(None, max_length=255)
    confidentiality: int | None = Field(None, ge=0, le=4)
    integrity: int | None = Field(None, ge=0, le=4)
    availability: int | None = Field(None, ge=0, le=4)
    traceability: int | None = Field(None, ge=0, le=4)
    contains_personal_data: bool = False
    personal_data_type: str | None = Field(None, max_length=100)
    contains_public_records: bool = False
    ropa_reference_id: str | None = Field(None, max_length=100)
    # Kategori 15: Informationshantering
    ihp_reference: str | None = None
    preservation_class: str | None = Field(None, max_length=100)
    retention_period: str | None = Field(None, max_length=255)
    archive_responsible: str | None = Field(None, max_length=255)
    e_archive_delivery: str | None = Field(None, max_length=100)
    long_term_format: str | None = Field(None, max_length=255)
    last_ihp_review: date | None = None


class InformationAssetUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    information_owner: str | None = Field(None, max_length=255)
    confidentiality: int | None = Field(None, ge=0, le=4)
    integrity: int | None = Field(None, ge=0, le=4)
    availability: int | None = Field(None, ge=0, le=4)
    traceability: int | None = Field(None, ge=0, le=4)
    contains_personal_data: bool | None = None
    personal_data_type: str | None = Field(None, max_length=100)
    contains_public_records: bool | None = None
    ropa_reference_id: str | None = Field(None, max_length=100)
    ihp_reference: str | None = None
    preservation_class: str | None = Field(None, max_length=100)
    retention_period: str | None = Field(None, max_length=255)
    archive_responsible: str | None = Field(None, max_length=255)
    e_archive_delivery: str | None = Field(None, max_length=100)
    long_term_format: str | None = Field(None, max_length=255)
    last_ihp_review: date | None = None


class InformationAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    information_owner: str | None
    confidentiality: int | None
    integrity: int | None
    availability: int | None
    traceability: int | None
    contains_personal_data: bool
    personal_data_type: str | None
    contains_public_records: bool
    ropa_reference_id: str | None
    ihp_reference: str | None
    preservation_class: str | None
    retention_period: str | None
    archive_responsible: str | None
    e_archive_delivery: str | None
    long_term_format: str | None
    last_ihp_review: date | None
    created_at: datetime
    updated_at: datetime


class InformationAssetLinkRequest(BaseModel):
    """Koppla/koppla bort informationsmängd från system."""
    system_id: UUID
