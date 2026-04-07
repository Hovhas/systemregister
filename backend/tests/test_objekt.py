"""
Tests for /api/v1/objekt/ endpoints.
"""

import pytest

from tests.factories import create_org, create_objekt


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_create_objekt(client):
    """POST /api/v1/objekt/ returns 201 with correct fields."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "name": "Ekonomiobjekt",
        "description": "Forvaltar ekonomisystem",
    }
    resp = await client.post("/api/v1/objekt/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["name"] == "Ekonomiobjekt"
    assert body["organization_id"] == org["id"]
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_get_objekt(client):
    """GET /api/v1/objekt/{id} returns correct data."""
    org = await create_org(client)
    objekt = await create_objekt(client, org["id"], name="Vard och Omsorg")

    resp = await client.get(f"/api/v1/objekt/{objekt['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == objekt["id"]
    assert body["name"] == "Vard och Omsorg"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_list_objekt(client):
    """GET /api/v1/objekt/ returns paginated list."""
    org = await create_org(client)
    await create_objekt(client, org["id"], name="Objekt A")
    await create_objekt(client, org["id"], name="Objekt B")

    resp = await client.get("/api/v1/objekt/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_list_objekt_filter_org(client):
    """GET /api/v1/objekt/?organization_id=X filters correctly."""
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B", org_type="bolag")
    await create_objekt(client, org_a["id"], name="A-objekt")
    await create_objekt(client, org_b["id"], name="B-objekt")

    resp = await client.get("/api/v1/objekt/", params={"organization_id": org_a["id"]})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["organization_id"] == org_a["id"]


@pytest.mark.asyncio
async def test_update_objekt(client):
    """PATCH /api/v1/objekt/{id} updates name."""
    org = await create_org(client)
    objekt = await create_objekt(client, org["id"], name="Gammalt Namn")

    resp = await client.patch(
        f"/api/v1/objekt/{objekt['id']}", json={"name": "Nytt Namn"}
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Nytt Namn"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_delete_objekt(client):
    """DELETE /api/v1/objekt/{id} returns 204."""
    org = await create_org(client)
    objekt = await create_objekt(client, org["id"])

    resp = await client.delete(f"/api/v1/objekt/{objekt['id']}")
    assert resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(f"/api/v1/objekt/{objekt['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_objekt_not_found(client):
    """GET /api/v1/objekt/{nonexistent} returns 404."""
    resp = await client.get(f"/api/v1/objekt/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_objekt_search(client):
    """GET /api/v1/objekt/?q=term filters by name."""
    org = await create_org(client)
    await create_objekt(client, org["id"], name="Skolforvaltning")
    await create_objekt(client, org["id"], name="Teknik och service")

    resp = await client.get("/api/v1/objekt/", params={"q": "skol"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    names = [item["name"] for item in body["items"]]
    assert any("Skolforvaltning" in n for n in names), f"Expected match, got {names}"
