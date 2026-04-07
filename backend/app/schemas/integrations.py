from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import IntegrationType, Criticality
from app.schemas.base import SafeStringMixin


# --- Integration ---

class IntegrationCreate(SafeStringMixin):
    source_system_id: UUID
    target_system_id: UUID
    integration_type: IntegrationType
    data_types: str | None = None
    frequency: str | None = Field(None, max_length=100)
    description: str | None = None
    criticality: Criticality | None = None
    is_external: bool = False
    external_party: str | None = Field(None, max_length=255)


class IntegrationUpdate(SafeStringMixin):
    integration_type: IntegrationType | None = None
    data_types: str | None = None
    frequency: str | None = Field(None, max_length=100)
    description: str | None = None
    criticality: Criticality | None = None
    is_external: bool | None = None
    external_party: str | None = Field(None, max_length=255)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_system_id: UUID
    target_system_id: UUID
    integration_type: IntegrationType
    data_types: str | None
    frequency: str | None
    description: str | None
    criticality: Criticality | None
    is_external: bool
    external_party: str | None
    created_at: datetime
