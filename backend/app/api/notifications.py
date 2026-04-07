from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.schemas import NotificationListResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifieringar"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    """Returnerar aktiva varningar/notifieringar."""
    notifications = await NotificationService.generate_notifications(db)

    by_severity: dict[str, int] = {}
    for n in notifications:
        by_severity[n["severity"]] = by_severity.get(n["severity"], 0) + 1

    return {
        "items": notifications[offset:offset + limit],
        "total": len(notifications),
        "limit": limit,
        "offset": offset,
        "by_severity": by_severity,
    }
