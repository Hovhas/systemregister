"""API för organisationsenheter (Paket A)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import OrgUnit
from app.schemas import (
    OrgUnitCreate, OrgUnitUpdate, OrgUnitResponse, OrgUnitTreeNode,
    PaginatedResponse,
)

router = APIRouter(prefix="/org-units", tags=["Organisationsenhet"])


@router.get("/", response_model=PaginatedResponse[OrgUnitResponse])
async def list_org_units(
    organization_id: UUID | None = Query(None),
    parent_unit_id: UUID | None = Query(None),
    only_top_level: bool = Query(False),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(OrgUnit)
    if organization_id:
        base = base.where(OrgUnit.organization_id == organization_id)
    if parent_unit_id:
        base = base.where(OrgUnit.parent_unit_id == parent_unit_id)
    if only_top_level:
        base = base.where(OrgUnit.parent_unit_id.is_(None))
    if q:
        base = base.where(OrgUnit.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    stmt = (
        base.order_by(OrgUnit.name, OrgUnit.id).offset(offset).limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return PaginatedResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/tree", response_model=list[OrgUnitTreeNode])
async def get_org_unit_tree(
    organization_id: UUID = Query(..., description="Organisation att bygga träd för"),
    db: AsyncSession = Depends(get_rls_db),
):
    """Returnerar hierarkin för en organisation som ett träd."""
    stmt = select(OrgUnit).where(OrgUnit.organization_id == organization_id)
    units = (await db.execute(stmt)).scalars().all()

    by_id: dict[UUID, OrgUnitTreeNode] = {
        u.id: OrgUnitTreeNode(
            id=u.id,
            name=u.name,
            unit_type=u.unit_type,
            manager_name=u.manager_name,
            cost_center=u.cost_center,
            children=[],
        )
        for u in units
    }
    roots: list[OrgUnitTreeNode] = []
    for u in units:
        node = by_id[u.id]
        if u.parent_unit_id and u.parent_unit_id in by_id:
            by_id[u.parent_unit_id].children.append(node)
        else:
            roots.append(node)
    # Sortera barnlistor
    for node in by_id.values():
        node.children.sort(key=lambda n: n.name)
    roots.sort(key=lambda n: n.name)
    return roots


@router.get("/{unit_id}", response_model=OrgUnitResponse)
async def get_org_unit(unit_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    unit = await db.get(OrgUnit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Organisationsenhet hittades inte")
    return unit


@router.post("/", response_model=OrgUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_org_unit(data: OrgUnitCreate, db: AsyncSession = Depends(get_rls_db)):
    if data.parent_unit_id:
        parent = await db.get(OrgUnit, data.parent_unit_id)
        if not parent:
            raise HTTPException(status_code=422, detail="Förälderenhet finns inte")
    unit = OrgUnit(**data.model_dump())
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    return unit


@router.patch("/{unit_id}", response_model=OrgUnitResponse)
async def update_org_unit(
    unit_id: UUID, data: OrgUnitUpdate, db: AsyncSession = Depends(get_rls_db),
):
    unit = await db.get(OrgUnit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Organisationsenhet hittades inte")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("parent_unit_id") == unit.id:
        raise HTTPException(status_code=422, detail="En enhet kan inte vara förälder till sig själv")
    for key, value in payload.items():
        setattr(unit, key, value)
    await db.flush()
    await db.refresh(unit)
    return unit


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_unit(unit_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    unit = await db.get(OrgUnit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Organisationsenhet hittades inte")
    await db.delete(unit)
    await db.flush()
