from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rls import get_rls_db
from app.models.models import AuditLog
from app.schemas import AuditListResponse, AuditEntryResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/", response_model=AuditListResponse)
async def list_audit_entries(
    table_name: str | None = Query(None),
    record_id: UUID | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    """Global ändringslogg med paginering och filter."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if table_name:
        stmt = stmt.where(AuditLog.table_name == table_name)
        count_stmt = count_stmt.where(AuditLog.table_name == table_name)
    if record_id:
        stmt = stmt.where(AuditLog.record_id == record_id)
        count_stmt = count_stmt.where(AuditLog.record_id == record_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.order_by(AuditLog.changed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return {
        "items": [
            {
                "id": str(e.id),
                "table_name": e.table_name,
                "record_id": str(e.record_id),
                "action": e.action.value if hasattr(e.action, "value") else e.action,
                "changed_by": e.changed_by,
                "changed_at": e.changed_at.isoformat() if e.changed_at else None,
                "old_values": e.old_values,
                "new_values": e.new_values,
                "ip_address": e.ip_address,
            }
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/record/{record_id}", response_model=list[AuditEntryResponse])
async def get_audit_for_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Ändringslogg för en specifik post (t.ex. ett system)."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.record_id == record_id)
        .order_by(AuditLog.changed_at.desc())
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "table_name": e.table_name,
            "record_id": str(e.record_id),
            "action": e.action.value if hasattr(e.action, "value") else e.action,
            "changed_by": e.changed_by,
            "changed_at": e.changed_at.isoformat() if e.changed_at else None,
            "old_values": e.old_values,
            "new_values": e.new_values,
        }
        for e in entries
    ]
