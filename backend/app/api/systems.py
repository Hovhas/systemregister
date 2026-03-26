from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import System, SystemClassification, SystemOwner
from app.models.enums import SystemCategory, LifecycleStatus, Criticality
from app.schemas import (
    SystemCreate, SystemUpdate, SystemResponse, SystemDetailResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/systems", tags=["System"])


@router.get("/", response_model=PaginatedResponse)
async def list_systems(
    q: str | None = Query(None, description="Fritextsökning i namn och beskrivning"),
    organization_id: UUID | None = Query(None),
    system_category: SystemCategory | None = Query(None),
    lifecycle_status: LifecycleStatus | None = Query(None),
    criticality: Criticality | None = Query(None),
    nis2_applicable: bool | None = Query(None),
    treats_personal_data: bool | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(System)

    # Filters
    if q:
        search = f"%{q}%"
        stmt = stmt.where(
            or_(
                System.name.ilike(search),
                System.description.ilike(search),
                System.aliases.ilike(search),
                System.product_name.ilike(search),
            )
        )
    if organization_id:
        stmt = stmt.where(System.organization_id == organization_id)
    if system_category:
        stmt = stmt.where(System.system_category == system_category)
    if lifecycle_status:
        stmt = stmt.where(System.lifecycle_status == lifecycle_status)
    if criticality:
        stmt = stmt.where(System.criticality == criticality)
    if nis2_applicable is not None:
        stmt = stmt.where(System.nis2_applicable == nis2_applicable)
    if treats_personal_data is not None:
        stmt = stmt.where(System.treats_personal_data == treats_personal_data)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    stmt = stmt.order_by(System.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    systems = result.scalars().all()

    return PaginatedResponse(
        items=[SystemResponse.model_validate(s) for s in systems],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{system_id}", response_model=SystemDetailResponse)
async def get_system(system_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(System)
        .options(
            selectinload(System.classifications),
            selectinload(System.owners),
        )
        .where(System.id == system_id)
    )
    result = await db.execute(stmt)
    system = result.scalar_one_or_none()
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    return system


@router.post("/", response_model=SystemResponse, status_code=status.HTTP_201_CREATED)
async def create_system(data: SystemCreate, db: AsyncSession = Depends(get_db)):
    system = System(**data.model_dump())
    db.add(system)
    await db.flush()
    await db.refresh(system)
    return system


@router.patch("/{system_id}", response_model=SystemResponse)
async def update_system(system_id: UUID, data: SystemUpdate, db: AsyncSession = Depends(get_db)):
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(system, key, value)
    await db.flush()
    await db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system(system_id: UUID, db: AsyncSession = Depends(get_db)):
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    await db.delete(system)


# --- Dashboard/stats ---

@router.get("/stats/overview")
async def system_stats(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """KPI:er för dashboard."""
    base = select(System)
    if organization_id:
        base = base.where(System.organization_id == organization_id)

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    # Per livscykelstatus
    lifecycle_stmt = (
        select(System.lifecycle_status, func.count())
        .group_by(System.lifecycle_status)
    )
    if organization_id:
        lifecycle_stmt = lifecycle_stmt.where(System.organization_id == organization_id)
    lifecycle_result = await db.execute(lifecycle_stmt)
    by_lifecycle = {str(row[0].value): row[1] for row in lifecycle_result.all()}

    # Per kritikalitet
    crit_stmt = (
        select(System.criticality, func.count())
        .group_by(System.criticality)
    )
    if organization_id:
        crit_stmt = crit_stmt.where(System.organization_id == organization_id)
    crit_result = await db.execute(crit_stmt)
    by_criticality = {str(row[0].value): row[1] for row in crit_result.all()}

    # NIS2-flaggade
    nis2_count = await db.scalar(
        select(func.count()).select_from(System).where(
            System.nis2_applicable == True,
            *([System.organization_id == organization_id] if organization_id else [])
        )
    ) or 0

    # Personuppgifter
    gdpr_count = await db.scalar(
        select(func.count()).select_from(System).where(
            System.treats_personal_data == True,
            *([System.organization_id == organization_id] if organization_id else [])
        )
    ) or 0

    return {
        "total_systems": total,
        "by_lifecycle_status": by_lifecycle,
        "by_criticality": by_criticality,
        "nis2_applicable_count": nis2_count,
        "treats_personal_data_count": gdpr_count,
    }
