"""Tester för ArchiMate Open Exchange-export (Paket B.2)."""
from xml.etree import ElementTree as ET

import pytest

from tests.factories import create_org, create_system


_NS = {
    "a": "http://www.opengroup.org/xsd/archimate/3.0/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


async def _create_capability(client, org_id: str, name: str, **extra):
    resp = await client.post(
        "/api/v1/capabilities/",
        json={"organization_id": str(org_id), "name": name, **extra},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_process(client, org_id: str, name: str, **extra):
    resp = await client.post(
        "/api/v1/processes/",
        json={"organization_id": str(org_id), "name": name, **extra},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_archimate_xml_is_well_formed(client):
    org = await create_org(client)
    await create_system(client, org["id"], name="System X")
    await _create_capability(client, org["id"], "Förmåga A")

    resp = await client.get(
        "/api/v1/export/archimate.xml",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")

    root = ET.fromstring(resp.content)
    assert root.tag.endswith("model")


@pytest.mark.asyncio
async def test_archimate_contains_systems_and_capabilities(client):
    org = await create_org(client)
    sys_x = await create_system(client, org["id"], name="MagiskSystem")
    cap_a = await _create_capability(client, org["id"], "VerksamhetsFörmåga")

    resp = await client.get(
        "/api/v1/export/archimate.xml",
        params={"organization_id": org["id"]},
    )
    root = ET.fromstring(resp.content)
    elements = root.findall("a:elements/a:element", _NS)
    names = [
        (e.find("a:name", _NS).text if e.find("a:name", _NS) is not None else None)
        for e in elements
    ]
    assert "MagiskSystem" in names
    assert "VerksamhetsFörmåga" in names


@pytest.mark.asyncio
async def test_archimate_realization_relationship(client):
    org = await create_org(client)
    sys_x = await create_system(client, org["id"], name="SystemR")
    cap_a = await _create_capability(client, org["id"], "Realiserad förmåga")
    await client.post(
        f"/api/v1/capabilities/{cap_a['id']}/systems",
        json={"system_id": sys_x["id"]},
    )

    resp = await client.get(
        "/api/v1/export/archimate.xml",
        params={"organization_id": org["id"]},
    )
    root = ET.fromstring(resp.content)
    rels = root.findall("a:relationships/a:relationship", _NS)
    types = {r.get(f"{{{_NS['xsi']}}}type") for r in rels}
    assert "Realization" in types


@pytest.mark.asyncio
async def test_archimate_respects_multi_org(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    await create_system(client, org_a["id"], name="OrgA-system")
    await create_system(client, org_b["id"], name="OrgB-system")

    resp = await client.get(
        "/api/v1/export/archimate.xml",
        params={"organization_id": org_a["id"]},
    )
    root = ET.fromstring(resp.content)
    elements = root.findall("a:elements/a:element", _NS)
    names = [
        (e.find("a:name", _NS).text if e.find("a:name", _NS) is not None else None)
        for e in elements
    ]
    assert "OrgA-system" in names
    assert "OrgB-system" not in names
