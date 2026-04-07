from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import OrganizationType
from app.schemas.base import SafeStringMixin


# --- Organization ---

class OrganizationCreate(SafeStringMixin):
    name: str = Field(min_length=1, max_length=255)
    org_number: str | None = Field(None, max_length=20)
    org_type: OrganizationType
    parent_org_id: UUID | None = None
    description: str | None = None


class OrganizationUpdate(SafeStringMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
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
