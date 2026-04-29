"""Tjänst som löser ut åtkomstpaketet för en anställningsmall (Paket C)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BusinessRole, EmploymentTemplate, System,
    template_role_link,
)
from app.models.enums import AccessLevel, AccessType
from app.schemas.iga import ResolvedAccessEntry, ResolvedAccessResponse


# Rangordningar — högsta vinner vid överlapp
_LEVEL_ORDER: dict[AccessLevel, int] = {
    AccessLevel.READ: 0,
    AccessLevel.WRITE: 1,
    AccessLevel.ADMIN: 2,
}

_TYPE_ORDER: dict[AccessType, int] = {
    AccessType.MANUAL: 0,
    AccessType.CONDITIONAL: 1,
    AccessType.BIRTHRIGHT: 2,
}


async def resolve_template_access(
    template_id: UUID, db: AsyncSession,
) -> ResolvedAccessResponse:
    """
    Returnerar deduplicerad lista över alla (system, access_level, access_type)
    som följer av mallens roller.

    - Vid överlapp på samma system: högsta access_level vinner.
    - Vid blandade access_type: birthright > conditional > manual.
    - Inaktiv mall (`is_active=False`): returnerar tom lista, men metadata fylls i.
    """
    template = await db.get(EmploymentTemplate, template_id)
    if not template:
        raise ValueError("Mall hittades inte")

    if not template.is_active:
        return ResolvedAccessResponse(
            template_id=template.id,
            template_name=template.name,
            is_active=False,
            entries=[],
        )

    # Hämta alla roller kopplade till mallen
    roles_stmt = (
        select(BusinessRole)
        .join(template_role_link, template_role_link.c.role_id == BusinessRole.id)
        .where(template_role_link.c.template_id == template_id)
        .options(selectinload(BusinessRole.system_accesses))
    )
    roles = (await db.execute(roles_stmt)).scalars().all()

    # Aggregera per system_id
    aggregated: dict[UUID, dict] = {}
    for role in roles:
        for access in role.system_accesses:
            current = aggregated.get(access.system_id)
            if current is None:
                aggregated[access.system_id] = {
                    "system_id": access.system_id,
                    "access_level": access.access_level,
                    "access_type": access.access_type,
                    "contributing_roles": {role.name},
                }
                continue
            current["contributing_roles"].add(role.name)
            if _LEVEL_ORDER[access.access_level] > _LEVEL_ORDER[current["access_level"]]:
                current["access_level"] = access.access_level
            if _TYPE_ORDER[access.access_type] > _TYPE_ORDER[current["access_type"]]:
                current["access_type"] = access.access_type

    if not aggregated:
        return ResolvedAccessResponse(
            template_id=template.id,
            template_name=template.name,
            is_active=True,
            entries=[],
        )

    # Hämta systemnamn
    system_ids = list(aggregated.keys())
    sys_rows = (await db.execute(
        select(System.id, System.name).where(System.id.in_(system_ids))
    )).all()
    name_by_id = {sid: sname for sid, sname in sys_rows}

    entries = [
        ResolvedAccessEntry(
            system_id=v["system_id"],
            system_name=name_by_id.get(v["system_id"], "(okänt system)"),
            access_level=v["access_level"],
            access_type=v["access_type"],
            contributing_role_names=sorted(v["contributing_roles"]),
        )
        for v in aggregated.values()
    ]
    entries.sort(key=lambda e: e.system_name)

    return ResolvedAccessResponse(
        template_id=template.id,
        template_name=template.name,
        is_active=True,
        entries=entries,
    )
