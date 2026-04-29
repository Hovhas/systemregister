"""API för värdeströmmar (Paket A)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import ValueStream
from app.schemas import (
    ValueStreamCreate, ValueStreamUpdate, ValueStreamResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/value-streams", tags=["Värdeström"])


@router.get("/", response_model=PaginatedResponse[ValueStreamResponse])
async def list_value_streams(
    organization_id: UUID | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(ValueStream)
    if organization_id:
        base = base.where(ValueStream.organization_id == organization_id)
    if q:
        base = base.where(ValueStream.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(ValueStream.name, ValueStream.id)
        .offset(offset).limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{value_stream_id}", response_model=ValueStreamResponse)
async def get_value_stream(value_stream_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    vs = await db.get(ValueStream, value_stream_id)
    if not vs:
        raise HTTPException(status_code=404, detail="Värdeström hittades inte")
    return vs


@router.post("/", response_model=ValueStreamResponse, status_code=status.HTTP_201_CREATED)
async def create_value_stream(
    data: ValueStreamCreate, db: AsyncSession = Depends(get_rls_db),
):
    payload = data.model_dump()
    payload["stages"] = [s for s in payload.get("stages", [])]
    vs = ValueStream(**payload)
    db.add(vs)
    await db.flush()
    await db.refresh(vs)
    return vs


@router.patch("/{value_stream_id}", response_model=ValueStreamResponse)
async def update_value_stream(
    value_stream_id: UUID,
    data: ValueStreamUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    vs = await db.get(ValueStream, value_stream_id)
    if not vs:
        raise HTTPException(status_code=404, detail="Värdeström hittades inte")
    payload = data.model_dump(exclude_unset=True)
    if "stages" in payload and payload["stages"] is not None:
        payload["stages"] = [s for s in payload["stages"]]
    for key, value in payload.items():
        setattr(vs, key, value)
    await db.flush()
    await db.refresh(vs)
    return vs


@router.delete("/{value_stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_value_stream(
    value_stream_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    vs = await db.get(ValueStream, value_stream_id)
    if not vs:
        raise HTTPException(status_code=404, detail="Värdeström hittades inte")
    await db.delete(vs)
    await db.flush()
