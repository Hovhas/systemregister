from uuid import UUID

from pydantic import BaseModel


# --- Notifications ---

class NotificationItem(BaseModel):
    """Enskild notifiering/varning."""
    type: str
    severity: str
    title: str
    description: str
    system_id: UUID
    record_id: UUID | None = None


class NotificationListResponse(BaseModel):
    """Paginerad lista av notifieringar med sammanfattning."""
    items: list[NotificationItem]
    total: int
    limit: int
    offset: int
    by_severity: dict[str, int]
