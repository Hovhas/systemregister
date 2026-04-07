"""
Tests for /api/v1/components/ endpoints.
"""

import pytest

from tests.factories import create_org, create_system, create_component


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_create_component(client):
    """POST /api/v1/components/ returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    payload = {
        "system_id": system["id"],
        "organization_id": org["id"],
        "name": "Webbserver",
        "description": "Frontend-komponent",
        "component_type": "server",
    }
    resp = await client.post("/api/v1/components/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["name"] == "Webbserver"
    assert body["system_id"] == system["id"]
    assert body["organization_id"] == org["id"]
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_get_component(client):
    """GET /api/v1/components/{id} returns correct data."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    comp = await create_component(client, system["id"], org["id"], name="Databas")

    resp = await client.get(f"/api/v1/components/{comp['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == comp["id"]
    assert body["name"] == "Databas"
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_list_components(client):
    """GET /api/v1/components/ returns paginated list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    await create_component(client, system["id"], org["id"], name="Komponent A")
    await create_component(client, system["id"], org["id"], name="Komponent B")

    resp = await client.get("/api/v1/components/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_list_components_by_system(client):
    """GET /api/v1/components/?system_id=X filters by system."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="System A")
    sys_b = await create_system(client, org["id"], name="System B")
    await create_component(client, sys_a["id"], org["id"], name="A-komp")
    await create_component(client, sys_b["id"], org["id"], name="B-komp")

    resp = await client.get("/api/v1/components/", params={"system_id": sys_a["id"]})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["system_id"] == sys_a["id"]


@pytest.mark.asyncio
async def test_update_component(client):
    """PATCH /api/v1/components/{id} updates fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    comp = await create_component(client, system["id"], org["id"], name="Gammalt")

    resp = await client.patch(
        f"/api/v1/components/{comp['id']}", json={"name": "Uppdaterat"}
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Uppdaterat"
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_delete_component(client):
    """DELETE /api/v1/components/{id} returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    comp = await create_component(client, system["id"], org["id"])

    resp = await client.delete(f"/api/v1/components/{comp['id']}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/components/{comp['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_component_not_found(client):
    """GET /api/v1/components/{nonexistent} returns 404."""
    resp = await client.get(f"/api/v1/components/{FAKE_UUID}")
    assert resp.status_code == 404
