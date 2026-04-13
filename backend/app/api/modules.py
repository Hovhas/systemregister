from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Module, System, module_system_link
from app.schemas import (
    ModuleCreate, ModuleUpdate, ModuleResponse, ModuleLinkRequest, PaginatedResponse,
)

router = APIRouter(prefix="/modules", tags=["Modul"])


@router.get("/", response_model=PaginatedResponse[ModuleResponse])
async def list_modules(
    organization_id: UUID | None = Query(None),
    q: str | None = Query(None),
    include_counts: bool = Query(False, description="Inkludera systems_count per modul"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(Module)
    if organization_id:
        base = base.where(Module.organization_id == organization_id)
    if q:
        base = base.where(Module.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    if include_counts:
        systems_count_sq = (
            select(func.count(module_system_link.c.system_id))
            .where(module_system_link.c.module_id == Module.id)
            .correlate(Module)
            .scalar_subquery()
        )
        stmt = (
            base.add_columns(systems_count_sq.label("systems_count"))
            .order_by(Module.created_at.desc(), Module.id)
            .offset(offset)
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        items: list[dict[str, Any]] = []
        for mod, count in rows:
            item = ModuleResponse.model_validate(mod).model_dump()
            item["systems_count"] = count or 0
            items.append(item)
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    stmt = base.order_by(Module.created_at.desc(), Module.id).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)


@router.get("/{module_id}", response_model=ModuleResponse)
async def get_module(module_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modul hittades inte")
    return mod


@router.post("/", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(data: ModuleCreate, db: AsyncSession = Depends(get_rls_db)):
    mod = Module(**data.model_dump())
    db.add(mod)
    await db.flush()
    await db.refresh(mod)
    return mod


@router.patch("/{module_id}", response_model=ModuleResponse)
async def update_module(module_id: UUID, data: ModuleUpdate, db: AsyncSession = Depends(get_rls_db)):
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modul hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(mod, key, value)
    await db.flush()
    await db.refresh(mod)
    return mod


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modul hittades inte")
    await db.delete(mod)
    await db.flush()


# --- System-koppling (N:M) ---

@router.post("/{module_id}/systems", status_code=status.HTTP_201_CREATED)
async def link_module_to_system(module_id: UUID, data: ModuleLinkRequest, db: AsyncSession = Depends(get_rls_db)):
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modul hittades inte")
    system = await db.get(System, data.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    await db.execute(module_system_link.insert().values(module_id=module_id, system_id=data.system_id))
    await db.flush()
    return {"detail": "Modul kopplad till system"}


@router.delete("/{module_id}/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_module_from_system(module_id: UUID, system_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    result = await db.execute(
        module_system_link.delete().where(
            module_system_link.c.module_id == module_id,
            module_system_link.c.system_id == system_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()
