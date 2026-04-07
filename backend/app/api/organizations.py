from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Organization
from app.schemas import OrganizationCreate, OrganizationUpdate, OrganizationResponse, SystemResponse

router = APIRouter(prefix="/organizations", tags=["Organisationer"])


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(db: AsyncSession = Depends(get_rls_db)):
    result = await db.execute(select(Organization).order_by(Organization.name))
    return result.scalars().all()


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation hittades inte")
    return org


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(data: OrganizationCreate, db: AsyncSession = Depends(get_rls_db)):
    org = Organization(**data.model_dump())
    db.add(org)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Organisation med detta org-nummer finns redan")
    await db.refresh(org)
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(org_id: UUID, data: OrganizationUpdate, db: AsyncSession = Depends(get_rls_db)):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(org, key, value)
    await db.flush()
    await db.refresh(org)
    return org


@router.get("/{org_id}/systems", response_model=list[SystemResponse])
async def list_organization_systems(org_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    """Hämta alla system för en organisation."""
    from app.models import System
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation hittades inte")
    result = await db.execute(
        select(System).where(System.organization_id == org_id).order_by(System.name)
    )
    return result.scalars().all()


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(org_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    from app.models import System

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation hittades inte")
    system_count = await db.scalar(
        select(func.count()).select_from(System).where(System.organization_id == org_id)
    )
    if system_count and system_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Kan inte radera organisation med {system_count} kopplade system"
        )
    await db.delete(org)
    await db.flush()
