"""Tester för Mermaid-diagramendpoints (Paket B.1)."""
import pytest

from tests.factories import create_org, create_system, create_integration


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_capability(client, org_id: str, name: str = "Förmåga", **extra):
    payload = {"organization_id": str(org_id), "name": name, **extra}
    resp = await client.post("/api/v1/capabilities/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _create_process(client, org_id: str, name: str = "Process", **extra):
    payload = {"organization_id": str(org_id), "name": name, **extra}
    resp = await client.post("/api/v1/processes/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _create_value_stream(client, org_id: str, name: str = "VS", stages=None):
    resp = await client.post(
        "/api/v1/value-streams/",
        json={
            "organization_id": str(org_id),
            "name": name,
            "stages": stages or [],
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_context_diagram_for_system(client):
    org = await create_org(client)
    a = await create_system(client, org["id"], name="Centrumsystem")
    b = await create_system(client, org["id"], name="Beroende-A")
    await create_integration(client, a["id"], b["id"], integration_type="api")

    resp = await client.get(f"/api/v1/diagrams/context/{a['id']}.mmd")
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("flowchart")
    assert "Centrumsystem" in body
    assert "Beroende-A" in body
    assert "api" in body


@pytest.mark.asyncio
async def test_context_diagram_404(client):
    resp = await client.get(f"/api/v1/diagrams/context/{FAKE_UUID}.mmd")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_capability_map(client):
    org = await create_org(client)
    parent = await _create_capability(client, org["id"], name="Toppförmåga")
    await _create_capability(
        client, org["id"], name="Underförmåga",
        parent_capability_id=parent["id"],
    )
    system = await create_system(client, org["id"], name="System X")
    await client.post(
        f"/api/v1/capabilities/{parent['id']}/systems",
        json={"system_id": system["id"]},
    )

    resp = await client.get(
        "/api/v1/diagrams/capability-map.mmd",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "flowchart" in body
    assert "Toppförmåga" in body
    assert "Underförmåga" in body
    assert "System X" in body


@pytest.mark.asyncio
async def test_capability_map_empty(client):
    org = await create_org(client)
    resp = await client.get(
        "/api/v1/diagrams/capability-map.mmd",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    assert "flowchart" in resp.text


@pytest.mark.asyncio
async def test_process_flow(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"], name="Bygglovshantering")
    system = await create_system(client, org["id"], name="ByggR")
    await client.post(
        f"/api/v1/processes/{proc['id']}/systems",
        json={"system_id": system["id"]},
    )

    resp = await client.get(f"/api/v1/diagrams/process-flow/{proc['id']}.mmd")
    assert resp.status_code == 200
    body = resp.text
    assert "Bygglovshantering" in body
    assert "ByggR" in body


@pytest.mark.asyncio
async def test_process_flow_404(client):
    resp = await client.get(f"/api/v1/diagrams/process-flow/{FAKE_UUID}.mmd")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_value_stream_diagram(client):
    org = await create_org(client)
    vs = await _create_value_stream(
        client, org["id"], name="Bli ny invånare",
        stages=[
            {"name": "Anmäl flytt", "description": None, "order": 0},
            {"name": "Folkbokföring", "description": None, "order": 1},
        ],
    )

    resp = await client.get(f"/api/v1/diagrams/value-stream/{vs['id']}.mmd")
    assert resp.status_code == 200
    body = resp.text
    assert "Anmäl flytt" in body
    assert "Folkbokföring" in body
    assert "-->" in body


@pytest.mark.asyncio
async def test_system_landscape(client):
    org = await create_org(client)
    a = await create_system(client, org["id"], name="A-system")
    b = await create_system(client, org["id"], name="B-system")
    await create_integration(client, a["id"], b["id"], integration_type="api")

    resp = await client.get(
        "/api/v1/diagrams/system-landscape.mmd",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "A-system" in body
    assert "B-system" in body
    assert "subgraph" in body


@pytest.mark.asyncio
async def test_diagrams_respect_multi_org(client):
    """system-landscape med org A-id ska inte innehålla org B:s system."""
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    sys_a = await create_system(client, org_a["id"], name="OrgA-system")
    sys_b = await create_system(client, org_b["id"], name="OrgB-system")

    resp = await client.get(
        "/api/v1/diagrams/system-landscape.mmd",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "OrgA-system" in body
    assert "OrgB-system" not in body
