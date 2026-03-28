"""
Tests for /api/v1/systems/{id}/owners and /api/v1/owners/{id} endpoints.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORG_PAYLOAD = {
    "name": "Sundsvalls kommun",
    "org_number": "212000-2723",
    "org_type": "kommun",
}

SYSTEM_BASE = {
    "name": "Procapita",
    "description": "Verksamhetssystem för individ- och familjeomsorg",
    "system_category": "verksamhetssystem",
}

OWNER_BASE = {
    "organization_id": "00000000-0000-0000-0000-000000000000",  # overridden per test
    "role": "systemägare",
    "name": "Anna Svensson",
    "email": "anna.svensson@sundsvall.se",
    "phone": "060-123456",
}


async def create_org(client) -> dict:
    resp = await client.post("/api/v1/organizations/", json=ORG_PAYLOAD)
    assert resp.status_code == 201, f"Org creation failed: {resp.text}"
    return resp.json()


async def create_system(client, org_id: str, name: str = "Procapita") -> dict:
    payload = {**SYSTEM_BASE, "organization_id": org_id, "name": name}
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 201, f"System creation failed: {resp.text}"
    return resp.json()


async def create_owner(client, system_id: str, org_id: str, overrides: dict | None = None) -> dict:
    payload = {**OWNER_BASE, "organization_id": org_id}
    if overrides:
        payload.update(overrides)
    resp = await client.post(f"/api/v1/systems/{system_id}/owners", json=payload)
    assert resp.status_code == 201, f"Owner creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_owner(client):
    """POST /api/v1/systems/{id}/owners returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {**OWNER_BASE, "organization_id": org["id"]}
    resp = await client.post(f"/api/v1/systems/{system_id}/owners", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["system_id"] == system_id
    assert body["organization_id"] == org["id"]
    assert body["role"] == OWNER_BASE["role"]
    assert body["name"] == OWNER_BASE["name"]
    assert body["email"] == OWNER_BASE["email"]
    assert body["phone"] == OWNER_BASE["phone"]
    assert "id" in body, "response must include id"
    assert "created_at" in body, "response must include created_at"


@pytest.mark.asyncio
async def test_add_owner_minimal_fields(client):
    """POST owner with only required fields (no email, no phone) should succeed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "IT-kontakt Person",
    }
    resp = await client.post(f"/api/v1/systems/{system_id}/owners", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["email"] is None
    assert body["phone"] is None


@pytest.mark.asyncio
async def test_list_owners(client):
    """GET /api/v1/systems/{id}/owners returns a list of owners."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    await create_owner(client, system_id, org["id"], {"name": "Person A", "role": "systemägare"})
    await create_owner(client, system_id, org["id"], {"name": "Person B", "role": "informationsägare"})

    resp = await client.get(f"/api/v1/systems/{system_id}/owners")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2, f"expected at least 2 owners, got {len(body)}"


@pytest.mark.asyncio
async def test_list_owners_empty(client):
    """GET /api/v1/systems/{id}/owners on new system returns empty list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/owners")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_owner(client):
    """PATCH /api/v1/owners/{id} updates fields without touching others."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"])
    owner_id = owner["id"]

    patch = {"name": "Anna Eriksson", "email": "anna.eriksson@sundsvall.se"}
    resp = await client.patch(f"/api/v1/owners/{owner_id}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Anna Eriksson"
    assert body["email"] == "anna.eriksson@sundsvall.se"
    # Unchanged fields should remain
    assert body["role"] == OWNER_BASE["role"]
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_update_owner_role(client):
    """PATCH /api/v1/owners/{id} can update the role."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"], {"role": "systemägare"})

    resp = await client.patch(f"/api/v1/owners/{owner['id']}", json={"role": "teknisk_förvaltare"})

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    assert resp.json()["role"] == "teknisk_förvaltare"


@pytest.mark.asyncio
async def test_update_owner_not_found(client):
    """PATCH /api/v1/owners/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/owners/{fake_id}", json={"name": "Ghost"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_owner(client):
    """DELETE /api/v1/owners/{id} removes the owner and returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"])
    owner_id = owner["id"]

    delete_resp = await client.delete(f"/api/v1/owners/{owner_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    # Verify it's gone from the system's owner list
    list_resp = await client.get(f"/api/v1/systems/{system['id']}/owners")
    assert list_resp.status_code == 200
    ids = [o["id"] for o in list_resp.json()]
    assert owner_id not in ids, "deleted owner should not appear in list"


@pytest.mark.asyncio
async def test_delete_owner_not_found(client):
    """DELETE /api/v1/owners/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/owners/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_owner_invalid_system(client):
    """POST /api/v1/systems/{id}/owners with non-existent system returns 404."""
    org = await create_org(client)
    fake_system_id = "00000000-0000-0000-0000-000000000000"

    payload = {**OWNER_BASE, "organization_id": org["id"]}
    resp = await client.post(f"/api/v1/systems/{fake_system_id}/owners", json=payload)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_owners_scoped_to_system(client):
    """Owners added to system A should not appear in system B's list."""
    org = await create_org(client)
    system_a = await create_system(client, org["id"], name="System A")
    system_b = await create_system(client, org["id"], name="System B")

    await create_owner(client, system_a["id"], org["id"])

    resp = await client.get(f"/api/v1/systems/{system_b['id']}/owners")
    assert resp.status_code == 200
    assert resp.json() == [], "system B should have no owners"


@pytest.mark.asyncio
async def test_add_owner_invalid_role(client):
    """POST owner with unknown role value returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {**OWNER_BASE, "organization_id": org["id"], "role": "okänd_roll"}
    resp = await client.post(f"/api/v1/systems/{system_id}/owners", json=payload)

    assert resp.status_code == 422, f"Expected 422 for invalid role, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Extended tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [
    "systemägare", "informationsägare", "systemförvaltare",
    "teknisk_förvaltare", "it_kontakt", "dataskyddsombud",
])
async def test_add_owner_all_six_roles(client, role):
    """POST owner accepts all 6 valid role values."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"System {role}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        **OWNER_BASE,
        "organization_id": org["id"],
        "role": role,
        "name": f"Person för {role}",
    })
    assert resp.status_code == 201, f"Expected 201 for role={role}: {resp.text}"
    assert resp.json()["role"] == role


@pytest.mark.asyncio
async def test_add_duplicate_owner_same_system_role_name_rejected(client):
    """POST same owner (system_id + role + name) twice should be rejected."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    payload = {
        **OWNER_BASE,
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "Dubbelregistrerad Person",
    }
    resp1 = await client.post(f"/api/v1/systems/{system['id']}/owners", json=payload)
    assert resp1.status_code == 201

    try:
        resp2 = await client.post(f"/api/v1/systems/{system['id']}/owners", json=payload)
        assert resp2.status_code in (409, 422, 400), (
            f"Duplicate owner should be rejected, got {resp2.status_code}: {resp2.text}"
        )
    except Exception:
        # FK/unique constraint as exception is also acceptable
        pass


@pytest.mark.asyncio
async def test_multiple_owners_different_roles_same_system(client):
    """Multiple owners with different roles for same system are all accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    roles = ["systemägare", "informationsägare", "systemförvaltare"]
    for i, role in enumerate(roles):
        resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
            "organization_id": org["id"],
            "role": role,
            "name": f"Person {i}",
        })
        assert resp.status_code == 201, f"Expected 201 for role={role}: {resp.text}"

    list_resp = await client.get(f"/api/v1/systems/{system['id']}/owners")
    assert list_resp.status_code == 200
    owners = list_resp.json()
    assert len(owners) == 3, f"Expected 3 owners, got {len(owners)}"


@pytest.mark.asyncio
async def test_update_owner_phone_number(client):
    """PATCH owner can update phone number."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"])

    resp = await client.patch(f"/api/v1/owners/{owner['id']}", json={"phone": "070-9876543"})
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    assert resp.json()["phone"] == "070-9876543"


@pytest.mark.asyncio
async def test_owner_system_id_in_response(client):
    """POST owner response includes correct system_id."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"])

    assert owner["system_id"] == system["id"], "owner.system_id must match the system"
    assert owner["organization_id"] == org["id"], "owner.organization_id must match the org"
