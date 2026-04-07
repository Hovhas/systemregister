from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.enums import OwnerRole
from app.schemas.base import SafeStringMixin


# --- Owner ---

class OwnerCreate(SafeStringMixin):
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


class OwnerUpdate(SafeStringMixin):
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
