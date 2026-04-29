"""Pydantic schemas för Paket C — rollkatalog och anställningsmallar (IGA)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AccessLevel, AccessType
from app.schemas.base import SafeStringMixin


# ============================================================
# BusinessRole
# ============================================================

class BusinessRoleCreate(SafeStringMixin):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    role_owner: str | None = Field(None, max_length=255)
    valid_from: date | None = None
    valid_until: date | None = None


class BusinessRoleUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    role_owner: str | None = Field(None, max_length=255)
    valid_from: date | None = None
    valid_until: date | None = None


class BusinessRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    role_owner: str | None
    valid_from: date | None
    valid_until: date | None
    created_at: datetime
    updated_at: datetime
    system_access_count: int | None = None


# ============================================================
# Position
# ============================================================

class PositionCreate(SafeStringMixin):
    organization_id: UUID
    org_unit_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    position_code: str | None = Field(None, max_length=100)
    description: str | None = None


class PositionUpdate(SafeStringMixin):
    org_unit_id: UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    position_code: str | None = Field(None, max_length=100)
    description: str | None = None


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    org_unit_id: UUID | None
    title: str
    position_code: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# RoleSystemAccess
# ============================================================

class RoleSystemAccessCreate(SafeStringMixin):
    business_role_id: UUID
    system_id: UUID
    access_level: AccessLevel
    access_type: AccessType = AccessType.BIRTHRIGHT
    justification: str | None = None
    approver_name: str | None = Field(None, max_length=255)
    approved_at: datetime | None = None


class RoleSystemAccessUpdate(SafeStringMixin):
    access_level: AccessLevel | None = None
    access_type: AccessType | None = None
    justification: str | None = None
    approver_name: str | None = Field(None, max_length=255)
    approved_at: datetime | None = None


class RoleSystemAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_role_id: UUID
    system_id: UUID
    access_level: AccessLevel
    access_type: AccessType
    justification: str | None
    approver_name: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# EmploymentTemplate
# ============================================================

class EmploymentTemplateCreate(SafeStringMixin):
    organization_id: UUID
    position_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(1, ge=1)
    is_active: bool = True
    approved_by: str | None = Field(None, max_length=255)
    approved_at: datetime | None = None
    notes: str | None = None
    role_ids: list[UUID] = Field(default_factory=list)


class EmploymentTemplateUpdate(SafeStringMixin):
    position_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    version: int | None = Field(None, ge=1)
    is_active: bool | None = None
    approved_by: str | None = Field(None, max_length=255)
    approved_at: datetime | None = None
    notes: str | None = None
    role_ids: list[UUID] | None = None


class EmploymentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    position_id: UUID | None
    name: str
    version: int
    is_active: bool
    approved_by: str | None
    approved_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    role_ids: list[UUID] = Field(default_factory=list)


class TemplateRoleLinkRequest(BaseModel):
    role_id: UUID


# ============================================================
# Resolved access (output från template_service)
# ============================================================

class ResolvedAccessEntry(BaseModel):
    system_id: UUID
    system_name: str
    access_level: AccessLevel
    access_type: AccessType
    contributing_role_names: list[str] = Field(default_factory=list)


class ResolvedAccessResponse(BaseModel):
    template_id: UUID
    template_name: str
    is_active: bool
    entries: list[ResolvedAccessEntry]
