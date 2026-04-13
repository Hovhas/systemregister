"""Webhook endpoints for external system integration."""
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rls import get_rls_db
from app.models.models import System

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class MetakatalogPayload(BaseModel):
    """Payload from Metakatalog webhook."""
    event: str  # "system.created" | "system.updated" | "system.deleted"
    metakatalog_id: str
    data: dict | None = None


@router.post("/metakatalog")
async def receive_metakatalog_webhook(
    payload: MetakatalogPayload,
    x_webhook_secret: str = Header(...),
    db: AsyncSession = Depends(get_rls_db),
):
    """Receive system sync events from Metakatalog.

    Security:
    - HMAC-validering FÖRST (fail fast innan feature-flag eller DB-anrop)
    - RLS via X-Organization-Id header (server-till-server, men isoleras per org)
    """
    settings = get_settings()

    # 1) Fail fast på signatur (innan feature-flag, innan DB-anrop)
    if not settings.metakatalog_webhook_secret or not hmac.compare_digest(
        x_webhook_secret, settings.metakatalog_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Ogiltig webhook-signatur")

    # 2) Feature-flag
    if not settings.metakatalog_enabled:
        raise HTTPException(status_code=404, detail="Metakatalog-integration ej aktiverad")

    logger.info("Metakatalog webhook: %s for %s", payload.event, payload.metakatalog_id)

    # Find system by metakatalog_id
    stmt = select(System).where(System.metakatalog_id == payload.metakatalog_id)
    result = await db.execute(stmt)
    system = result.scalar_one_or_none()

    if payload.event == "system.updated" and system and payload.data:
        # Update allowed fields from Metakatalog
        allowed = {"name", "description", "product_name", "product_version"}
        for key, value in payload.data.items():
            if key in allowed and hasattr(system, key):
                setattr(system, key, value)
        await db.commit()
        return {"status": "updated", "system_id": str(system.id)}

    if payload.event == "system.deleted" and system:
        logger.warning("Metakatalog delete event for %s — flagging only", system.name)
        return {"status": "acknowledged", "system_id": str(system.id)}

    return {"status": "ignored"}
