"""
In-process event bus for system change events.

Listeners are registered at startup and called synchronously
after audit entries are created. Used for Metakatalog sync
and other integrations.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    SYSTEM_CREATED = "system.created"
    SYSTEM_UPDATED = "system.updated"
    SYSTEM_DELETED = "system.deleted"


@dataclass
class SystemEvent:
    event_type: EventType
    record_id: str
    table_name: str
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    changed_by: str | None = None


_listeners: list[Callable[[SystemEvent], None]] = []


def register_listener(fn: Callable[[SystemEvent], None]) -> None:
    """Register a listener that will be called on system events."""
    _listeners.append(fn)
    logger.info("Event listener registered: %s", fn.__name__)


def emit_event(event: SystemEvent) -> None:
    """Emit an event to all registered listeners."""
    for listener in _listeners:
        try:
            listener(event)
        except Exception:
            logger.exception("Event listener %s failed for %s", listener.__name__, event.event_type)
