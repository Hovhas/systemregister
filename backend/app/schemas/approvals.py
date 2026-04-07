from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import ApprovalStatus, ApprovalType
from app.schemas.base import SafeStringMixin


class ApprovalCreate(SafeStringMixin):
    organization_id: UUID
    approval_type: ApprovalType
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    target_table: str | None = Field(None, max_length=100)
    target_record_id: UUID | None = None
    proposed_changes: dict | None = None
    requested_by: str | None = Field(None, max_length=255)


class ApprovalReview(SafeStringMixin):
    status: ApprovalStatus  # godkänd / avvisad / avbruten
    reviewed_by: str = Field(min_length=1, max_length=255)
    review_comment: str | None = None


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    approval_type: ApprovalType
    status: ApprovalStatus
    title: str
    description: str | None
    target_table: str | None
    target_record_id: UUID | None
    proposed_changes: dict | None
    requested_by: str | None
    reviewed_by: str | None
    review_comment: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
