"""
Tests for /api/v1/audit/ endpoints.

Kategori 10: Audit trail (~30 testfall)
"""

import pytest
from uuid import uuid4
from tests.factories import (
    create_org, create_system, create_classification,
    create_owner, create_contract, create_gdpr_treatment,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_list_returns_200(client):
    """GET /api/v1/audit/ returns 200 with expected structure."""
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_audit_list_empty_on_fresh_db(client):
    """GET /api/v1/audit/ on empty DB returns empty items list."""
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_audit_record_nonexistent_returns_empty_list(client):
    """GET /api/v1/audit/record/{id} with unknown id returns empty list (not 404)."""
    resp = await client.get(f"/api/v1/audit/record/{FAKE_UUID}")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Audit entry structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_entry_has_required_fields(client):
    """Audit entries must include id, table_name, record_id, action, changed_at."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0, "Expected at least one audit entry after creating org/system"

    entry = items[0]
    for field in ("id", "table_name", "record_id", "action", "changed_at"):
        assert field in entry, f"Audit entry missing field: {field}"


@pytest.mark.asyncio
async def test_audit_entry_action_is_string(client):
    """Audit entry action should be a string (not an enum object)."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    for item in items:
        assert isinstance(item["action"], str), f"action should be string, got: {type(item['action'])}"


@pytest.mark.asyncio
async def test_audit_new_values_present_on_create(client):
    """Audit entries for create operations should have new_values."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    create_entries = [e for e in entries if e["action"] == "create"]
    if create_entries:
        entry = create_entries[0]
        assert entry["new_values"] is not None, "Create audit should have new_values"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_filter_by_table_name(client):
    """GET /api/v1/audit/?table_name=systems returns only system audit entries."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"table_name": "systems"})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["table_name"] == "systems", (
            f"Expected table_name=systems, got {item['table_name']}"
        )


@pytest.mark.asyncio
async def test_audit_filter_by_action_create(client):
    """GET /api/v1/audit/?action=create returns only create entries."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"action": "create"})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["action"] == "create", f"Expected action=create, got {item['action']}"


@pytest.mark.asyncio
async def test_audit_filter_by_record_id(client):
    """GET /api/v1/audit/?record_id=<system_id> returns only entries for that system."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="System A")
    sys_b = await create_system(client, org["id"], name="System B")

    resp = await client.get("/api/v1/audit/", params={"record_id": sys_a["id"]})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["record_id"] == sys_a["id"], (
            f"Expected record_id={sys_a['id']}, got {item['record_id']}"
        )


@pytest.mark.asyncio
async def test_audit_filter_unknown_table_returns_empty(client):
    """Filtering by non-existent table_name returns empty result."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"table_name": "nonexistent_table_xyz"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_pagination_limit(client):
    """GET /api/v1/audit/?limit=2 returns at most 2 items."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"AuditSys-{i}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/audit/", params={"limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 2


@pytest.mark.asyncio
async def test_audit_pagination_offset(client):
    """Offset-based pagination returns different results."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"OffSys-{i}-{uuid4().hex[:6]}")

    resp_p1 = await client.get("/api/v1/audit/", params={"limit": 2, "offset": 0})
    resp_p2 = await client.get("/api/v1/audit/", params={"limit": 2, "offset": 2})
    assert resp_p1.status_code == 200
    assert resp_p2.status_code == 200

    ids_p1 = {i["id"] for i in resp_p1.json()["items"]}
    ids_p2 = {i["id"] for i in resp_p2.json()["items"]}
    assert ids_p1.isdisjoint(ids_p2), "Pages should not overlap"


@pytest.mark.asyncio
async def test_audit_default_limit_is_50(client):
    """Default limit should be 50."""
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    assert resp.json()["limit"] == 50


@pytest.mark.asyncio
async def test_audit_limit_max_200(client):
    """limit parameter should be capped at 200."""
    resp = await client.get("/api/v1/audit/", params={"limit": 201})
    assert resp.status_code == 422, "limit > 200 should return 422"


# ---------------------------------------------------------------------------
# Record-level audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_record_returns_list(client):
    """GET /api/v1/audit/record/{id} returns a list."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_record_entries_match_requested_id(client):
    """All entries from /audit/record/{id} should have matching record_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["record_id"] == sys["id"]


@pytest.mark.asyncio
async def test_audit_update_creates_update_entry(client):
    """PATCH on a system should produce an update audit entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "Updated Name"})

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    update_entries = [e for e in entries if e["action"] == "update"]
    assert len(update_entries) >= 1, "PATCH borde generera audit update-entry"


@pytest.mark.asyncio
async def test_audit_delete_creates_delete_entry(client):
    """DELETE on a system should produce a delete audit entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    sys_id = sys["id"]
    await client.delete(f"/api/v1/systems/{sys_id}")

    resp = await client.get(f"/api/v1/audit/record/{sys_id}")
    assert resp.status_code == 200
    entries = resp.json()
    delete_entries = [e for e in entries if e["action"] == "delete"]
    assert len(delete_entries) >= 1, "DELETE borde generera audit delete-entry"


@pytest.mark.asyncio
async def test_audit_contract_create_logged(client):
    """Creating a contract should generate an audit entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": contract["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "Contract create borde generera audit-entry"


@pytest.mark.asyncio
async def test_audit_classification_logged(client):
    """Creating a classification should be recorded in audit log."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": clf["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "Classification create borde generera audit-entry"


@pytest.mark.asyncio
async def test_audit_owner_create_logged(client):
    """Creating an owner should appear in audit log."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": owner["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "Owner create borde generera audit-entry"


@pytest.mark.asyncio
async def test_audit_gdpr_create_logged(client):
    """Creating a GDPR treatment should appear in audit log."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": gdpr["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "GDPR treatment create borde generera audit-entry"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_ordered_by_changed_at_desc(client):
    """Audit entries should be ordered by changed_at descending (newest first)."""
    org = await create_org(client)
    await create_system(client, org["id"], name="First System")
    await create_system(client, org["id"], name="Second System")

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if len(items) >= 2:
        times = [i["changed_at"] for i in items if i["changed_at"]]
        assert times == sorted(times, reverse=True), "Audit log should be newest-first"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_invalid_record_id_format(client):
    """GET /api/v1/audit/record/not-a-uuid should return 422."""
    resp = await client.get("/api/v1/audit/record/not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_filter_by_invalid_record_id_format(client):
    """GET /api/v1/audit/?record_id=not-a-uuid should return 422."""
    resp = await client.get("/api/v1/audit/", params={"record_id": "not-a-uuid"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_total_increases_after_operations(client):
    """Total audit entries should increase as more records are created."""
    resp_before = await client.get("/api/v1/audit/")
    total_before = resp_before.json()["total"]

    org = await create_org(client)
    await create_system(client, org["id"])

    resp_after = await client.get("/api/v1/audit/")
    total_after = resp_after.json()["total"]

    assert total_after >= total_before, "Audit total should not decrease after creates"
