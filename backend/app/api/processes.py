"""API för verksamhetsprocesser (Paket A)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import (
    BusinessProcess, BusinessCapability, System, InformationAsset,
    process_system_link, process_capability_link, process_information_link,
)
from app.schemas import (
    ProcessCreate, ProcessUpdate, ProcessResponse,
    SystemLinkRequest, CapabilityLinkRequest, InformationAssetLinkBody,
    PaginatedResponse,
)

router = APIRouter(prefix="/processes", tags=["Verksamhetsprocess"])


def _serialize(
    proc: BusinessProcess, *,
    system_count: int = 0, capability_count: int = 0,
    information_asset_count: int = 0, children_count: int = 0,
) -> dict[str, Any]:
    item = ProcessResponse.model_validate(proc).model_dump()
    item["system_count"] = system_count
    item["capability_count"] = capability_count
    item["information_asset_count"] = information_asset_count
    item["children_count"] = children_count
    return item


@router.get("/", response_model=PaginatedResponse[ProcessResponse])
async def list_processes(
    organization_id: UUID | None = Query(None),
    parent_process_id: UUID | None = Query(None),
    only_top_level: bool = Query(False),
    q: str | None = Query(None),
    include_counts: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(BusinessProcess)
    if organization_id:
        base = base.where(BusinessProcess.organization_id == organization_id)
    if parent_process_id:
        base = base.where(BusinessProcess.parent_process_id == parent_process_id)
    if only_top_level:
        base = base.where(BusinessProcess.parent_process_id.is_(None))
    if q:
        base = base.where(BusinessProcess.name.ilike(f"%{q}%"))

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(BusinessProcess.name, BusinessProcess.id)
        .offset(offset).limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    if not include_counts:
        return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)

    items: list[dict[str, Any]] = []
    for proc in rows:
        sc = await db.scalar(
            select(func.count(process_system_link.c.system_id))
            .where(process_system_link.c.process_id == proc.id)
        ) or 0
        cc_caps = await db.scalar(
            select(func.count(process_capability_link.c.capability_id))
            .where(process_capability_link.c.process_id == proc.id)
        ) or 0
        ic = await db.scalar(
            select(func.count(process_information_link.c.information_asset_id))
            .where(process_information_link.c.process_id == proc.id)
        ) or 0
        cc_children = await db.scalar(
            select(func.count(BusinessProcess.id))
            .where(BusinessProcess.parent_process_id == proc.id)
        ) or 0
        items.append(_serialize(
            proc,
            system_count=sc, capability_count=cc_caps,
            information_asset_count=ic, children_count=cc_children,
        ))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(process_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    sc = await db.scalar(
        select(func.count(process_system_link.c.system_id))
        .where(process_system_link.c.process_id == proc.id)
    ) or 0
    cc_caps = await db.scalar(
        select(func.count(process_capability_link.c.capability_id))
        .where(process_capability_link.c.process_id == proc.id)
    ) or 0
    ic = await db.scalar(
        select(func.count(process_information_link.c.information_asset_id))
        .where(process_information_link.c.process_id == proc.id)
    ) or 0
    cc_children = await db.scalar(
        select(func.count(BusinessProcess.id))
        .where(BusinessProcess.parent_process_id == proc.id)
    ) or 0
    return _serialize(
        proc,
        system_count=sc, capability_count=cc_caps,
        information_asset_count=ic, children_count=cc_children,
    )


@router.post("/", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(data: ProcessCreate, db: AsyncSession = Depends(get_rls_db)):
    if data.parent_process_id:
        parent = await db.get(BusinessProcess, data.parent_process_id)
        if not parent:
            raise HTTPException(status_code=422, detail="Parent-process finns inte")
    proc = BusinessProcess(**data.model_dump())
    db.add(proc)
    await db.flush()
    await db.refresh(proc)
    return proc


@router.patch("/{process_id}", response_model=ProcessResponse)
async def update_process(
    process_id: UUID,
    data: ProcessUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("parent_process_id") == proc.id:
        raise HTTPException(status_code=422, detail="En process kan inte vara förälder till sig själv")
    for key, value in payload.items():
        setattr(proc, key, value)
    await db.flush()
    await db.refresh(proc)
    return proc


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process(process_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    await db.delete(proc)
    await db.flush()


# --- Länkar: system ---

@router.get("/{process_id}/systems")
async def list_process_systems(process_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    stmt = (
        select(System)
        .join(process_system_link, process_system_link.c.system_id == System.id)
        .where(process_system_link.c.process_id == process_id)
        .order_by(System.name)
    )
    systems = (await db.execute(stmt)).scalars().all()
    return [
        {"id": str(s.id), "name": s.name, "system_category": s.system_category.value}
        for s in systems
    ]


@router.post("/{process_id}/systems", status_code=status.HTTP_201_CREATED)
async def link_process_to_system(
    process_id: UUID,
    data: SystemLinkRequest,
    db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    system = await db.get(System, data.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    exists = await db.scalar(
        select(func.count())
        .select_from(process_system_link)
        .where(
            process_system_link.c.process_id == process_id,
            process_system_link.c.system_id == data.system_id,
        )
    )
    if exists:
        return {"detail": "Process redan kopplad till system"}
    await db.execute(
        process_system_link.insert().values(
            process_id=process_id, system_id=data.system_id,
        )
    )
    await db.flush()
    return {"detail": "Process kopplad till system"}


@router.delete(
    "/{process_id}/systems/{system_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_process_from_system(
    process_id: UUID,
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    result = await db.execute(
        process_system_link.delete().where(
            process_system_link.c.process_id == process_id,
            process_system_link.c.system_id == system_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()


# --- Länkar: capability ---

@router.get("/{process_id}/capabilities")
async def list_process_capabilities(
    process_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    stmt = (
        select(BusinessCapability)
        .join(
            process_capability_link,
            process_capability_link.c.capability_id == BusinessCapability.id,
        )
        .where(process_capability_link.c.process_id == process_id)
        .order_by(BusinessCapability.name)
    )
    caps = (await db.execute(stmt)).scalars().all()
    return [{"id": str(c.id), "name": c.name} for c in caps]


@router.post("/{process_id}/capabilities", status_code=status.HTTP_201_CREATED)
async def link_process_to_capability(
    process_id: UUID,
    data: CapabilityLinkRequest,
    db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    cap = await db.get(BusinessCapability, data.capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail="Förmåga hittades inte")
    exists = await db.scalar(
        select(func.count())
        .select_from(process_capability_link)
        .where(
            process_capability_link.c.process_id == process_id,
            process_capability_link.c.capability_id == data.capability_id,
        )
    )
    if exists:
        return {"detail": "Process redan kopplad till förmåga"}
    await db.execute(
        process_capability_link.insert().values(
            process_id=process_id, capability_id=data.capability_id,
        )
    )
    await db.flush()
    return {"detail": "Process kopplad till förmåga"}


@router.delete(
    "/{process_id}/capabilities/{capability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_process_from_capability(
    process_id: UUID,
    capability_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    result = await db.execute(
        process_capability_link.delete().where(
            process_capability_link.c.process_id == process_id,
            process_capability_link.c.capability_id == capability_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()


# --- Länkar: information_asset ---

@router.get("/{process_id}/information-assets")
async def list_process_information_assets(
    process_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    stmt = (
        select(InformationAsset)
        .join(
            process_information_link,
            process_information_link.c.information_asset_id == InformationAsset.id,
        )
        .where(process_information_link.c.process_id == process_id)
        .order_by(InformationAsset.name)
    )
    assets = (await db.execute(stmt)).scalars().all()
    return [{"id": str(a.id), "name": a.name} for a in assets]


@router.post("/{process_id}/information-assets", status_code=status.HTTP_201_CREATED)
async def link_process_to_information_asset(
    process_id: UUID,
    data: InformationAssetLinkBody,
    db: AsyncSession = Depends(get_rls_db),
):
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Process hittades inte")
    asset = await db.get(InformationAsset, data.information_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Informationsmängd hittades inte")
    exists = await db.scalar(
        select(func.count())
        .select_from(process_information_link)
        .where(
            process_information_link.c.process_id == process_id,
            process_information_link.c.information_asset_id == data.information_asset_id,
        )
    )
    if exists:
        return {"detail": "Process redan kopplad till informationsmängd"}
    await db.execute(
        process_information_link.insert().values(
            process_id=process_id,
            information_asset_id=data.information_asset_id,
        )
    )
    await db.flush()
    return {"detail": "Process kopplad till informationsmängd"}


@router.delete(
    "/{process_id}/information-assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_process_from_information_asset(
    process_id: UUID,
    asset_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    result = await db.execute(
        process_information_link.delete().where(
            process_information_link.c.process_id == process_id,
            process_information_link.c.information_asset_id == asset_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()
