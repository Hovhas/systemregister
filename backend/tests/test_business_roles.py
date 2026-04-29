"""Tester för /api/v1/business-roles/ (Paket C)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org, create_system


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_role(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Bygglovshandläggare"),
        "description": overrides.pop("description", None),
        "role_owner": overrides.pop("role_owner", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/business-roles/", json=payload)
    assert resp.status_code == 201, f"create_role failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"], name="Lärare")
    assert role["name"] == "Lärare"

    patch_resp = await client.patch(
        f"/api/v1/business-roles/{role['id']}",
        json={"description": "Undervisar elever"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Undervisar elever"

    del_resp = await client.delete(f"/api/v1/business-roles/{role['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    role = await _create_role(client, org_a["id"])
    resp = await client.get(
        f"/api/v1/business-roles/{role['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_row_created(client, db_session):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "business_roles",
            text("record_id = :rid"),
        ).params(rid=role["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_safe_string_rejects_null_byte(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/business-roles/",
        json={"organization_id": org["id"], "name": "Roll\x00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_role_systems_endpoint(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    system = await create_system(client, org["id"])
    # Skapa via /role-access
    resp = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "läs",
            "access_type": "grundbehörighet",
        },
    )
    assert resp.status_code == 201

    listed = await client.get(f"/api/v1/business-roles/{role['id']}/systems")
    assert listed.status_code == 200
    items = listed.json()
    assert any(item["system_id"] == system["id"] for item in items)


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/business-roles/{FAKE_UUID}")
    assert resp.status_code == 404
