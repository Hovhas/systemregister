from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AuditAction
from app.schemas.base import PaginatedResponse


# --- Audit ---

class AuditEntryResponse(BaseModel):
    """Enskild audit-logg-post."""
    id: UUID
    table_name: str
    record_id: UUID
    action: AuditAction
    changed_by: str | None
    changed_at: datetime | None
    old_values: dict | None
    new_values: dict | None
    ip_address: str | None = None


class AuditListResponse(PaginatedResponse[AuditEntryResponse]):
    """Paginerad lista av audit-poster."""
    pass
