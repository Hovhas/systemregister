"""
Tests for /api/v1/integrations and /api/v1/systems/{id}/integrations endpoints.
"""

import pytest
from uuid import uuid4

from tests.factories import create_org, create_system, create_integration


# ---------------------------------------------------------------------------
# Constants used in direct POST calls within tests
# ---------------------------------------------------------------------------

INTEGRATION_BASE = {
    "integration_type": "api",
    "description": "REST-baserad integration",
    "data_types": "personuppgifter",
    "frequency": "realtid",
    "is_external": False,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_integration(client):
    """POST /api/v1/integrations/ returns 201 with correct fields."""
    org = await create_org(client)
    source = await create_system(client, org["id"], name="Procapita")
    target = await create_system(client, org["id"], name="DataLager")

    payload = {
        **INTEGRATION_BASE,
        "source_system_id": source["id"],
        "target_system_id": target["id"],
    }
    resp = await client.post("/api/v1/integrations/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["source_system_id"] == source["id"]
    assert body["target_system_id"] == target["id"]
    assert body["integration_type"] == INTEGRATION_BASE["integration_type"]
    assert body["description"] == INTEGRATION_BASE["description"]
    assert body["is_external"] is False
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_list_integrations(client):
    """GET /api/v1/integrations/ returns all integrations."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"Alfa-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"Beta-{uuid4().hex[:6]}")
    sys_c = await create_system(client, org["id"], name=f"Gamma-{uuid4().hex[:6]}")

    await create_integration(client, sys_a["id"], sys_b["id"])
    await create_integration(client, sys_b["id"], sys_c["id"])

    resp = await client.get("/api/v1/integrations/")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2


@pytest.mark.asyncio
async def test_list_integrations_empty(client):
    """GET /api/v1/integrations/ returns empty list when no integrations exist."""
    resp = await client.get("/api/v1/integrations/")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_filter_integrations_by_system(client):
    """GET /api/v1/integrations/?system_id=... returns only integrations involving that system."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"Filterkälla-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"Brygga-{uuid4().hex[:6]}")
    sys_c = await create_system(client, org["id"], name=f"Destination-{uuid4().hex[:6]}")

    # A -> B (involves A)
    await create_integration(client, sys_a["id"], sys_b["id"])
    # B -> A (also involves A as target)
    await create_integration(client, sys_b["id"], sys_a["id"])
    # B -> C (does NOT involve A)
    await create_integration(client, sys_b["id"], sys_c["id"])

    resp = await client.get("/api/v1/integrations/", params={"system_id": sys_a["id"]})

    assert resp.status_code == 200
    body = resp.json()
    # Only integrations where A is source OR target
    assert len(body) == 2, f"Expected 2 integrations for system A, got {len(body)}"
    for item in body:
        assert item["source_system_id"] == sys_a["id"] or item["target_system_id"] == sys_a["id"], (
            f"Integration {item['id']} does not involve system A"
        )


@pytest.mark.asyncio
async def test_get_integration(client):
    """GET /api/v1/integrations/{id} returns the correct integration."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"GetSrc-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"GetTgt-{uuid4().hex[:6]}")
    created = await create_integration(client, sys_a["id"], sys_b["id"])

    resp = await client.get(f"/api/v1/integrations/{created['id']}")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["id"] == created["id"]
    assert body["source_system_id"] == sys_a["id"]
    assert body["target_system_id"] == sys_b["id"]


@pytest.mark.asyncio
async def test_get_integration_not_found(client):
    """GET /api/v1/integrations/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/integrations/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_integration(client):
    """PATCH /api/v1/integrations/{id} updates fields without touching others."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"PatchSrc-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"PatchTgt-{uuid4().hex[:6]}")
    created = await create_integration(client, sys_a["id"], sys_b["id"])

    patch = {
        "description": "Uppdaterad beskrivning",
        "frequency": "nattlig",
        "criticality": "hög",
    }
    resp = await client.patch(f"/api/v1/integrations/{created['id']}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["description"] == "Uppdaterad beskrivning"
    assert body["frequency"] == "nattlig"
    assert body["criticality"] == "hög"
    # Unchanged fields
    assert body["integration_type"] == INTEGRATION_BASE["integration_type"]
    assert body["source_system_id"] == sys_a["id"]


@pytest.mark.asyncio
async def test_update_integration_not_found(client):
    """PATCH /api/v1/integrations/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/integrations/{fake_id}", json={"description": "X"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_integration(client):
    """DELETE /api/v1/integrations/{id} removes the integration and returns 204."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"DelSrc-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"DelTgt-{uuid4().hex[:6]}")
    created = await create_integration(client, sys_a["id"], sys_b["id"])
    integration_id = created["id"]

    delete_resp = await client.delete(f"/api/v1/integrations/{integration_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    get_resp = await client.get(f"/api/v1/integrations/{integration_id}")
    assert get_resp.status_code == 404, "integration should be gone after delete"


@pytest.mark.asyncio
async def test_delete_integration_not_found(client):
    """DELETE /api/v1/integrations/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/integrations/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_system_integrations(client):
    """GET /api/v1/systems/{id}/integrations returns both inbound and outbound integrations."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"ListSysA-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"ListSysB-{uuid4().hex[:6]}")
    sys_c = await create_system(client, org["id"], name=f"ListSysC-{uuid4().hex[:6]}")

    # A -> B (outbound from A)
    await create_integration(client, sys_a["id"], sys_b["id"])
    # C -> A (inbound to A)
    await create_integration(client, sys_c["id"], sys_a["id"])
    # B -> C (no A involvement)
    await create_integration(client, sys_b["id"], sys_c["id"])

    resp = await client.get(f"/api/v1/systems/{sys_a['id']}/integrations")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert len(body) == 2, f"Expected 2 integrations (1 in + 1 out), got {len(body)}"

    source_ids = {item["source_system_id"] for item in body}
    target_ids = {item["target_system_id"] for item in body}
    # A should appear as either source or target in all returned integrations
    for item in body:
        assert item["source_system_id"] == sys_a["id"] or item["target_system_id"] == sys_a["id"], (
            f"Integration {item['id']} does not involve system A"
        )


@pytest.mark.asyncio
async def test_list_system_integrations_invalid_system(client):
    """GET /api/v1/systems/{id}/integrations with non-existent system returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/systems/{fake_id}/integrations")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_integration_invalid_type(client):
    """POST integration with unknown integration_type returns 422."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"InvTypeSrc-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"InvTypeTgt-{uuid4().hex[:6]}")

    payload = {
        **INTEGRATION_BASE,
        "source_system_id": sys_a["id"],
        "target_system_id": sys_b["id"],
        "integration_type": "okänd_typ",
    }
    resp = await client.post("/api/v1/integrations/", json=payload)

    assert resp.status_code == 422, f"Expected 422 for invalid type, got {resp.status_code}"


@pytest.mark.asyncio
async def test_create_integration_invalid_source_system(client):
    """POST integration with non-existent source_system_id returns 404."""
    org = await create_org(client)
    sys_b = await create_system(client, org["id"], name="System B")
    fake_id = "00000000-0000-0000-0000-000000000000"

    payload = {
        **INTEGRATION_BASE,
        "source_system_id": fake_id,
        "target_system_id": sys_b["id"],
    }
    resp = await client.post("/api/v1/integrations/", json=payload)

    assert resp.status_code == 404, f"Expected 404 for invalid source system, got {resp.status_code}"


@pytest.mark.asyncio
async def test_filter_integrations_by_type(client):
    """GET /api/v1/integrations/?integration_type=... filters by type."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name=f"FltTypSrc-{uuid4().hex[:6]}")
    sys_b = await create_system(client, org["id"], name=f"FltTypMid-{uuid4().hex[:6]}")
    sys_c = await create_system(client, org["id"], name=f"FltTypTgt-{uuid4().hex[:6]}")

    await create_integration(client, sys_a["id"], sys_b["id"], integration_type="api")
    await create_integration(client, sys_b["id"], sys_c["id"], integration_type="filöverföring")

    resp = await client.get("/api/v1/integrations/", params={"integration_type": "api"})

    assert resp.status_code == 200
    body = resp.json()
    assert all(item["integration_type"] == "api" for item in body), (
        "All returned integrations should be of type 'api'"
    )
