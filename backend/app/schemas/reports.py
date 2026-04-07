from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import NIS2Classification, Criticality


# --- Reports ---

class NIS2SystemEntry(BaseModel):
    """Single system entry in NIS2 report."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    nis2_classification: NIS2Classification | None
    criticality: Criticality
    last_risk_assessment_date: date | None
    has_gdpr_treatment: bool
    owner_names: list[str]


class NIS2ReportSummary(BaseModel):
    total: int
    without_classification: int
    without_risk_assessment: int


class NIS2ReportResponse(BaseModel):
    generated_at: datetime
    summary: NIS2ReportSummary
    systems: list[NIS2SystemEntry]


class ComplianceGaps(BaseModel):
    """Kategoriserade gap-listor — matchar faktisk API-respons från _get_compliance_gap_data."""
    missing_classification: list[dict]
    missing_owner: list[dict]
    personal_data_without_gdpr: list[dict]
    nis2_without_risk_assessment: list[dict]
    expiring_contracts: list[dict]


class ComplianceGapSummary(BaseModel):
    total_gaps: int


class ComplianceGapResponse(BaseModel):
    generated_at: datetime
    gaps: ComplianceGaps
    summary: ComplianceGapSummary
