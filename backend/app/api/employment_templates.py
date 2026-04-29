"""API för anställningsmallar (Paket C)."""
import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rls import get_rls_db
from app.models import (
    BusinessRole, EmploymentTemplate, Position, template_role_link,
)
from app.schemas import (
    EmploymentTemplateCreate, EmploymentTemplateUpdate, EmploymentTemplateResponse,
    TemplateRoleLinkRequest, PaginatedResponse, ResolvedAccessResponse,
)
from app.services.template_service import resolve_template_access

router = APIRouter(prefix="/employment-templates", tags=["Anställningsmall"])


def _to_response(template: EmploymentTemplate) -> EmploymentTemplateResponse:
    role_ids = [role.id for role in template.roles] if template.roles else []
    data = EmploymentTemplateResponse.model_validate(template).model_copy()
    data.role_ids = role_ids
    return data


@router.get("/", response_model=PaginatedResponse[EmploymentTemplateResponse])
async def list_templates(
    organization_id: UUID | None = Query(None),
    position_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    base = select(EmploymentTemplate).options(selectinload(EmploymentTemplate.roles))
    if organization_id:
        base = base.where(EmploymentTemplate.organization_id == organization_id)
    if position_id:
        base = base.where(EmploymentTemplate.position_id == position_id)
    if is_active is not None:
        base = base.where(EmploymentTemplate.is_active == is_active)
    if q:
        base = base.where(EmploymentTemplate.name.ilike(f"%{q}%"))

    count_base = select(EmploymentTemplate.id)
    if organization_id:
        count_base = count_base.where(EmploymentTemplate.organization_id == organization_id)
    if position_id:
        count_base = count_base.where(EmploymentTemplate.position_id == position_id)
    if is_active is not None:
        count_base = count_base.where(EmploymentTemplate.is_active == is_active)
    if q:
        count_base = count_base.where(EmploymentTemplate.name.ilike(f"%{q}%"))
    total = await db.scalar(
        select(func.count()).select_from(count_base.subquery())
    ) or 0

    stmt = base.order_by(EmploymentTemplate.name, EmploymentTemplate.id).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    items = [_to_response(t) for t in rows]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{template_id}", response_model=EmploymentTemplateResponse)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    stmt = (
        select(EmploymentTemplate)
        .where(EmploymentTemplate.id == template_id)
        .options(selectinload(EmploymentTemplate.roles))
    )
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Mall hittades inte")
    return _to_response(template)


@router.post(
    "/", response_model=EmploymentTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: EmploymentTemplateCreate, db: AsyncSession = Depends(get_rls_db),
):
    if data.position_id:
        pos = await db.get(Position, data.position_id)
        if not pos:
            raise HTTPException(status_code=422, detail="Befattning finns inte")

    role_ids = data.role_ids
    payload = data.model_dump(exclude={"role_ids"})
    template = EmploymentTemplate(**payload)
    db.add(template)
    await db.flush()

    for rid in role_ids:
        role = await db.get(BusinessRole, rid)
        if not role:
            raise HTTPException(status_code=422, detail=f"Roll {rid} finns inte")
        await db.execute(
            template_role_link.insert().values(template_id=template.id, role_id=rid)
        )
    await db.flush()

    stmt = (
        select(EmploymentTemplate)
        .where(EmploymentTemplate.id == template.id)
        .options(selectinload(EmploymentTemplate.roles))
    )
    template = (await db.execute(stmt)).scalar_one()
    return _to_response(template)


@router.patch("/{template_id}", response_model=EmploymentTemplateResponse)
async def update_template(
    template_id: UUID, data: EmploymentTemplateUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    template = await db.get(EmploymentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Mall hittades inte")

    payload = data.model_dump(exclude_unset=True)
    role_ids = payload.pop("role_ids", None)

    if "position_id" in payload and payload["position_id"]:
        pos = await db.get(Position, payload["position_id"])
        if not pos:
            raise HTTPException(status_code=422, detail="Befattning finns inte")

    for key, value in payload.items():
        setattr(template, key, value)
    await db.flush()

    if role_ids is not None:
        await db.execute(
            template_role_link.delete().where(
                template_role_link.c.template_id == template_id
            )
        )
        for rid in role_ids:
            role = await db.get(BusinessRole, rid)
            if not role:
                raise HTTPException(status_code=422, detail=f"Roll {rid} finns inte")
            await db.execute(
                template_role_link.insert().values(template_id=template_id, role_id=rid)
            )
        await db.flush()

    stmt = (
        select(EmploymentTemplate)
        .where(EmploymentTemplate.id == template_id)
        .options(selectinload(EmploymentTemplate.roles))
    )
    template = (await db.execute(stmt)).scalar_one()
    return _to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    template = await db.get(EmploymentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Mall hittades inte")
    await db.delete(template)
    await db.flush()


@router.post(
    "/{template_id}/roles", status_code=status.HTTP_201_CREATED,
)
async def add_role_to_template(
    template_id: UUID, data: TemplateRoleLinkRequest,
    db: AsyncSession = Depends(get_rls_db),
):
    template = await db.get(EmploymentTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Mall hittades inte")
    role = await db.get(BusinessRole, data.role_id)
    if not role:
        raise HTTPException(status_code=422, detail="Roll finns inte")
    exists = await db.scalar(
        select(func.count())
        .select_from(template_role_link)
        .where(
            template_role_link.c.template_id == template_id,
            template_role_link.c.role_id == data.role_id,
        )
    )
    if not exists:
        await db.execute(
            template_role_link.insert().values(
                template_id=template_id, role_id=data.role_id,
            )
        )
        await db.flush()
    return {"detail": "Roll kopplad till mall"}


@router.delete(
    "/{template_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_role_from_template(
    template_id: UUID, role_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    result = await db.execute(
        template_role_link.delete().where(
            template_role_link.c.template_id == template_id,
            template_role_link.c.role_id == role_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()


@router.get(
    "/{template_id}/resolved-access", response_model=ResolvedAccessResponse,
)
async def get_resolved_access(
    template_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    """Returnerar deduplicerad åtkomstlista som följer av mallens roller."""
    try:
        return await resolve_template_access(template_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{template_id}/resolved-access.csv")
async def get_resolved_access_csv(
    template_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    """Resolved access som CSV — beställningsformatet IT-samordnaren använder."""
    try:
        resolved = await resolve_template_access(template_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel", delimiter=";")
    writer.writerow([
        "system_namn", "access_nivå", "access_typ", "via_roller",
    ])
    for entry in resolved.entries:
        writer.writerow([
            entry.system_name,
            entry.access_level.value,
            entry.access_type.value,
            ", ".join(entry.contributing_role_names),
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=resolved-access-{template_id}.csv"
            )
        },
    )
