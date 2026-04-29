"""Pydantic schemas för Paket A — verksamhetsskikt."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Criticality, OrgUnitType
from app.schemas.base import SafeStringMixin


# ============================================================
# BusinessCapability
# ============================================================

class CapabilityCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_capability_id: UUID | None = None
    capability_owner: str | None = Field(None, max_length=255)
    maturity_level: int | None = Field(None, ge=0, le=5)


class CapabilityUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    parent_capability_id: UUID | None = None
    capability_owner: str | None = Field(None, max_length=255)
    maturity_level: int | None = Field(None, ge=0, le=5)


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    parent_capability_id: UUID | None
    capability_owner: str | None
    maturity_level: int | None
    created_at: datetime
    updated_at: datetime
    system_count: int | None = None
    process_count: int | None = None
    children_count: int | None = None


# ============================================================
# BusinessProcess
# ============================================================

class ProcessCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_process_id: UUID | None = None
    process_owner: str | None = Field(None, max_length=255)
    criticality: Criticality | None = None


class ProcessUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    parent_process_id: UUID | None = None
    process_owner: str | None = Field(None, max_length=255)
    criticality: Criticality | None = None


class ProcessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    parent_process_id: UUID | None
    process_owner: str | None
    criticality: Criticality | None
    created_at: datetime
    updated_at: datetime
    system_count: int | None = None
    capability_count: int | None = None
    information_asset_count: int | None = None
    children_count: int | None = None


# ============================================================
# ValueStream
# ============================================================

class ValueStreamStage(BaseModel):
    """Etapp i en värdeström."""
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    order: int = Field(ge=0)


class ValueStreamCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    stages: list[ValueStreamStage] = Field(default_factory=list)


class ValueStreamUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    stages: list[ValueStreamStage] | None = None


class ValueStreamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    stages: list | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# OrgUnit
# ============================================================

class OrgUnitCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    parent_unit_id: UUID | None = None
    unit_type: OrgUnitType
    manager_name: str | None = Field(None, max_length=255)
    cost_center: str | None = Field(None, max_length=100)


class OrgUnitUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    parent_unit_id: UUID | None = None
    unit_type: OrgUnitType | None = None
    manager_name: str | None = Field(None, max_length=255)
    cost_center: str | None = Field(None, max_length=100)


class OrgUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    parent_unit_id: UUID | None
    unit_type: OrgUnitType
    manager_name: str | None
    cost_center: str | None
    created_at: datetime
    updated_at: datetime


class OrgUnitTreeNode(BaseModel):
    """Trädnod för hierarkivy. Children skapas rekursivt."""
    id: UUID
    name: str
    unit_type: OrgUnitType
    manager_name: str | None
    cost_center: str | None
    children: list["OrgUnitTreeNode"] = Field(default_factory=list)


OrgUnitTreeNode.model_rebuild()


# ============================================================
# Länkningsförfrågningar
# ============================================================

class SystemLinkRequest(BaseModel):
    system_id: UUID


class CapabilityLinkRequest(BaseModel):
    capability_id: UUID


class InformationAssetLinkBody(BaseModel):
    information_asset_id: UUID
