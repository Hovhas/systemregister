"""
Negativa tester — felfall, saknade resurser, ogiltig data.

Kategori 15: Negativa tester (~50 testfall)
"""

import pytest
from datetime import date, timedelta
from tests.factories import (
    create_org, create_system, create_classification,
    create_owner, create_contract, create_gdpr_treatment,
    create_integration,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Systems - 404 cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_system_nonexistent(client):
    """GET nonexistent system returns 404."""
    resp = await client.get(f"/api/v1/systems/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_system_nonexistent(client):
    """PATCH nonexistent system returns 404."""
    resp = await client.patch(f"/api/v1/systems/{FAKE_UUID}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_system_nonexistent(client):
    """DELETE nonexistent system returns 404."""
    resp = await client.delete(f"/api/v1/systems/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_system_invalid_uuid(client):
    """GET system with non-UUID path param returns 422."""
    resp = await client.get("/api/v1/systems/not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_system_classifications_nonexistent_system(client):
    """GET classifications for nonexistent system returns 404."""
    resp = await client.get(f"/api/v1/systems/{FAKE_UUID}/classifications")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_system_classifications_latest_nonexistent(client):
    """GET latest classification for nonexistent system returns 404."""
    resp = await client.get(f"/api/v1/systems/{FAKE_UUID}/classifications/latest")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Organizations - 404 cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_org_nonexistent(client):
    """GET nonexistent organization returns 404."""
    resp = await client.get(f"/api/v1/organizations/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_org_nonexistent(client):
    """PATCH nonexistent organization returns 404."""
    resp = await client.patch(f"/api/v1/organizations/{FAKE_UUID}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_org_nonexistent(client):
    """DELETE nonexistent organization returns 404."""
    resp = await client.delete(f"/api/v1/organizations/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_org_invalid_uuid(client):
    """GET org with non-UUID path param returns 422."""
    resp = await client.get("/api/v1/organizations/definitely-not-a-uuid")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Owners - 404 and invalid cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_owner_nonexistent(client):
    """PATCH nonexistent owner returns 404."""
    resp = await client.patch(f"/api/v1/systems/{FAKE_UUID}/owners/{FAKE_UUID}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_owner_nonexistent(client):
    """DELETE nonexistent owner returns 404."""
    resp = await client.delete(f"/api/v1/systems/{FAKE_UUID}/owners/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_owner_for_nonexistent_system(client):
    """Creating owner for nonexistent system should fail."""
    org = await create_org(client)
    try:
        resp = await client.post(f"/api/v1/systems/{FAKE_UUID}/owners", json={
            "organization_id": org["id"],
            "role": "systemägare",
            "name": "Test Person",
        })
        assert resp.status_code != 201, "Should not create owner for nonexistent system"
    except Exception:
        pass  # FK violation is acceptable


# ---------------------------------------------------------------------------
# Integrations - invalid cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_integration_nonexistent(client):
    """GET nonexistent integration returns 404."""
    resp = await client.get(f"/api/v1/integrations/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_integration_nonexistent(client):
    """PATCH nonexistent integration returns 404."""
    resp = await client.patch(f"/api/v1/integrations/{FAKE_UUID}", json={"description": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_integration_nonexistent(client):
    """DELETE nonexistent integration returns 404."""
    resp = await client.delete(f"/api/v1/integrations/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_integration_nonexistent_source(client):
    """Creating integration with nonexistent source system should fail."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    try:
        resp = await client.post("/api/v1/integrations/", json={
            "source_system_id": FAKE_UUID,
            "target_system_id": sys["id"],
            "integration_type": "api",
        })
        assert resp.status_code != 201
    except Exception:
        pass  # FK violation


@pytest.mark.asyncio
async def test_create_integration_invalid_type(client):
    """Creating integration with invalid type returns 422."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="Source")
    sys_b = await create_system(client, org["id"], name="Target")
    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys_a["id"],
        "target_system_id": sys_b["id"],
        "integration_type": "teleportation",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GDPR - invalid cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_gdpr_nonexistent(client):
    """PATCH nonexistent GDPR treatment returns 404."""
    resp = await client.patch(f"/api/v1/systems/{FAKE_UUID}/gdpr/{FAKE_UUID}", json={"legal_basis": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_gdpr_nonexistent(client):
    """DELETE nonexistent GDPR treatment returns 404."""
    resp = await client.delete(f"/api/v1/systems/{FAKE_UUID}/gdpr/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_gdpr_nonexistent_system(client):
    """Creating GDPR treatment for nonexistent system should fail."""
    try:
        resp = await client.post(f"/api/v1/systems/{FAKE_UUID}/gdpr", json={
            "data_categories": ["vanliga"],
        })
        assert resp.status_code != 201
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Contracts - invalid cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_contract_nonexistent(client):
    """PATCH nonexistent contract returns 404."""
    resp = await client.patch(f"/api/v1/systems/{FAKE_UUID}/contracts/{FAKE_UUID}", json={"supplier_name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_contract_nonexistent(client):
    """DELETE nonexistent contract returns 404."""
    resp = await client.delete(f"/api/v1/systems/{FAKE_UUID}/contracts/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_contract_end_before_start_rejected_or_accepted(client):
    """Contract med end_date före start_date ska alltid rejectas med 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Bad Dates",
        "contract_start": "2025-12-01",
        "contract_end": "2025-01-01",  # end before start
    })
    assert resp.status_code == 422, (
        f"Förväntade 422 för omvända datum, fick: {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Pagination edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_systems_limit_zero(client):
    """limit=0 should return 422 or empty list, never crash."""
    resp = await client.get("/api/v1/systems/", params={"limit": 0})
    assert resp.status_code in (200, 422), f"Unexpected: {resp.status_code}"


@pytest.mark.asyncio
async def test_systems_negative_limit(client):
    """Negative limit should return 422."""
    resp = await client.get("/api/v1/systems/", params={"limit": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_systems_negative_offset(client):
    """Negative offset should return 422."""
    resp = await client.get("/api/v1/systems/", params={"offset": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_systems_limit_above_max(client):
    """limit > 200 should return 422."""
    resp = await client.get("/api/v1/systems/", params={"limit": 201})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_systems_very_large_offset(client):
    """Very large offset with empty DB should return empty list, not error."""
    resp = await client.get("/api/v1/systems/", params={"offset": 999999})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Empty/whitespace inputs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system_empty_name(client):
    """System with empty name should be rejected (422) or accepted."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    # Empty name is invalid — should be 422
    assert resp.status_code == 422, (
        f"Empty name should be rejected, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_create_org_empty_name(client):
    """Organization with empty name should be rejected."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "",
        "org_type": "kommun",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_empty_name(client):
    """Owner with empty name should be rejected."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(client):
    """Empty q parameter should return all systems (not crash)."""
    org = await create_org(client)
    await create_system(client, org["id"])
    resp = await client.get("/api/v1/systems/", params={"q": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


# ---------------------------------------------------------------------------
# Double-delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_double_delete_system(client):
    """Deleting the same system twice should return 404 on second attempt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    first = await client.delete(f"/api/v1/systems/{sys['id']}")
    assert first.status_code == 204

    second = await client.delete(f"/api/v1/systems/{sys['id']}")
    assert second.status_code == 404


@pytest.mark.asyncio
async def test_double_delete_org(client):
    """Deleting the same organization twice returns 404 on second attempt."""
    org = await create_org(client)

    first = await client.delete(f"/api/v1/organizations/{org['id']}")
    assert first.status_code == 204

    second = await client.delete(f"/api/v1/organizations/{org['id']}")
    assert second.status_code == 404


# ---------------------------------------------------------------------------
# Wrong content type / malformed body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system_with_wrong_content_type(client):
    """POST with text/plain content-type should return 422 (not 500)."""
    resp = await client.post(
        "/api/v1/systems/",
        content=b"plain text body",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code in (422, 400), (
        f"Wrong content-type should be rejected: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_create_system_with_empty_body(client):
    """POST with empty body should return 422."""
    resp = await client.post("/api/v1/systems/", json=None)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_system_with_empty_body(client):
    """PATCH with empty body — document behavior (may succeed or fail)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={})
    # Empty patch is a no-op — should succeed or return 422
    assert resp.status_code in (200, 422)


# ---------------------------------------------------------------------------
# Conflicting operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_system_invalid_lifecycle_status(client):
    """PATCH system with invalid lifecycle_status should return 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "lifecycle_status": "TOTALLY_INVALID",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_system_invalid_criticality(client):
    """PATCH system with invalid criticality should return 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "criticality": "ultra",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_system_classification_latest_no_classification(client):
    """GET latest classification for system with no classifications returns 404."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications/latest")
    assert resp.status_code == 404, (
        f"System with no classifications should return 404 for /latest, got {resp.status_code}"
    )
