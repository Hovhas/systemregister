"""
Audit trail via SQLAlchemy session-level event listeners.

Strategy: listen on Session "after_flush" which fires synchronously inside the
async flush cycle. At that point session.new / session.dirty / session.deleted
are still populated. We append AuditLog rows directly to the same session so
they are committed atomically with the original change.

Tracked models: Organization, System, SystemClassification, SystemOwner
Skipped: AuditLog itself (prevents recursion)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.enums import AuditAction

# Columns to exclude from serialisation — large / internal / already captured
_EXCLUDE_COLS: frozenset[str] = frozenset({"created_at", "updated_at"})

# Model table names that should be audited
_AUDITED_TABLES: frozenset[str] = frozenset(
    {"organizations", "systems", "system_classifications", "system_owners",
     "gdpr_treatments", "contracts", "system_integrations",
     "objekt", "components", "modules", "information_assets", "approvals"}
)


def _serialize_instance(instance: Any) -> dict[str, Any]:
    """Return a plain dict of column values for *instance*, JSON-safe."""
    mapper = inspect(type(instance))
    result: dict[str, Any] = {}
    for col in mapper.mapper.column_attrs:
        if col.key in _EXCLUDE_COLS:
            continue
        val = getattr(instance, col.key)
        # Convert non-JSON-native types
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif hasattr(val, "value"):
            # Enum members — store the .value string
            val = val.value
        elif isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, date):
            val = val.isoformat()
        result[col.key] = val
    return result


def _get_changed_fields(
    instance: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Return (old_values, new_values) containing only the columns that changed.
    Uses SQLAlchemy's history tracking (available during after_flush).
    """
    mapper = inspect(type(instance))
    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for col in mapper.mapper.column_attrs:
        if col.key in _EXCLUDE_COLS:
            continue
        history = inspect(instance).attrs[col.key].history
        if not history.has_changes():
            continue
        # history.deleted holds the previous value(s); history.added the new
        old_raw = history.deleted[0] if history.deleted else None
        new_raw = getattr(instance, col.key)

        def _to_json(val: Any) -> Any:
            if isinstance(val, uuid.UUID):
                return str(val)
            if hasattr(val, "value"):
                return val.value
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, date):
                return val.isoformat()
            return val

        old_values[col.key] = _to_json(old_raw)
        new_values[col.key] = _to_json(new_raw)

    return old_values, new_values


def _make_audit_entry(
    action: AuditAction,
    table_name: str,
    record_id: uuid.UUID,
    old_values: dict[str, Any] | None,
    new_values: dict[str, Any] | None,
) -> Any:
    """Construct an AuditLog instance (imported lazily to avoid circular imports)."""
    # Late import to avoid circular dependency at module load time
    from app.models.models import AuditLog  # noqa: PLC0415

    return AuditLog(
        id=uuid.uuid4(),
        table_name=table_name,
        record_id=record_id,
        action=action,
        changed_by=None,  # Placeholder until auth is implemented
        changed_at=datetime.now(timezone.utc),
        old_values=old_values or None,
        new_values=new_values or None,
        ip_address=None,
    )


def _handle_after_flush(session: Session, flush_context: Any) -> None:
    """
    Session-level after_flush handler.

    Runs synchronously inside the async flush. We collect audit entries for
    new / dirty / deleted objects and add them to the session. They will be
    written in the same transaction on the next flush (which SQLAlchemy
    triggers automatically when the session commits).
    """
    audit_entries: list[Any] = []

    # --- INSERT ---
    for obj in list(session.new):
        table_name = obj.__tablename__
        if table_name not in _AUDITED_TABLES:
            continue
        new_values = _serialize_instance(obj)
        entry = _make_audit_entry(
            action=AuditAction.CREATE,
            table_name=table_name,
            record_id=obj.id,
            old_values=None,
            new_values=new_values,
        )
        audit_entries.append(entry)

    # --- UPDATE ---
    for obj in list(session.dirty):
        table_name = obj.__tablename__
        if table_name not in _AUDITED_TABLES:
            continue
        if not session.is_modified(obj):
            continue
        old_values, new_values = _get_changed_fields(obj)
        if not new_values:
            # No tracked column actually changed
            continue
        entry = _make_audit_entry(
            action=AuditAction.UPDATE,
            table_name=table_name,
            record_id=obj.id,
            old_values=old_values,
            new_values=new_values,
        )
        audit_entries.append(entry)

    # --- DELETE ---
    for obj in list(session.deleted):
        table_name = obj.__tablename__
        if table_name not in _AUDITED_TABLES:
            continue
        old_values = _serialize_instance(obj)
        entry = _make_audit_entry(
            action=AuditAction.DELETE,
            table_name=table_name,
            record_id=obj.id,
            old_values=old_values,
            new_values=None,
        )
        audit_entries.append(entry)

    # Add all entries — SQLAlchemy will flush them in the next sub-flush
    for entry in audit_entries:
        session.add(entry)


def register_audit_listeners() -> None:
    """
    Attach the after_flush listener to the SQLAlchemy Session class.

    Call once at application startup (e.g. inside the FastAPI lifespan).
    Idempotent — safe to call multiple times (SQLAlchemy deduplicates).
    """
    event.listen(Session, "after_flush", _handle_after_flush)
