"""Tester för /api/v1/positions/ (Paket C)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_org_unit(client, org_id: str, name: str = "Enhet") -> dict:
    resp = await client.post(
        "/api/v1/org-units/",
        json={"organization_id": str(org_id), "name": name, "unit_type": "förvaltning"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_position(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "title": overrides.pop("title", "Handläggare"),
        "org_unit_id": overrides.pop("org_unit_id", None),
        "position_code": overrides.pop("position_code", None),
        "description": overrides.pop("description", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/positions/", json=payload)
    assert resp.status_code == 201, f"create_position failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    pos = await _create_position(client, org["id"], title="Bygglovshandläggare")
    assert pos["title"] == "Bygglovshandläggare"

    patch_resp = await client.patch(
        f"/api/v1/positions/{pos['id']}",
        json={"position_code": "AID-101"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["position_code"] == "AID-101"

    del_resp = await client.delete(f"/api/v1/positions/{pos['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    pos = await _create_position(client, org_a["id"])
    resp = await client.get(
        f"/api/v1/positions/{pos['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_to_org_unit(client):
    org = await create_org(client)
    unit = await _create_org_unit(client, org["id"], name="Bygglov")
    pos = await _create_position(client, org["id"], org_unit_id=unit["id"])
    assert pos["org_unit_id"] == unit["id"]


@pytest.mark.asyncio
async def test_audit_row_created(client, db_session):
    org = await create_org(client)
    pos = await _create_position(client, org["id"])
    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "positions",
            text("record_id = :rid"),
        ).params(rid=pos["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_invalid_org_unit_rejected(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/positions/",
        json={
            "organization_id": org["id"],
            "title": "Handläggare",
            "org_unit_id": FAKE_UUID,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/positions/{FAKE_UUID}")
    assert resp.status_code == 404
