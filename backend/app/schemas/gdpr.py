from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import ProcessorAgreementStatus
from app.schemas.base import SafeStringMixin


# --- GDPRTreatment ---

class GDPRTreatmentCreate(SafeStringMixin):
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


class GDPRTreatmentUpdate(SafeStringMixin):
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
