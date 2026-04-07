from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.schemas.base import SafeStringMixin


# --- Contract ---

class ContractCreate(SafeStringMixin):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_org_number: str | None = Field(None, max_length=20)
    contract_id_external: str | None = Field(None, max_length=100)
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renewal: bool = False
    notice_period_months: int | None = Field(None, ge=0)
    sla_description: str | None = None
    license_model: str | None = Field(None, max_length=100)
    annual_license_cost: int | None = Field(None, ge=0)
    annual_operations_cost: int | None = Field(None, ge=0)
    procurement_type: str | None = Field(None, max_length=100)
    support_level: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_contract_dates(self):
        """Kontrollera att contract_end inte är före contract_start."""
        if self.contract_start and self.contract_end:
            if self.contract_end < self.contract_start:
                raise ValueError("contract_end kan inte vara före contract_start")
        return self


class ContractUpdate(SafeStringMixin):
    supplier_name: str | None = Field(None, max_length=255)
    supplier_org_number: str | None = Field(None, max_length=20)
    contract_id_external: str | None = Field(None, max_length=100)
    contract_start: date | None = None
    contract_end: date | None = None
    auto_renewal: bool | None = None
    notice_period_months: int | None = Field(None, ge=0)
    sla_description: str | None = None
    license_model: str | None = Field(None, max_length=100)
    annual_license_cost: int | None = Field(None, ge=0)
    annual_operations_cost: int | None = Field(None, ge=0)
    procurement_type: str | None = Field(None, max_length=100)
    support_level: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_contract_dates(self):
        """Kontrollera att contract_end inte är före contract_start (båda måste anges)."""
        if self.contract_start and self.contract_end:
            if self.contract_end < self.contract_start:
                raise ValueError("contract_end kan inte vara före contract_start")
        return self


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_id: UUID
    supplier_name: str
    supplier_org_number: str | None
    contract_id_external: str | None
    contract_start: date | None
    contract_end: date | None
    auto_renewal: bool
    notice_period_months: int | None
    sla_description: str | None
    license_model: str | None
    annual_license_cost: int | None
    annual_operations_cost: int | None
    procurement_type: str | None
    support_level: str | None
    created_at: datetime
    updated_at: datetime
