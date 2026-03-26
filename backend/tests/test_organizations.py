"""
Tests for /api/v1/organizations endpoints.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORG_BASE = {
    "name": "Sundsvalls kommun",
    "org_number": "212000-2723",
    "org_type": "kommun",
    "description": "Moderorganisation",
}


async def create_org(client, payload: dict | None = None) -> dict:
    """Helper: POST a new organization and return the response JSON."""
    data = payload or ORG_BASE.copy()
    resp = await client.post("/api/v1/organizations/", json=data)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_organization(client):
    """POST /api/v1/organizations/ returns 201 with correct fields."""
    resp = await client.post("/api/v1/organizations/", json=ORG_BASE)

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert body["name"] == ORG_BASE["name"], "name mismatch"
    assert body["org_number"] == ORG_BASE["org_number"], "org_number mismatch"
    assert body["org_type"] == ORG_BASE["org_type"], "org_type mismatch"
    assert body["description"] == ORG_BASE["description"], "description mismatch"
    assert "id" in body, "response must include id"
    assert "created_at" in body, "response must include created_at"
    assert "updated_at" in body, "response must include updated_at"
    # parent_org_id should default to None
    assert body["parent_org_id"] is None, "parent_org_id should be None by default"


@pytest.mark.asyncio
async def test_create_organization_minimal(client):
    """POST with only required fields (no org_number, no description) should succeed."""
    payload = {"name": "DIGIT", "org_type": "digit"}
    resp = await client.post("/api/v1/organizations/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["org_number"] is None
    assert body["description"] is None


@pytest.mark.asyncio
async def test_create_organization_invalid_org_type(client):
    """POST with an unknown org_type should return 422."""
    payload = {**ORG_BASE, "org_type": "invalid_type"}
    resp = await client.post("/api/v1/organizations/", json=payload)

    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_organizations(client):
    """GET /api/v1/organizations/ returns a list."""
    await create_org(client)
    await create_org(client, {**ORG_BASE, "name": "Bolag AB", "org_number": "556000-0001", "org_type": "bolag"})

    resp = await client.get("/api/v1/organizations/")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list), "response should be a list"
    assert len(body) >= 2, f"expected at least 2 orgs, got {len(body)}"
    # Verify sorting by name (alphabetical)
    names = [o["name"] for o in body]
    assert names == sorted(names), "organizations should be sorted by name"


@pytest.mark.asyncio
async def test_list_organizations_empty(client):
    """GET /api/v1/organizations/ on empty DB returns empty list."""
    resp = await client.get("/api/v1/organizations/")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_organization(client):
    """GET /api/v1/organizations/{id} returns the correct org."""
    created = await create_org(client)
    org_id = created["id"]

    resp = await client.get(f"/api/v1/organizations/{org_id}")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["id"] == org_id, "id should match"
    assert body["name"] == created["name"]


@pytest.mark.asyncio
async def test_get_organization_not_found(client):
    """GET /api/v1/organizations/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/organizations/{fake_id}")

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_update_organization(client):
    """PATCH /api/v1/organizations/{id} updates fields correctly."""
    created = await create_org(client)
    org_id = created["id"]

    patch_payload = {"name": "Uppdaterat Namn", "description": "Ny beskrivning"}
    resp = await client.patch(f"/api/v1/organizations/{org_id}", json=patch_payload)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Uppdaterat Namn", "name should be updated"
    assert body["description"] == "Ny beskrivning", "description should be updated"
    # Unchanged fields should remain intact
    assert body["org_type"] == created["org_type"], "org_type should not change"
    assert body["org_number"] == created["org_number"], "org_number should not change"


@pytest.mark.asyncio
async def test_update_organization_not_found(client):
    """PATCH on non-existent org returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/organizations/{fake_id}", json={"name": "X"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_organization(client):
    """DELETE /api/v1/organizations/{id} removes the org and returns 204."""
    created = await create_org(client)
    org_id = created["id"]

    delete_resp = await client.delete(f"/api/v1/organizations/{org_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/organizations/{org_id}")
    assert get_resp.status_code == 404, "org should be gone after delete"


@pytest.mark.asyncio
async def test_delete_organization_not_found(client):
    """DELETE on non-existent org returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/organizations/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_organization_with_systems_fails(client):
    """DELETE on org that has linked systems returns 409."""
    org = await create_org(client)
    org_id = org["id"]

    # Create a system linked to this org
    system_payload = {
        "organization_id": org_id,
        "name": "Testssystem",
        "description": "Ett teststystem",
        "system_category": "verksamhetssystem",
    }
    sys_resp = await client.post("/api/v1/systems/", json=system_payload)
    assert sys_resp.status_code == 201, f"System creation failed: {sys_resp.text}"

    # Now try to delete the org — should fail
    delete_resp = await client.delete(f"/api/v1/organizations/{org_id}")
    assert delete_resp.status_code == 409, (
        f"Expected 409 when deleting org with systems, got {delete_resp.status_code}: {delete_resp.text}"
    )
    assert "system" in delete_resp.json()["detail"].lower(), "Error detail should mention systems"
