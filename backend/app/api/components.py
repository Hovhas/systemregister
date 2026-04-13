from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Component
from app.schemas import (
    ComponentCreate, ComponentUpdate, ComponentResponse, PaginatedResponse,
)

router = APIRouter(prefix="/components", tags=["Komponent"])


@router.get("/", response_model=PaginatedResponse[ComponentResponse])
async def list_components(
    system_id: UUID | None = Query(None),
    organization_id: UUID | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    stmt = select(Component)
    if system_id:
        stmt = stmt.where(Component.system_id == system_id)
    if organization_id:
        stmt = stmt.where(Component.organization_id == organization_id)
    if q:
        stmt = stmt.where(Component.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Component.created_at.desc(), Component.id).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    comp = await db.get(Component, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Komponent hittades inte")
    return comp


@router.post("/", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(data: ComponentCreate, db: AsyncSession = Depends(get_rls_db)):
    comp = Component(**data.model_dump())
    db.add(comp)
    await db.flush()
    await db.refresh(comp)
    return comp


@router.patch("/{component_id}", response_model=ComponentResponse)
async def update_component(component_id: UUID, data: ComponentUpdate, db: AsyncSession = Depends(get_rls_db)):
    comp = await db.get(Component, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Komponent hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(comp, key, value)
    await db.flush()
    await db.refresh(comp)
    return comp


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(component_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    comp = await db.get(Component, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Komponent hittades inte")
    await db.delete(comp)
    await db.flush()
