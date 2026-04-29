"""Tjänst för Mermaid-diagramgenerering (Paket B)."""
from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BusinessCapability, BusinessProcess,
    System, SystemIntegration, ValueStream,
)


_NODE_ID_RE = re.compile(r"[^A-Za-z0-9_]")


def _node_id(prefix: str, value: UUID | str) -> str:
    """Skapa stabilt Mermaid-nod-ID från ett UUID."""
    raw = str(value).replace("-", "")[:12]
    return f"{prefix}{raw}"


def _escape_label(text: str) -> str:
    """Escape:a tecken som bryter Mermaids node-syntax."""
    if text is None:
        return ""
    return text.replace('"', "&quot;").replace("\n", " ").strip()


# ============================================================
# Context-diagram för ett system
# ============================================================

async def build_context_diagram(
    system_id: UUID, db: AsyncSession,
) -> str:
    """Returnerar Mermaid flowchart för ett systems integrationer (in/ut)."""
    system = await db.get(System, system_id)
    if not system:
        raise ValueError("System hittades inte")

    out_stmt = (
        select(SystemIntegration, System)
        .join(System, System.id == SystemIntegration.target_system_id)
        .where(SystemIntegration.source_system_id == system_id)
    )
    in_stmt = (
        select(SystemIntegration, System)
        .join(System, System.id == SystemIntegration.source_system_id)
        .where(SystemIntegration.target_system_id == system_id)
    )
    outgoing = (await db.execute(out_stmt)).all()
    incoming = (await db.execute(in_stmt)).all()

    lines = ["flowchart LR"]
    center = _node_id("S", system.id)
    lines.append(f'    {center}["{_escape_label(system.name)}"]:::focus')

    rendered: set[str] = {center}
    for integration, target in outgoing:
        nid = _node_id("S", target.id)
        if nid not in rendered:
            lines.append(f'    {nid}["{_escape_label(target.name)}"]')
            rendered.add(nid)
        lines.append(
            f"    {center} -->|{integration.integration_type.value}| {nid}"
        )
    for integration, source in incoming:
        nid = _node_id("S", source.id)
        if nid not in rendered:
            lines.append(f'    {nid}["{_escape_label(source.name)}"]')
            rendered.add(nid)
        lines.append(
            f"    {nid} -->|{integration.integration_type.value}| {center}"
        )

    lines.append("    classDef focus fill:#0057A8,stroke:#0057A8,color:#ffffff;")
    return "\n".join(lines)


# ============================================================
# Förmågekarta
# ============================================================

async def build_capability_map(
    organization_id: UUID, db: AsyncSession, *, max_systems_per_capability: int = 5,
) -> str:
    """Förmågehierarki + N stödjande system per förmåga."""
    stmt = (
        select(BusinessCapability)
        .where(BusinessCapability.organization_id == organization_id)
        .options(selectinload(BusinessCapability.systems))
        .order_by(BusinessCapability.name)
    )
    capabilities = (await db.execute(stmt)).scalars().all()

    lines = ["flowchart TD"]
    cap_ids: set[str] = set()
    for cap in capabilities:
        nid = _node_id("C", cap.id)
        cap_ids.add(nid)
        lines.append(f'    {nid}["{_escape_label(cap.name)}"]')

    # Hierarki — parent → child
    for cap in capabilities:
        if cap.parent_capability_id:
            parent_nid = _node_id("C", cap.parent_capability_id)
            child_nid = _node_id("C", cap.id)
            if parent_nid in cap_ids:
                lines.append(f"    {parent_nid} --> {child_nid}")

    # System per förmåga
    for cap in capabilities:
        cap_nid = _node_id("C", cap.id)
        for system in cap.systems[:max_systems_per_capability]:
            sys_nid = _node_id("S", system.id)
            lines.append(f'    {sys_nid}(["{_escape_label(system.name)}"])')
            lines.append(f"    {cap_nid} -.-> {sys_nid}")

    if not capabilities:
        lines.append('    empty["Inga förmågor registrerade"]')

    return "\n".join(lines)


# ============================================================
# Process-flow
# ============================================================

async def build_process_flow(
    process_id: UUID, db: AsyncSession,
) -> str:
    """Process + delprocesser + system + informationsmängder."""
    proc = await db.get(BusinessProcess, process_id)
    if not proc:
        raise ValueError("Process hittades inte")

    # Eager-ladda relationer
    stmt = (
        select(BusinessProcess)
        .where(BusinessProcess.id == process_id)
        .options(
            selectinload(BusinessProcess.systems),
            selectinload(BusinessProcess.information_assets),
            selectinload(BusinessProcess.children),
        )
    )
    proc = (await db.execute(stmt)).scalar_one()

    lines = ["flowchart LR"]
    main = _node_id("P", proc.id)
    lines.append(f'    {main}["{_escape_label(proc.name)}"]:::focus')

    for child in proc.children:
        cnid = _node_id("P", child.id)
        lines.append(f'    {cnid}["{_escape_label(child.name)}"]')
        lines.append(f"    {main} --> {cnid}")

    for system in proc.systems:
        snid = _node_id("S", system.id)
        lines.append(f'    {snid}(["{_escape_label(system.name)}"])')
        lines.append(f"    {main} -.system.-> {snid}")

    for asset in proc.information_assets:
        anid = _node_id("I", asset.id)
        lines.append(f'    {anid}[/"{_escape_label(asset.name)}"/]')
        lines.append(f"    {main} -.info.-> {anid}")

    lines.append("    classDef focus fill:#0057A8,stroke:#0057A8,color:#ffffff;")
    return "\n".join(lines)


# ============================================================
# Värdeström
# ============================================================

async def build_value_stream_diagram(
    value_stream_id: UUID, db: AsyncSession,
) -> str:
    """Värdeström med stages som horisontellt flöde."""
    vs = await db.get(ValueStream, value_stream_id)
    if not vs:
        raise ValueError("Värdeström hittades inte")

    stages = sorted(vs.stages or [], key=lambda s: s.get("order", 0))

    lines = [f"%% Värdeström: {_escape_label(vs.name)}", "flowchart LR"]
    if not stages:
        lines.append('    empty["Inga etapper"]')
        return "\n".join(lines)

    prev_nid = None
    for idx, stage in enumerate(stages):
        nid = f"E{idx}"
        label = _escape_label(stage.get("name", f"Etapp {idx + 1}"))
        lines.append(f'    {nid}["{label}"]')
        if prev_nid:
            lines.append(f"    {prev_nid} --> {nid}")
        prev_nid = nid
    return "\n".join(lines)


# ============================================================
# Systemlandskap
# ============================================================

async def build_system_landscape(
    organization_id: UUID, db: AsyncSession,
) -> str:
    """Alla system grupperade per kategori med integrationer."""
    sys_stmt = (
        select(System)
        .where(System.organization_id == organization_id)
        .order_by(System.system_category, System.name)
    )
    systems = (await db.execute(sys_stmt)).scalars().all()

    by_category: dict[str, list[System]] = {}
    for s in systems:
        by_category.setdefault(s.system_category.value, []).append(s)

    lines = ["flowchart LR"]
    for category, group in by_category.items():
        # Mermaid kräver att subgraph-id är ett enkelt token
        sg_id = _NODE_ID_RE.sub("_", category)
        lines.append(f"    subgraph {sg_id}[\"{_escape_label(category)}\"]")
        for s in group:
            nid = _node_id("S", s.id)
            lines.append(f'        {nid}["{_escape_label(s.name)}"]')
        lines.append("    end")

    if not by_category:
        lines.append('    empty["Inga system"]')

    sys_ids = {s.id for s in systems}
    int_stmt = (
        select(SystemIntegration)
        .where(
            SystemIntegration.source_system_id.in_(sys_ids)
            | SystemIntegration.target_system_id.in_(sys_ids)
        )
    )
    integrations = (await db.execute(int_stmt)).scalars().all()
    for integration in integrations:
        if integration.source_system_id not in sys_ids or integration.target_system_id not in sys_ids:
            continue
        src = _node_id("S", integration.source_system_id)
        tgt = _node_id("S", integration.target_system_id)
        lines.append(f"    {src} -->|{integration.integration_type.value}| {tgt}")

    return "\n".join(lines)
