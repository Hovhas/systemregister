"""API för verksamhetsroller (Paket C)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import BusinessRole, RoleSystemAccess, System
from app.schemas import (
    BusinessRoleCreate, BusinessRoleUpdate, BusinessRoleResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/business-roles", tags=["Verksamhetsroll"])


def _serialize(role: BusinessRole, *, system_access_count: int = 0) -> dict[str, Any]:
    item = BusinessRoleResponse.model_validate(role).model_dump()
    item["system_access_count"] = system_access_count
    return item


@router.get("/", response_model=PaginatedResponse[BusinessRoleResponse])
async def list_business_roles(
    organization_id: UUID | None = Query(None),
    q: str | None = Query(None),
    include_counts: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(BusinessRole)
    if organization_id:
        base = base.where(BusinessRole.organization_id == organization_id)
    if q:
        base = base.where(BusinessRole.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(BusinessRole.name, BusinessRole.id).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    if not include_counts:
        return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)

    items: list[dict[str, Any]] = []
    for role in rows:
        ac = await db.scalar(
            select(func.count(RoleSystemAccess.id))
            .where(RoleSystemAccess.business_role_id == role.id)
        ) or 0
        items.append(_serialize(role, system_access_count=ac))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{role_id}", response_model=BusinessRoleResponse)
async def get_business_role(role_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    role = await db.get(BusinessRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Roll hittades inte")
    ac = await db.scalar(
        select(func.count(RoleSystemAccess.id))
        .where(RoleSystemAccess.business_role_id == role.id)
    ) or 0
    return _serialize(role, system_access_count=ac)


@router.post("/", response_model=BusinessRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_business_role(
    data: BusinessRoleCreate, db: AsyncSession = Depends(get_rls_db),
):
    role = BusinessRole(**data.model_dump())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


@router.patch("/{role_id}", response_model=BusinessRoleResponse)
async def update_business_role(
    role_id: UUID, data: BusinessRoleUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    role = await db.get(BusinessRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Roll hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(role, key, value)
    await db.flush()
    await db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_role(role_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    role = await db.get(BusinessRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Roll hittades inte")
    await db.delete(role)
    await db.flush()


@router.get("/{role_id}/systems")
async def list_role_systems(role_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    """Resolved access för en enskild roll."""
    role = await db.get(BusinessRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Roll hittades inte")
    stmt = (
        select(RoleSystemAccess, System)
        .join(System, System.id == RoleSystemAccess.system_id)
        .where(RoleSystemAccess.business_role_id == role_id)
        .order_by(System.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "access_id": str(access.id),
            "system_id": str(system.id),
            "system_name": system.name,
            "access_level": access.access_level.value,
            "access_type": access.access_type.value,
            "justification": access.justification,
        }
        for access, system in rows
    ]
