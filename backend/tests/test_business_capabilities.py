"""Tester för /api/v1/capabilities/ — verksamhetsförmågor (Paket A)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org, create_system


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_capability(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testförmåga"),
        "description": overrides.pop("description", None),
        "parent_capability_id": overrides.pop("parent_capability_id", None),
        "capability_owner": overrides.pop("capability_owner", None),
        "maturity_level": overrides.pop("maturity_level", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/capabilities/", json=payload)
    assert resp.status_code == 201, f"create_capability failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    """POST → GET → PATCH → DELETE."""
    org = await create_org(client)
    cap = await _create_capability(client, org["id"], name="Bygglovsförmåga")
    assert cap["name"] == "Bygglovsförmåga"

    get_resp = await client.get(f"/api/v1/capabilities/{cap['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Bygglovsförmåga"

    patch_resp = await client.patch(
        f"/api/v1/capabilities/{cap['id']}",
        json={"name": "Bygglovsförmåga 2.0", "maturity_level": 3},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Bygglovsförmåga 2.0"
    assert patch_resp.json()["maturity_level"] == 3

    del_resp = await client.delete(f"/api/v1/capabilities/{cap['id']}")
    assert del_resp.status_code == 204

    get_after = await client.get(f"/api/v1/capabilities/{cap['id']}")
    assert get_after.status_code == 404


@pytest.mark.asyncio
async def test_list_pagination(client):
    org = await create_org(client)
    await _create_capability(client, org["id"], name="A-förmåga")
    await _create_capability(client, org["id"], name="B-förmåga")

    resp = await client.get(
        "/api/v1/capabilities/",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert {"items", "total", "limit", "offset"} <= set(body.keys())


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    """Förmåga skapad i org A ska inte synas via org B-header."""
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    cap_a = await _create_capability(client, org_a["id"], name="Hemlighet")

    # Org B-header — RLS ska blockera
    resp = await client.get(
        f"/api/v1/capabilities/{cap_a['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_row_created_on_create(client, db_session):
    org = await create_org(client)
    cap = await _create_capability(client, org["id"], name="Audit-test")

    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "business_capabilities",
            text("record_id = :rid"),
        ).params(rid=cap["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_hierarchy_parent_child(client):
    org = await create_org(client)
    parent = await _create_capability(client, org["id"], name="Toppförmåga")
    child = await _create_capability(
        client, org["id"], name="Underförmåga",
        parent_capability_id=parent["id"],
    )
    assert child["parent_capability_id"] == parent["id"]

    # Listfilter på parent
    resp = await client.get(
        "/api/v1/capabilities/",
        params={"parent_capability_id": parent["id"]},
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["items"]]
    assert child["id"] in ids


@pytest.mark.asyncio
async def test_link_capability_to_system(client):
    org = await create_org(client)
    cap = await _create_capability(client, org["id"], name="LänkadFörmåga")
    system = await create_system(client, org["id"])

    link_resp = await client.post(
        f"/api/v1/capabilities/{cap['id']}/systems",
        json={"system_id": system["id"]},
    )
    assert link_resp.status_code == 201

    list_resp = await client.get(f"/api/v1/capabilities/{cap['id']}/systems")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json()]
    assert system["id"] in ids

    # Counts via include_counts
    resp = await client.get(
        "/api/v1/capabilities/",
        params={"organization_id": org["id"], "include_counts": "true"},
    )
    cap_in_list = next(c for c in resp.json()["items"] if c["id"] == cap["id"])
    assert cap_in_list["system_count"] >= 1


@pytest.mark.asyncio
async def test_safe_string_rejects_null_byte(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/capabilities/",
        json={
            "organization_id": org["id"],
            "name": "Något\x00bus",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_maturity_level_constraint(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/capabilities/",
        json={
            "organization_id": org["id"],
            "name": "Förmåga",
            "maturity_level": 9,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/capabilities/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_self_parent_rejected(client):
    org = await create_org(client)
    cap = await _create_capability(client, org["id"], name="Förmåga")
    resp = await client.patch(
        f"/api/v1/capabilities/{cap['id']}",
        json={"parent_capability_id": cap["id"]},
    )
    assert resp.status_code == 422
