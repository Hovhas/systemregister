from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_or_404
from app.core.rls import get_rls_db
from app.models import SystemClassification
from app.schemas import ClassificationCreate, ClassificationResponse

router = APIRouter(tags=["Classifications"])


@router.post(
    "/systems/{system_id}/classifications",
    response_model=ClassificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_classification(
    system_id: UUID,
    data: ClassificationCreate,
    db: AsyncSession = Depends(get_rls_db),
):
    """Create a new classification entry for a system."""
    await get_system_or_404(system_id, db)

    payload = data.model_dump()
    payload["system_id"] = system_id  # path param takes precedence

    classification = SystemClassification(**payload)
    db.add(classification)
    await db.flush()
    await db.refresh(classification)

    # MSBFS 2020:7: Auto-flagga förhöjt skyddsbehov vid K/R/T >= 3
    if (
        classification.confidentiality >= 3
        or classification.integrity >= 3
        or classification.availability >= 3
    ):
        from app.models.models import System
        system = await db.get(System, system_id)
        if system and not system.has_elevated_protection:
            system.has_elevated_protection = True
            await db.flush()

    return classification


@router.get(
    "/systems/{system_id}/classifications",
    response_model=list[ClassificationResponse],
)
async def list_classifications(
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """List all classifications for a system, newest first."""
    await get_system_or_404(system_id, db)

    stmt = (
        select(SystemClassification)
        .where(SystemClassification.system_id == system_id)
        .order_by(SystemClassification.classified_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/systems/{system_id}/classifications/latest",
    response_model=ClassificationResponse,
)
async def get_latest_classification(
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Get the most recent classification for a system."""
    await get_system_or_404(system_id, db)

    stmt = (
        select(SystemClassification)
        .where(SystemClassification.system_id == system_id)
        .order_by(SystemClassification.classified_at.desc(), SystemClassification.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    classification = result.scalar_one_or_none()
    if not classification:
        raise HTTPException(status_code=404, detail="No classification found for this system")
    return classification
