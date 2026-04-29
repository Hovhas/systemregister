"""API för befattningar (Paket C)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Position, OrgUnit
from app.schemas import (
    PositionCreate, PositionUpdate, PositionResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/positions", tags=["Befattning"])


@router.get("/", response_model=PaginatedResponse[PositionResponse])
async def list_positions(
    organization_id: UUID | None = Query(None),
    org_unit_id: UUID | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(Position)
    if organization_id:
        base = base.where(Position.organization_id == organization_id)
    if org_unit_id:
        base = base.where(Position.org_unit_id == org_unit_id)
    if q:
        base = base.where(Position.title.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = base.order_by(Position.title, Position.id).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(position_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    pos = await db.get(Position, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Befattning hittades inte")
    return pos


@router.post("/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(data: PositionCreate, db: AsyncSession = Depends(get_rls_db)):
    if data.org_unit_id:
        unit = await db.get(OrgUnit, data.org_unit_id)
        if not unit:
            raise HTTPException(status_code=422, detail="Organisationsenhet finns inte")
    pos = Position(**data.model_dump())
    db.add(pos)
    await db.flush()
    await db.refresh(pos)
    return pos


@router.patch("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID, data: PositionUpdate, db: AsyncSession = Depends(get_rls_db),
):
    pos = await db.get(Position, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Befattning hittades inte")
    payload = data.model_dump(exclude_unset=True)
    if "org_unit_id" in payload and payload["org_unit_id"]:
        unit = await db.get(OrgUnit, payload["org_unit_id"])
        if not unit:
            raise HTTPException(status_code=422, detail="Organisationsenhet finns inte")
    for key, value in payload.items():
        setattr(pos, key, value)
    await db.flush()
    await db.refresh(pos)
    return pos


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(position_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    pos = await db.get(Position, position_id)
    if not pos:
        raise HTTPException(status_code=404, detail="Befattning hittades inte")
    await db.delete(pos)
    await db.flush()
