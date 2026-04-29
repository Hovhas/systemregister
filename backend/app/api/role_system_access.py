"""API för roll→system-åtkomst (Paket C)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import BusinessRole, RoleSystemAccess, System
from app.schemas import (
    RoleSystemAccessCreate, RoleSystemAccessUpdate, RoleSystemAccessResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/role-access", tags=["Roll-åtkomst"])


@router.get("/", response_model=PaginatedResponse[RoleSystemAccessResponse])
async def list_role_access(
    business_role_id: UUID | None = Query(None),
    system_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(RoleSystemAccess)
    if business_role_id:
        base = base.where(RoleSystemAccess.business_role_id == business_role_id)
    if system_id:
        base = base.where(RoleSystemAccess.system_id == system_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(RoleSystemAccess.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{access_id}", response_model=RoleSystemAccessResponse)
async def get_role_access(access_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    access = await db.get(RoleSystemAccess, access_id)
    if not access:
        raise HTTPException(status_code=404, detail="Roll-åtkomst hittades inte")
    return access


@router.post(
    "/", response_model=RoleSystemAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_access(
    data: RoleSystemAccessCreate, db: AsyncSession = Depends(get_rls_db),
):
    role = await db.get(BusinessRole, data.business_role_id)
    if not role:
        raise HTTPException(status_code=422, detail="Roll finns inte")
    system = await db.get(System, data.system_id)
    if not system:
        raise HTTPException(status_code=422, detail="System finns inte")
    access = RoleSystemAccess(**data.model_dump())
    db.add(access)
    await db.flush()
    await db.refresh(access)
    return access


@router.patch("/{access_id}", response_model=RoleSystemAccessResponse)
async def update_role_access(
    access_id: UUID, data: RoleSystemAccessUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    access = await db.get(RoleSystemAccess, access_id)
    if not access:
        raise HTTPException(status_code=404, detail="Roll-åtkomst hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(access, key, value)
    await db.flush()
    await db.refresh(access)
    return access


@router.delete("/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_access(access_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    access = await db.get(RoleSystemAccess, access_id)
    if not access:
        raise HTTPException(status_code=404, detail="Roll-åtkomst hittades inte")
    await db.delete(access)
    await db.flush()
