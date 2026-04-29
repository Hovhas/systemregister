"""ArchiMate Open Exchange Format-generering (Paket B.2).

Producerar XML enligt http://www.opengroup.org/xsd/archimate/3.0/.
2C8 / Archi / Sparx EA kan importera detta som vy utan att äga datat.
"""
from __future__ import annotations

import uuid as _uuid
from uuid import UUID
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BusinessCapability, BusinessProcess, InformationAsset,
    OrgUnit, System,
    capability_system_link, process_system_link, process_capability_link,
    process_information_link,
)


_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"


def _e(tag: str, **attrs: str) -> ET.Element:
    el = ET.Element(f"{{{_NS}}}{tag}")
    for k, v in attrs.items():
        el.set(k, v)
    return el


def _xsi_type(el: ET.Element, value: str) -> None:
    el.set(f"{{{_XSI}}}type", value)


def _name(parent: ET.Element, text: str) -> None:
    name = ET.SubElement(parent, f"{{{_NS}}}name")
    name.set("xml:lang", "sv")
    name.text = text


def _doc(parent: ET.Element, text: str | None) -> None:
    if not text:
        return
    documentation = ET.SubElement(parent, f"{{{_NS}}}documentation")
    documentation.set("xml:lang", "sv")
    documentation.text = text


async def build_archimate_xml(
    organization_id: UUID, db: AsyncSession,
) -> str:
    """Bygg ArchiMate XML för en organisation."""
    ET.register_namespace("", _NS)
    ET.register_namespace("xsi", _XSI)

    root = _e("model", identifier=f"id-{_uuid.uuid4()}")
    root.set(f"{{{_XSI}}}schemaLocation",
             f"{_NS} http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd")
    _name(root, "Sundsvalls systemregister-export")

    # Element-block
    elements_el = ET.SubElement(root, f"{{{_NS}}}elements")
    rels_el = ET.SubElement(root, f"{{{_NS}}}relationships")

    def add_element(entity_id: UUID, name: str, archi_type: str,
                    documentation: str | None = None) -> str:
        eid = f"el-{entity_id}"
        elem = ET.SubElement(elements_el, f"{{{_NS}}}element", identifier=eid)
        _xsi_type(elem, archi_type)
        _name(elem, name)
        _doc(elem, documentation)
        return eid

    def add_relationship(rel_type: str, source_id: str, target_id: str,
                         name: str | None = None) -> None:
        rid = f"rel-{_uuid.uuid4()}"
        rel = ET.SubElement(
            rels_el, f"{{{_NS}}}relationship",
            identifier=rid, source=source_id, target=target_id,
        )
        _xsi_type(rel, rel_type)
        if name:
            _name(rel, name)

    # --- Hämta data ---
    systems = (await db.execute(
        select(System).where(System.organization_id == organization_id)
    )).scalars().all()
    capabilities = (await db.execute(
        select(BusinessCapability)
        .where(BusinessCapability.organization_id == organization_id)
    )).scalars().all()
    processes = (await db.execute(
        select(BusinessProcess)
        .where(BusinessProcess.organization_id == organization_id)
    )).scalars().all()
    information_assets = (await db.execute(
        select(InformationAsset)
        .where(InformationAsset.organization_id == organization_id)
    )).scalars().all()
    org_units = (await db.execute(
        select(OrgUnit).where(OrgUnit.organization_id == organization_id)
    )).scalars().all()

    # --- Skapa element ---
    for s in systems:
        add_element(s.id, s.name, "ApplicationComponent", s.description)
    for c in capabilities:
        add_element(c.id, c.name, "Capability", c.description)
    for p in processes:
        add_element(p.id, p.name, "BusinessProcess", p.description)
    for a in information_assets:
        add_element(a.id, a.name, "DataObject", a.description)
    for u in org_units:
        add_element(u.id, u.name, "BusinessActor", None)

    def el_id(entity_id: UUID) -> str:
        return f"el-{entity_id}"

    # --- Composition: parent → child för hierarki ---
    for c in capabilities:
        if c.parent_capability_id:
            add_relationship("Composition", el_id(c.parent_capability_id), el_id(c.id))
    for p in processes:
        if p.parent_process_id:
            add_relationship("Composition", el_id(p.parent_process_id), el_id(p.id))
    for u in org_units:
        if u.parent_unit_id:
            add_relationship("Composition", el_id(u.parent_unit_id), el_id(u.id))

    # --- Realization: System realiserar Capability ---
    cap_sys_rows = (await db.execute(
        select(capability_system_link.c.capability_id, capability_system_link.c.system_id)
    )).all()
    sys_ids = {s.id for s in systems}
    cap_ids = {c.id for c in capabilities}
    for cap_id, sys_id in cap_sys_rows:
        if sys_id in sys_ids and cap_id in cap_ids:
            add_relationship("Realization", el_id(sys_id), el_id(cap_id))

    # --- Serving: System tjänar Process ---
    proc_sys_rows = (await db.execute(
        select(process_system_link.c.process_id, process_system_link.c.system_id)
    )).all()
    proc_ids = {p.id for p in processes}
    for proc_id, sys_id in proc_sys_rows:
        if sys_id in sys_ids and proc_id in proc_ids:
            add_relationship("Serving", el_id(sys_id), el_id(proc_id))

    # --- Realization: Process realiserar Capability ---
    proc_cap_rows = (await db.execute(
        select(process_capability_link.c.process_id, process_capability_link.c.capability_id)
    )).all()
    for proc_id, cap_id in proc_cap_rows:
        if proc_id in proc_ids and cap_id in cap_ids:
            add_relationship("Realization", el_id(proc_id), el_id(cap_id))

    # --- Access: Process använder InformationAsset ---
    proc_info_rows = (await db.execute(
        select(
            process_information_link.c.process_id,
            process_information_link.c.information_asset_id,
        )
    )).all()
    info_ids = {a.id for a in information_assets}
    for proc_id, info_id in proc_info_rows:
        if proc_id in proc_ids and info_id in info_ids:
            add_relationship("Access", el_id(proc_id), el_id(info_id))

    # --- Default-vy ---
    views_el = ET.SubElement(root, f"{{{_NS}}}views")
    diagrams_el = ET.SubElement(views_el, f"{{{_NS}}}diagrams")
    view = ET.SubElement(
        diagrams_el, f"{{{_NS}}}view",
        identifier=f"view-{_uuid.uuid4()}",
    )
    _xsi_type(view, "Diagram")
    _name(view, "Översikt")

    return ET.tostring(root, encoding="unicode", xml_declaration=True)
