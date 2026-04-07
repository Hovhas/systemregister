"""
Tests for /api/v1/information-assets/ endpoints.
"""

import pytest

from tests.factories import create_org, create_system, create_information_asset


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_create_information_asset(client):
    """POST /api/v1/information-assets/ returns 201 with correct fields."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "name": "Elevregister",
        "description": "Register over elever i kommunen",
    }
    resp = await client.post("/api/v1/information-assets/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["name"] == "Elevregister"
    assert body["organization_id"] == org["id"]
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_with_classification(client):
    """POST with confidentiality/integrity/availability values."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "name": "Hemlig mangd",
        "confidentiality": 3,
        "integrity": 2,
        "availability": 1,
    }
    resp = await client.post("/api/v1/information-assets/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["confidentiality"] == 3
    assert body["integrity"] == 2
    assert body["availability"] == 1


@pytest.mark.asyncio
async def test_get_information_asset(client):
    """GET /api/v1/information-assets/{id} returns correct data."""
    org = await create_org(client)
    asset = await create_information_asset(client, org["id"], name="Patientdata")

    resp = await client.get(f"/api/v1/information-assets/{asset['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == asset["id"]
    assert body["name"] == "Patientdata"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_list_information_assets(client):
    """GET /api/v1/information-assets/ returns paginated list."""
    org = await create_org(client)
    await create_information_asset(client, org["id"], name="Mangd A")
    await create_information_asset(client, org["id"], name="Mangd B")

    resp = await client.get("/api/v1/information-assets/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_filter_by_personal_data(client):
    """GET /api/v1/information-assets/?contains_personal_data=true filters correctly."""
    org = await create_org(client)
    await create_information_asset(
        client, org["id"], name="Personuppgifter", contains_personal_data=True
    )
    await create_information_asset(
        client, org["id"], name="Offentlig data", contains_personal_data=False
    )

    resp = await client.get(
        "/api/v1/information-assets/",
        params={"contains_personal_data": "true"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["contains_personal_data"] is True


@pytest.mark.asyncio
async def test_update_information_asset(client):
    """PATCH /api/v1/information-assets/{id} updates fields."""
    org = await create_org(client)
    asset = await create_information_asset(client, org["id"], name="Gammalt Namn")

    resp = await client.patch(
        f"/api/v1/information-assets/{asset['id']}",
        json={"name": "Uppdaterat Namn"},
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Uppdaterat Namn"
    assert body["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_delete_information_asset(client):
    """DELETE /api/v1/information-assets/{id} returns 204."""
    org = await create_org(client)
    asset = await create_information_asset(client, org["id"])

    resp = await client.delete(f"/api/v1/information-assets/{asset['id']}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/information-assets/{asset['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_link_to_system(client):
    """POST /api/v1/information-assets/{id}/systems links asset to system."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    asset = await create_information_asset(client, org["id"])

    resp = await client.post(
        f"/api/v1/information-assets/{asset['id']}/systems",
        json={"system_id": system["id"]},
    )

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_unlink_from_system(client):
    """DELETE /api/v1/information-assets/{id}/systems/{system_id} returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    asset = await create_information_asset(client, org["id"])

    # Link first
    link_resp = await client.post(
        f"/api/v1/information-assets/{asset['id']}/systems",
        json={"system_id": system["id"]},
    )
    assert link_resp.status_code == 201

    # Unlink
    resp = await client.delete(
        f"/api/v1/information-assets/{asset['id']}/systems/{system['id']}"
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_not_found(client):
    """GET /api/v1/information-assets/{nonexistent} returns 404."""
    resp = await client.get(f"/api/v1/information-assets/{FAKE_UUID}")
    assert resp.status_code == 404
