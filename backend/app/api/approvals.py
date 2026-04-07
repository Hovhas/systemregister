"""Arbetsflöden och godkännandeprocesser (FK-15)."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Approval
from app.models.enums import ApprovalStatus
from app.schemas import (
    ApprovalCreate, ApprovalReview, ApprovalResponse, PaginatedResponse,
)

router = APIRouter(prefix="/approvals", tags=["Godkännanden"])


@router.get("/", response_model=PaginatedResponse[ApprovalResponse])
async def list_approvals(
    organization_id: UUID | None = Query(None),
    status_filter: ApprovalStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    stmt = select(Approval)
    if organization_id:
        stmt = stmt.where(Approval.organization_id == organization_id)
    if status_filter:
        stmt = stmt.where(Approval.status == status_filter)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Approval.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)


@router.get("/pending/count")
async def pending_count(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_rls_db),
):
    """Antal väntande godkännanden — för dashboard-badge."""
    stmt = select(func.count()).select_from(Approval).where(Approval.status == ApprovalStatus.PENDING)
    if organization_id:
        stmt = stmt.where(Approval.organization_id == organization_id)
    count = await db.scalar(stmt) or 0
    return {"pending": count}


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Godkännande hittades inte")
    return approval


@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval(data: ApprovalCreate, db: AsyncSession = Depends(get_rls_db)):
    approval = Approval(**data.model_dump())
    db.add(approval)
    await db.flush()
    await db.refresh(approval)
    return approval


@router.post("/{approval_id}/review", response_model=ApprovalResponse)
async def review_approval(
    approval_id: UUID,
    data: ApprovalReview,
    db: AsyncSession = Depends(get_rls_db),
):
    """Godkänn, avvisa eller avbryt ett ärende."""
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Godkännande hittades inte")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Ärendet är redan {approval.status.value} och kan inte granskas igen",
        )
    approval.status = data.status
    approval.reviewed_by = data.reviewed_by
    approval.review_comment = data.review_comment
    approval.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(approval)
    return approval


@router.delete("/{approval_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_approval(approval_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Godkännande hittades inte")
    await db.delete(approval)
    await db.flush()
