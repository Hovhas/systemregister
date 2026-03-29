from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rls import get_rls_db
from app.models import System, SystemClassification, SystemOwner
from app.models.enums import SystemCategory, LifecycleStatus, Criticality
from app.schemas import (
    SystemCreate, SystemUpdate, SystemResponse, SystemDetailResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/systems", tags=["System"])


def _escape_like(s: str) -> str:
    """Escapa LIKE-wildcards (% och _) i sokstrangar."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/", response_model=PaginatedResponse[SystemResponse])
async def list_systems(
    q: str | None = Query(None, description="Fritextsökning i namn och beskrivning"),
    organization_id: UUID | None = Query(None),
    system_category: SystemCategory | None = Query(None),
    lifecycle_status: LifecycleStatus | None = Query(None),
    criticality: Criticality | None = Query(None),
    nis2_applicable: bool | None = Query(None),
    treats_personal_data: bool | None = Query(None),
    hosting_model: str | None = Query(None, description="Filter på driftmodell (on-premise, cloud, hybrid)"),
    extended_search: str | None = Query(None, description="Sök i extended_attributes (JSONB)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    stmt = select(System)

    # Filters
    if q:
        # Sanitera söksträng — null bytes crashar PostgreSQL
        q_clean = q.replace("\x00", "")
        if not q_clean:
            # Söksträng bestod enbart av null bytes — returnera tomt resultat direkt
            return PaginatedResponse(items=[], total=0, limit=limit, offset=offset)
        search = f"%{_escape_like(q_clean)}%"
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
    if hosting_model:
        stmt = stmt.where(System.hosting_model == hosting_model)
    if extended_search:
        # Textsökning i JSONB — cast till text och sök med ILIKE
        stmt = stmt.where(
            cast(System.extended_attributes, String).ilike(f"%{_escape_like(extended_search)}%")
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    stmt = stmt.order_by(System.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    systems = result.scalars().all()

    return PaginatedResponse(
        items=systems,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{system_id}", response_model=SystemDetailResponse)
async def get_system(system_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    stmt = (
        select(System)
        .options(
            selectinload(System.classifications),
            selectinload(System.owners),
            selectinload(System.gdpr_treatments),
        )
        .where(System.id == system_id)
    )
    result = await db.execute(stmt)
    system = result.scalar_one_or_none()
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    return system


@router.post("/", response_model=SystemResponse, status_code=status.HTTP_201_CREATED)
# TODO(P1.1/P1.2): Apply org-context from auth token when auth is implemented.
# get_rls_db anropas men set_org_context() sätts inte — RLS blockerar eller
# tillåter allt beroende på null-bypass-policyn. Se migration 0003 och conftest.py.
async def create_system(data: SystemCreate, db: AsyncSession = Depends(get_rls_db)):
    system = System(**data.model_dump())
    db.add(system)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail="Organisationen finns inte eller databaskonflikt"
        )
    except ProgrammingError as e:
        await db.rollback()
        if "row-level security" in str(e).lower() or "insufficient_privilege" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="Åtkomst nekad: systemet tillhör en annan organisation"
            )
        raise
    await db.refresh(system)
    return system


@router.patch("/{system_id}", response_model=SystemResponse)
# TODO(P1.1/P1.2): Apply org-context from auth token when auth is implemented.
async def update_system(system_id: UUID, data: SystemUpdate, db: AsyncSession = Depends(get_rls_db)):
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(system, key, value)
    await db.flush()
    await db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
# TODO(P1.1/P1.2): Apply org-context from auth token when auth is implemented.
async def delete_system(system_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    # session.delete() triggar after_flush-listenern → audit_log
    # ON DELETE CASCADE i PostgreSQL hanterar barnrader (classifications, owners, etc.)
    await db.delete(system)
    await db.flush()


# --- Dashboard/stats ---

@router.get("/stats/overview")
async def system_stats(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_rls_db),
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
