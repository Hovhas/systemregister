from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Objekt
from app.schemas import (
    ObjektCreate, ObjektUpdate, ObjektResponse, PaginatedResponse,
)

router = APIRouter(prefix="/objekt", tags=["Objekt"])


@router.get("/", response_model=PaginatedResponse[ObjektResponse])
async def list_objekt(
    organization_id: UUID | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    stmt = select(Objekt)
    if organization_id:
        stmt = stmt.where(Objekt.organization_id == organization_id)
    if q:
        stmt = stmt.where(Objekt.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Objekt.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)


@router.get("/{objekt_id}", response_model=ObjektResponse)
async def get_objekt(objekt_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    obj = await db.get(Objekt, objekt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objekt hittades inte")
    return obj


@router.post("/", response_model=ObjektResponse, status_code=status.HTTP_201_CREATED)
async def create_objekt(data: ObjektCreate, db: AsyncSession = Depends(get_rls_db)):
    obj = Objekt(**data.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.patch("/{objekt_id}", response_model=ObjektResponse)
async def update_objekt(objekt_id: UUID, data: ObjektUpdate, db: AsyncSession = Depends(get_rls_db)):
    obj = await db.get(Objekt, objekt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objekt hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/{objekt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_objekt(objekt_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    obj = await db.get(Objekt, objekt_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Objekt hittades inte")
    await db.delete(obj)
    await db.flush()
