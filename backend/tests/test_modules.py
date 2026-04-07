"""
Tests for /api/v1/modules/ endpoints.
"""

import pytest

from tests.factories import create_org, create_system, create_module


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_create_module(client):
    """POST /api/v1/modules/ returns 201 with correct fields."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "name": "Fakturamodul",
        "description": "Hanterar fakturering",
    }
    resp = await client.post("/api/v1/modules/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["name"] == "Fakturamodul"
    assert body["organization_id"] == org["id"]
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_module_with_ai(client):
    """POST /api/v1/modules/ with uses_ai=True and ai_risk_class."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "name": "AI-analysmodul",
        "uses_ai": True,
        "ai_risk_class": "hog_risk",
    }
    resp = await client.post("/api/v1/modules/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["uses_ai"] is True
    assert body["ai_risk_class"] == "hog_risk"


@pytest.mark.asyncio
async def test_get_module(client):
    """GET /api/v1/modules/{id} returns correct data."""
    org = await create_org(client)
    mod = await create_module(client, org["id"], name="Rapportmodul")

    resp = await client.get(f"/api/v1/modules/{mod['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == mod["id"]
    assert body["name"] == "Rapportmodul"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_list_modules(client):
    """GET /api/v1/modules/ returns paginated list."""
    org = await create_org(client)
    await create_module(client, org["id"], name="Modul A")
    await create_module(client, org["id"], name="Modul B")

    resp = await client.get("/api/v1/modules/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_update_module(client):
    """PATCH /api/v1/modules/{id} updates fields."""
    org = await create_org(client)
    mod = await create_module(client, org["id"], name="Gammal Modul")

    resp = await client.patch(
        f"/api/v1/modules/{mod['id']}", json={"name": "Ny Modul"}
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Ny Modul"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_delete_module(client):
    """DELETE /api/v1/modules/{id} returns 204."""
    org = await create_org(client)
    mod = await create_module(client, org["id"])

    resp = await client.delete(f"/api/v1/modules/{mod['id']}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/modules/{mod['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_link_module_to_system(client):
    """POST /api/v1/modules/{id}/systems links module to system, returns 201."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    mod = await create_module(client, org["id"])

    resp = await client.post(
        f"/api/v1/modules/{mod['id']}/systems",
        json={"system_id": system["id"]},
    )

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_unlink_module_from_system(client):
    """DELETE /api/v1/modules/{id}/systems/{system_id} returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    mod = await create_module(client, org["id"])

    # Link first
    link_resp = await client.post(
        f"/api/v1/modules/{mod['id']}/systems",
        json={"system_id": system["id"]},
    )
    assert link_resp.status_code == 201

    # Unlink
    resp = await client.delete(
        f"/api/v1/modules/{mod['id']}/systems/{system['id']}"
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_link_nonexistent_module(client):
    """POST /api/v1/modules/{nonexistent}/systems returns 404."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(
        f"/api/v1/modules/{FAKE_UUID}/systems",
        json={"system_id": system["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unlink_nonexistent(client):
    """DELETE /api/v1/modules/{id}/systems/{nonexistent} returns 404."""
    org = await create_org(client)
    mod = await create_module(client, org["id"])

    resp = await client.delete(
        f"/api/v1/modules/{mod['id']}/systems/{FAKE_UUID}"
    )
    assert resp.status_code == 404
