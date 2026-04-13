from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rls import get_rls_db
from app.models import System, SystemClassification, SystemOwner, GDPRTreatment, Objekt, Module, Component, InformationAsset, Approval
from app.models.enums import SystemCategory, LifecycleStatus, Criticality, AIRiskClass, ApprovalStatus
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
    stmt = stmt.order_by(System.created_at.desc(), System.id).offset(offset).limit(limit)
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
            selectinload(System.contracts),
            selectinload(System.integrations_out),
            selectinload(System.integrations_in),
            selectinload(System.objekt),
            selectinload(System.modules_used),
            selectinload(System.information_assets),
            selectinload(System.components),
        )
        .where(System.id == system_id)
    )
    result = await db.execute(stmt)
    system = result.scalar_one_or_none()
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    return system


@router.post("/", response_model=SystemResponse, status_code=status.HTTP_201_CREATED)
async def create_system(data: SystemCreate, db: AsyncSession = Depends(get_rls_db)):
    # FK-14: Dubbletthantering — varna vid liknande systemnamn
    similar_stmt = select(System.id, System.name).where(
        System.organization_id == data.organization_id,
        or_(
            System.name.ilike(data.name),
            func.similarity(System.name, data.name) > 0.4,
        ) if hasattr(func, 'similarity') else System.name.ilike(data.name),
    ).limit(5)
    try:
        similar_result = await db.execute(similar_stmt)
        duplicates = [{"id": str(row.id), "name": row.name} for row in similar_result.all()]
    except ProgrammingError:
        # pg_trgm inte installerad — fallback till exakt match
        await db.rollback()
        exact_stmt = select(System.id, System.name).where(
            System.organization_id == data.organization_id,
            System.name.ilike(data.name),
        ).limit(5)
        similar_result = await db.execute(exact_stmt)
        duplicates = [{"id": str(row.id), "name": row.name} for row in similar_result.all()]

    if duplicates:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"System med liknande namn finns redan ({len(duplicates)} träffar)",
                "duplicates": duplicates,
            },
        )

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
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
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
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
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

    # AI-användning
    uses_ai_count = await db.scalar(
        select(func.count()).select_from(System).where(
            System.uses_ai == True,
            *([System.organization_id == organization_id] if organization_id else [])
        )
    ) or 0

    ai_risk_stmt = (
        select(System.ai_risk_class, func.count())
        .where(System.uses_ai == True)  # noqa: E712
        .where(System.ai_risk_class.is_not(None))
        .group_by(System.ai_risk_class)
    )
    if organization_id:
        ai_risk_stmt = ai_risk_stmt.where(System.organization_id == organization_id)
    ai_risk_result = await db.execute(ai_risk_stmt)
    ai_by_risk_class = {str(row[0].value): row[1] for row in ai_risk_result.all()}

    # Klassningsstatus
    with_classification = await db.scalar(
        select(func.count()).select_from(
            select(System).where(System.classifications.any()).options(
                selectinload(System.classifications)
            ).subquery()
        )
    ) or 0
    without_classification = total - with_classification

    # Expired classifications — systems where most recent classification has valid_until < today
    from datetime import date as date_type
    today_date = date_type.today()
    expired_subq = (
        select(
            SystemClassification.system_id,
            func.max(SystemClassification.classified_at).label("latest"),
        )
        .group_by(SystemClassification.system_id)
        .subquery()
    )
    expired_cls_stmt = (
        select(func.count(func.distinct(SystemClassification.system_id)))
        .join(expired_subq, SystemClassification.system_id == expired_subq.c.system_id)
        .where(SystemClassification.classified_at == expired_subq.c.latest)
        .where(SystemClassification.valid_until.is_not(None))
        .where(SystemClassification.valid_until < today_date)
    )
    expired_classification = await db.scalar(expired_cls_stmt) or 0

    classification_stats = {
        "with_classification": with_classification,
        "without_classification": without_classification,
        "expired": expired_classification,
    }

    # GDPR-stats
    pub_agreement_count = await db.scalar(
        select(func.count(func.distinct(GDPRTreatment.system_id))).where(
            GDPRTreatment.processor_agreement_status.is_not(None)
        )
    ) or 0

    dpia_count = await db.scalar(
        select(func.count(func.distinct(GDPRTreatment.system_id))).where(
            GDPRTreatment.dpia_conducted == True  # noqa: E712
        )
    ) or 0

    gdpr_stats = {
        "pub_agreement_count": pub_agreement_count,
        "dpia_count": dpia_count,
    }

    # --- Entity counts (Objekt, Module, Component, InformationAsset, pending Approvals) ---
    org_filter_objekt = [Objekt.organization_id == organization_id] if organization_id else []
    org_filter_module = [Module.organization_id == organization_id] if organization_id else []
    org_filter_component = [Component.organization_id == organization_id] if organization_id else []
    org_filter_asset = [InformationAsset.organization_id == organization_id] if organization_id else []
    org_filter_approval = [Approval.organization_id == organization_id] if organization_id else []

    objekt_count = await db.scalar(
        select(func.count()).select_from(Objekt).where(*org_filter_objekt)
    ) or 0
    module_count = await db.scalar(
        select(func.count()).select_from(Module).where(*org_filter_module)
    ) or 0
    component_count = await db.scalar(
        select(func.count()).select_from(Component).where(*org_filter_component)
    ) or 0
    information_asset_count = await db.scalar(
        select(func.count()).select_from(InformationAsset).where(*org_filter_asset)
    ) or 0
    pending_approval_count = await db.scalar(
        select(func.count()).select_from(Approval).where(
            Approval.status == ApprovalStatus.PENDING,
            *org_filter_approval,
        )
    ) or 0

    return {
        "total_systems": total,
        "by_lifecycle_status": by_lifecycle,
        "by_criticality": by_criticality,
        "nis2_applicable_count": nis2_count,
        "treats_personal_data_count": gdpr_count,
        "uses_ai_count": uses_ai_count,
        "ai_by_risk_class": ai_by_risk_class,
        "classification_stats": classification_stats,
        "gdpr_stats": gdpr_stats,
        "objekt_count": objekt_count,
        "module_count": module_count,
        "information_asset_count": information_asset_count,
        "component_count": component_count,
        "pending_approval_count": pending_approval_count,
    }
