"""Tester för /api/v1/org-units/ — organisationsenheter (Paket A)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_unit(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testenhet"),
        "parent_unit_id": overrides.pop("parent_unit_id", None),
        "unit_type": overrides.pop("unit_type", "förvaltning"),
        "manager_name": overrides.pop("manager_name", None),
        "cost_center": overrides.pop("cost_center", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/org-units/", json=payload)
    assert resp.status_code == 201, f"create_unit failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    unit = await _create_unit(
        client, org["id"], name="Stadsbyggnadskontoret",
        unit_type="förvaltning", cost_center="42",
    )
    assert unit["name"] == "Stadsbyggnadskontoret"
    assert unit["unit_type"] == "förvaltning"

    patch_resp = await client.patch(
        f"/api/v1/org-units/{unit['id']}",
        json={"manager_name": "Anna Andersson"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["manager_name"] == "Anna Andersson"

    del_resp = await client.delete(f"/api/v1/org-units/{unit['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_hierarchy(client):
    org = await create_org(client)
    parent = await _create_unit(client, org["id"], name="Förvaltningen", unit_type="förvaltning")
    child = await _create_unit(
        client, org["id"], name="Bygglovsenheten",
        unit_type="enhet", parent_unit_id=parent["id"],
    )
    assert child["parent_unit_id"] == parent["id"]


@pytest.mark.asyncio
async def test_tree_endpoint(client):
    org = await create_org(client)
    parent = await _create_unit(client, org["id"], name="Toppen", unit_type="förvaltning")
    child = await _create_unit(
        client, org["id"], name="Mellan",
        unit_type="avdelning", parent_unit_id=parent["id"],
    )
    grandchild = await _create_unit(
        client, org["id"], name="Botten",
        unit_type="enhet", parent_unit_id=child["id"],
    )

    resp = await client.get(
        "/api/v1/org-units/tree",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Toppen"
    assert tree[0]["children"][0]["name"] == "Mellan"
    assert tree[0]["children"][0]["children"][0]["name"] == "Botten"


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    unit = await _create_unit(client, org_a["id"], name="HemligEnhet")

    resp = await client.get(
        f"/api/v1/org-units/{unit['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_row_created(client, db_session):
    org = await create_org(client)
    unit = await _create_unit(client, org["id"])

    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "org_units",
            text("record_id = :rid"),
        ).params(rid=unit["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_safe_string_rejects_null_byte(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/org-units/",
        json={
            "organization_id": org["id"],
            "name": "Enhet\x00",
            "unit_type": "förvaltning",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_unit_type_rejected(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/org-units/",
        json={
            "organization_id": org["id"],
            "name": "Enhet",
            "unit_type": "obekant_typ",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_self_parent_rejected(client):
    org = await create_org(client)
    unit = await _create_unit(client, org["id"])
    resp = await client.patch(
        f"/api/v1/org-units/{unit['id']}",
        json={"parent_unit_id": unit["id"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/org-units/{FAKE_UUID}")
    assert resp.status_code == 404
