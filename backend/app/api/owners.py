from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import System, SystemOwner
from app.schemas import OwnerCreate, OwnerUpdate, OwnerResponse

router = APIRouter(tags=["Owners"])


async def _get_system_or_404(system_id: UUID, db: AsyncSession) -> System:
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system


@router.post(
    "/systems/{system_id}/owners",
    response_model=OwnerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_owner(
    system_id: UUID,
    data: OwnerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an owner/role to a system."""
    await _get_system_or_404(system_id, db)

    payload = data.model_dump()
    payload["system_id"] = system_id  # path param takes precedence

    owner = SystemOwner(**payload)
    db.add(owner)
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ägare med samma roll och namn finns redan för detta system",
        )
    await db.refresh(owner)
    return owner


@router.get(
    "/systems/{system_id}/owners",
    response_model=list[OwnerResponse],
)
async def list_owners(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all owners/roles for a system."""
    await _get_system_or_404(system_id, db)

    stmt = (
        select(SystemOwner)
        .where(SystemOwner.system_id == system_id)
        .order_by(SystemOwner.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/owners/{owner_id}", response_model=OwnerResponse)
async def update_owner(
    owner_id: UUID,
    data: OwnerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an owner entry."""
    owner = await db.get(SystemOwner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(owner, key, value)

    await db.flush()
    await db.refresh(owner)
    return owner


@router.delete("/owners/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner(
    owner_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove an owner entry."""
    owner = await db.get(SystemOwner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    await db.delete(owner)
    await db.flush()
