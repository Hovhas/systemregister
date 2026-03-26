"""
Tests for /api/v1/systems/{id}/gdpr and /api/v1/gdpr/{id} endpoints.
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
    "name": "Lifecare",
    "description": "Verksamhetssystem för hälso- och sjukvård",
    "system_category": "verksamhetssystem",
}

GDPR_BASE = {
    "ropa_reference_id": "ROPA-2024-001",
    "data_categories": ["vanliga", "känsliga_art9"],
    "categories_of_data_subjects": "medborgare, patienter",
    "legal_basis": "Artikel 9.2(h) – hälso- och sjukvård",
    "data_processor": "CGI Sverige AB",
    "processor_agreement_status": "ja",
    "sub_processors": ["Amazon Web Services"],
    "third_country_transfer_details": None,
    "retention_policy": "7 år efter senaste kontakt",
    "dpia_conducted": True,
    "dpia_date": "2024-03-15",
    "dpia_link": "https://gdpr.sundsvall.se/dpia/lifecare",
}


async def create_org(client) -> dict:
    resp = await client.post("/api/v1/organizations/", json=ORG_PAYLOAD)
    assert resp.status_code == 201, f"Org creation failed: {resp.text}"
    return resp.json()


async def create_system(client, org_id: str, name: str = "Lifecare", overrides: dict | None = None) -> dict:
    payload = {**SYSTEM_BASE, "organization_id": org_id, "name": name}
    if overrides:
        payload.update(overrides)
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 201, f"System creation failed: {resp.text}"
    return resp.json()


async def create_gdpr_treatment(client, system_id: str, overrides: dict | None = None) -> dict:
    payload = {**GDPR_BASE}
    if overrides:
        payload.update(overrides)
    resp = await client.post(f"/api/v1/systems/{system_id}/gdpr", json=payload)
    assert resp.status_code == 201, f"GDPR treatment creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_gdpr_treatment(client):
    """POST /api/v1/systems/{id}/gdpr returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    resp = await client.post(f"/api/v1/systems/{system_id}/gdpr", json=GDPR_BASE)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["system_id"] == system_id
    assert body["ropa_reference_id"] == GDPR_BASE["ropa_reference_id"]
    assert body["data_categories"] == GDPR_BASE["data_categories"]
    assert body["legal_basis"] == GDPR_BASE["legal_basis"]
    assert body["data_processor"] == GDPR_BASE["data_processor"]
    assert body["processor_agreement_status"] == GDPR_BASE["processor_agreement_status"]
    assert body["dpia_conducted"] is True
    assert body["dpia_date"] == GDPR_BASE["dpia_date"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_gdpr_treatment_minimal(client):
    """POST GDPR treatment with only required fields (all optional) should succeed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={})

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["ropa_reference_id"] is None
    assert body["data_categories"] is None
    assert body["dpia_conducted"] is False


@pytest.mark.asyncio
async def test_list_gdpr_treatments(client):
    """GET /api/v1/systems/{id}/gdpr returns list of treatments."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    await create_gdpr_treatment(client, system_id, {"ropa_reference_id": "ROPA-001"})
    await create_gdpr_treatment(client, system_id, {"ropa_reference_id": "ROPA-002"})

    resp = await client.get(f"/api/v1/systems/{system_id}/gdpr")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2, f"Expected at least 2 treatments, got {len(body)}"
    ropa_ids = [t["ropa_reference_id"] for t in body]
    assert "ROPA-001" in ropa_ids
    assert "ROPA-002" in ropa_ids


@pytest.mark.asyncio
async def test_list_gdpr_treatments_empty(client):
    """GET /api/v1/systems/{id}/gdpr on new system returns empty list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/gdpr")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_gdpr_treatment(client):
    """PATCH /api/v1/gdpr/{id} updates fields without touching others."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"])
    treatment_id = treatment["id"]

    patch = {
        "legal_basis": "Artikel 6.1(e) – allmänt intresse",
        "dpia_conducted": False,
        "retention_policy": "5 år",
    }
    resp = await client.patch(f"/api/v1/gdpr/{treatment_id}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["legal_basis"] == "Artikel 6.1(e) – allmänt intresse"
    assert body["dpia_conducted"] is False
    assert body["retention_policy"] == "5 år"
    # Unpatched fields should remain
    assert body["ropa_reference_id"] == GDPR_BASE["ropa_reference_id"]
    assert body["data_processor"] == GDPR_BASE["data_processor"]
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_update_gdpr_treatment_not_found(client):
    """PATCH /api/v1/gdpr/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/gdpr/{fake_id}", json={"legal_basis": "test"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_gdpr_treatment(client):
    """DELETE /api/v1/gdpr/{id} removes treatment and returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"])
    treatment_id = treatment["id"]

    delete_resp = await client.delete(f"/api/v1/gdpr/{treatment_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    # Verify it's gone from the system's list
    list_resp = await client.get(f"/api/v1/systems/{system['id']}/gdpr")
    assert list_resp.status_code == 200
    ids = [t["id"] for t in list_resp.json()]
    assert treatment_id not in ids, "Deleted treatment should not appear in list"


@pytest.mark.asyncio
async def test_delete_gdpr_treatment_not_found(client):
    """DELETE /api/v1/gdpr/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/gdpr/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_gdpr_invalid_system(client):
    """POST /api/v1/systems/{id}/gdpr with non-existent system returns 404."""
    fake_system_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/systems/{fake_system_id}/gdpr", json=GDPR_BASE)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_gdpr_treatments_scoped_to_system(client):
    """GDPR treatments added to system A should not appear in system B's list."""
    org = await create_org(client)
    system_a = await create_system(client, org["id"], name="System A")
    system_b = await create_system(client, org["id"], name="System B")

    await create_gdpr_treatment(client, system_a["id"])

    resp = await client.get(f"/api/v1/systems/{system_b['id']}/gdpr")
    assert resp.status_code == 200
    assert resp.json() == [], "System B should have no GDPR treatments"


@pytest.mark.asyncio
async def test_create_gdpr_invalid_processor_status(client):
    """POST GDPR treatment with invalid processor_agreement_status returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    payload = {**GDPR_BASE, "processor_agreement_status": "okänd_status"}
    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json=payload)

    assert resp.status_code == 422, f"Expected 422 for invalid enum, got {resp.status_code}"
