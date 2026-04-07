from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import SafeStringMixin


# --- Classification ---

class ClassificationCreate(SafeStringMixin):
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
