from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import System
from app.models.models import GDPRTreatment
from app.schemas import GDPRTreatmentCreate, GDPRTreatmentUpdate, GDPRTreatmentResponse

router = APIRouter(tags=["GDPR"])


async def _get_system_or_404(system_id: UUID, db: AsyncSession) -> System:
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system


@router.post(
    "/systems/{system_id}/gdpr",
    response_model=GDPRTreatmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gdpr_treatment(
    system_id: UUID,
    data: GDPRTreatmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a GDPR treatment record linked to a system."""
    await _get_system_or_404(system_id, db)

    payload = data.model_dump()
    payload["system_id"] = system_id

    treatment = GDPRTreatment(**payload)
    db.add(treatment)
    await db.flush()
    await db.refresh(treatment)
    return treatment


@router.get(
    "/systems/{system_id}/gdpr",
    response_model=list[GDPRTreatmentResponse],
)
async def list_gdpr_treatments(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all GDPR treatment records for a system."""
    await _get_system_or_404(system_id, db)

    stmt = (
        select(GDPRTreatment)
        .where(GDPRTreatment.system_id == system_id)
        .order_by(GDPRTreatment.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/gdpr/{treatment_id}", response_model=GDPRTreatmentResponse)
async def update_gdpr_treatment(
    treatment_id: UUID,
    data: GDPRTreatmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a GDPR treatment record."""
    treatment = await db.get(GDPRTreatment, treatment_id)
    if not treatment:
        raise HTTPException(status_code=404, detail="GDPR treatment not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(treatment, key, value)

    await db.flush()
    await db.refresh(treatment)
    return treatment


@router.delete("/gdpr/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gdpr_treatment(
    treatment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a GDPR treatment record."""
    treatment = await db.get(GDPRTreatment, treatment_id)
    if not treatment:
        raise HTTPException(status_code=404, detail="GDPR treatment not found")
    await db.delete(treatment)
