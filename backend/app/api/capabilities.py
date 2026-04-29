"""API för verksamhetsförmågor (Paket A)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import (
    BusinessCapability, System, BusinessProcess,
    capability_system_link, process_capability_link,
)
from app.schemas import (
    CapabilityCreate, CapabilityUpdate, CapabilityResponse,
    SystemLinkRequest, PaginatedResponse,
)

router = APIRouter(prefix="/capabilities", tags=["Verksamhetsförmåga"])


def _serialize(cap: BusinessCapability, *, system_count: int = 0,
               process_count: int = 0, children_count: int = 0) -> dict[str, Any]:
    item = CapabilityResponse.model_validate(cap).model_dump()
    item["system_count"] = system_count
    item["process_count"] = process_count
    item["children_count"] = children_count
    return item


@router.get("/", response_model=PaginatedResponse[CapabilityResponse])
async def list_capabilities(
    organization_id: UUID | None = Query(None),
    parent_capability_id: UUID | None = Query(None),
    only_top_level: bool = Query(False),
    q: str | None = Query(None),
    include_counts: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(BusinessCapability)
    if organization_id:
        base = base.where(BusinessCapability.organization_id == organization_id)
    if parent_capability_id:
        base = base.where(BusinessCapability.parent_capability_id == parent_capability_id)
    if only_top_level:
        base = base.where(BusinessCapability.parent_capability_id.is_(None))
    if q:
        base = base.where(BusinessCapability.name.ilike(f"%{q}%"))

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(BusinessCapability.name, BusinessCapability.id)
        .offset(offset).limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    if not include_counts:
        return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)

    items: list[dict[str, Any]] = []
    for cap in rows:
        sc = await db.scalar(
            select(func.count(capability_system_link.c.system_id))
            .where(capability_system_link.c.capability_id == cap.id)
        ) or 0
        pc = await db.scalar(
            select(func.count(process_capability_link.c.process_id))
            .where(process_capability_link.c.capability_id == cap.id)
        ) or 0
        cc = await db.scalar(
            select(func.count(BusinessCapability.id))
            .where(BusinessCapability.parent_capability_id == cap.id)
        ) or 0
        items.append(_serialize(cap, system_count=sc, process_count=pc, children_count=cc))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(capability_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    sc = await db.scalar(
        select(func.count(capability_system_link.c.system_id))
        .where(capability_system_link.c.capability_id == cap.id)
    ) or 0
    pc = await db.scalar(
        select(func.count(process_capability_link.c.process_id))
        .where(process_capability_link.c.capability_id == cap.id)
    ) or 0
    cc = await db.scalar(
        select(func.count(BusinessCapability.id))
        .where(BusinessCapability.parent_capability_id == cap.id)
    ) or 0
    return _serialize(cap, system_count=sc, process_count=pc, children_count=cc)


@router.post("/", response_model=CapabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_capability(data: CapabilityCreate, db: AsyncSession = Depends(get_rls_db)):
    if data.parent_capability_id:
        parent = await db.get(BusinessCapability, data.parent_capability_id)
        if not parent:
            raise HTTPException(status_code=422, detail="Parent-förmåga finns inte")
    cap = BusinessCapability(**data.model_dump())
    db.add(cap)
    await db.flush()
    await db.refresh(cap)
    return cap


@router.patch("/{capability_id}", response_model=CapabilityResponse)
async def update_capability(
    capability_id: UUID,
    data: CapabilityUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("parent_capability_id") == cap.id:
        raise HTTPException(status_code=422, detail="En förmåga kan inte vara förälder till sig själv")
    for key, value in payload.items():
        setattr(cap, key, value)
    await db.flush()
    await db.refresh(cap)
    return cap


@router.delete("/{capability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capability(capability_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    await db.delete(cap)
    await db.flush()


# --- System-koppling ---

@router.get("/{capability_id}/systems")
async def list_capability_systems(
    capability_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    stmt = (
        select(System)
        .join(capability_system_link, capability_system_link.c.system_id == System.id)
        .where(capability_system_link.c.capability_id == capability_id)
        .order_by(System.name)
    )
    systems = (await db.execute(stmt)).scalars().all()
    return [
        {"id": str(s.id), "name": s.name, "system_category": s.system_category.value}
        for s in systems
    ]


@router.post("/{capability_id}/systems", status_code=status.HTTP_201_CREATED)
async def link_capability_to_system(
    capability_id: UUID,
    data: SystemLinkRequest,
    db: AsyncSession = Depends(get_rls_db),
):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    system = await db.get(System, data.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    exists = await db.scalar(
        select(func.count())
        .select_from(capability_system_link)
        .where(
            capability_system_link.c.capability_id == capability_id,
            capability_system_link.c.system_id == data.system_id,
        )
    )
    if exists:
        return {"detail": "Förmåga redan kopplad till system"}
    await db.execute(
        capability_system_link.insert().values(
            capability_id=capability_id, system_id=data.system_id,
        )
    )
    await db.flush()
    return {"detail": "Förmåga kopplad till system"}


@router.delete(
    "/{capability_id}/systems/{system_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_capability_from_system(
    capability_id: UUID,
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    result = await db.execute(
        capability_system_link.delete().where(
            capability_system_link.c.capability_id == capability_id,
            capability_system_link.c.system_id == system_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()


# --- Process-koppling (vy) ---

@router.get("/{capability_id}/processes")
async def list_capability_processes(
    capability_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    cap = await db.get(BusinessCapability, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    stmt = (
        select(BusinessProcess)
        .join(
            process_capability_link,
            process_capability_link.c.process_id == BusinessProcess.id,
        )
        .where(process_capability_link.c.capability_id == capability_id)
        .order_by(BusinessProcess.name)
    )
    processes = (await db.execute(stmt)).scalars().all()
    return [{"id": str(p.id), "name": p.name} for p in processes]
