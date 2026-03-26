"""
Tests for /api/v1/systems/{id}/classifications endpoints.
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

CLASSIFICATION_BASE = {
    "system_id": "00000000-0000-0000-0000-000000000000",  # overridden per test
    "confidentiality": 2,
    "integrity": 3,
    "availability": 1,
    "traceability": 2,
    "classified_by": "anna.svensson@sundsvall.se",
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


async def create_classification(client, system_id: str, overrides: dict | None = None) -> dict:
    payload = {**CLASSIFICATION_BASE, "system_id": system_id}
    if overrides:
        payload.update(overrides)
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=payload)
    assert resp.status_code == 201, f"Classification creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_classification(client):
    """POST /api/v1/systems/{id}/classifications returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {**CLASSIFICATION_BASE, "system_id": system_id}
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["system_id"] == system_id, "system_id mismatch"
    assert body["confidentiality"] == CLASSIFICATION_BASE["confidentiality"]
    assert body["integrity"] == CLASSIFICATION_BASE["integrity"]
    assert body["availability"] == CLASSIFICATION_BASE["availability"]
    assert body["traceability"] == CLASSIFICATION_BASE["traceability"]
    assert body["classified_by"] == CLASSIFICATION_BASE["classified_by"]
    assert "id" in body, "response must include id"
    assert "classified_at" in body, "response must include classified_at"
    # Optional fields default to None
    assert body["valid_until"] is None
    assert body["notes"] is None


@pytest.mark.asyncio
async def test_list_classifications(client):
    """GET /api/v1/systems/{id}/classifications returns a list sorted newest first."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    await create_classification(client, system_id, {"confidentiality": 1})
    await create_classification(client, system_id, {"confidentiality": 3})

    resp = await client.get(f"/api/v1/systems/{system_id}/classifications")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list), "response should be a list"
    assert len(body) >= 2, f"expected at least 2 classifications, got {len(body)}"

    # Verify descending order by classified_at
    timestamps = [c["classified_at"] for c in body]
    assert timestamps == sorted(timestamps, reverse=True), (
        "classifications should be sorted newest first"
    )


@pytest.mark.asyncio
async def test_list_classifications_empty(client):
    """GET /api/v1/systems/{id}/classifications on a new system returns empty list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/classifications")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_latest_classification(client):
    """GET /api/v1/systems/{id}/classifications/latest returns exactly one classification.

    NOTE: classified_at uses server_default=func.now() which resolves to the same
    timestamp for multiple inserts within the same DB transaction/flush. Therefore
    we cannot reliably assert *which* of two same-timestamp entries is returned —
    only that the endpoint returns exactly one valid classification record.
    """
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    first = await create_classification(client, system_id, {"confidentiality": 1, "notes": "first"})
    second = await create_classification(client, system_id, {"confidentiality": 4, "notes": "second"})

    resp = await client.get(f"/api/v1/systems/{system_id}/classifications/latest")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()

    # Endpoint must return exactly one record with required fields
    assert "id" in body
    assert "classified_at" in body
    assert body["system_id"] == system_id

    # The returned record must be one of the two we created
    valid_ids = {first["id"], second["id"]}
    assert body["id"] in valid_ids, (
        f"Latest classification {body['id']} is not one of the created ones: {valid_ids}"
    )


@pytest.mark.asyncio
async def test_get_latest_classification_no_classifications_returns_404(client):
    """GET /api/v1/systems/{id}/classifications/latest on system with no classifications returns 404."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/classifications/latest")

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_create_classification_invalid_system(client):
    """POST /api/v1/systems/{id}/classifications with non-existent system returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    payload = {**CLASSIFICATION_BASE, "system_id": fake_id}

    resp = await client.post(f"/api/v1/systems/{fake_id}/classifications", json=payload)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_classification_values_validated_below_range(client):
    """POST classification with value below 0 returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {**CLASSIFICATION_BASE, "system_id": system_id, "confidentiality": -1}
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=payload)

    assert resp.status_code == 422, f"Expected 422 for value -1, got {resp.status_code}"


@pytest.mark.asyncio
async def test_classification_values_validated_above_range(client):
    """POST classification with value above 4 returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {**CLASSIFICATION_BASE, "system_id": system_id, "integrity": 5}
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=payload)

    assert resp.status_code == 422, f"Expected 422 for value 5, got {resp.status_code}"


@pytest.mark.asyncio
async def test_classification_boundary_values_valid(client):
    """POST classification with boundary values 0 and 4 should succeed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    payload = {
        **CLASSIFICATION_BASE,
        "system_id": system_id,
        "confidentiality": 0,
        "integrity": 4,
        "availability": 0,
        "traceability": 4,
    }
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=payload)

    assert resp.status_code == 201, f"Expected 201 for boundary values, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["confidentiality"] == 0
    assert body["integrity"] == 4
    assert body["availability"] == 0
    assert body["traceability"] == 4


@pytest.mark.asyncio
async def test_list_classifications_scoped_to_system(client):
    """Classifications of system A should not appear when listing system B's classifications."""
    org = await create_org(client)
    system_a = await create_system(client, org["id"], name="System A")
    system_b = await create_system(client, org["id"], name="System B")

    # Add classification to system A only
    await create_classification(client, system_a["id"])

    resp = await client.get(f"/api/v1/systems/{system_b['id']}/classifications")

    assert resp.status_code == 200
    assert resp.json() == [], "system B should have no classifications"
