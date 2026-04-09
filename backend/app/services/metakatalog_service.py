"""
Metakatalog sync service.

Sends system changes to Metakatalog's API when enabled.
Registered as an event listener in the app lifespan.
"""
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.core.events import SystemEvent

logger = logging.getLogger(__name__)


def sync_to_metakatalog(event: SystemEvent) -> None:
    """Send a system change event to Metakatalog (fire-and-forget)."""
    settings = get_settings()
    if not settings.metakatalog_enabled or not settings.metakatalog_base_url:
        return

    try:
        # Synchronous call (runs in the after_flush context)
        with httpx.Client(timeout=5) as client:
            resp = client.post(
                f"{settings.metakatalog_base_url.rstrip('/')}/api/systems/sync",
                json={
                    "event": event.event_type.value,
                    "source": "systemregister",
                    "record_id": event.record_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": event.new_values,
                },
                headers={
                    "Authorization": f"Bearer {settings.metakatalog_api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            logger.info("Synced %s to Metakatalog: %s", event.record_id, resp.status_code)
    except Exception:
        logger.exception("Failed to sync %s to Metakatalog", event.record_id)
