"""Tester för /api/v1/value-streams/ — värdeströmmar (Paket A)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_value_stream(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testvärdeström"),
        "description": overrides.pop("description", None),
        "stages": overrides.pop("stages", []),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/value-streams/", json=payload)
    assert resp.status_code == 201, f"create_value_stream failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    vs = await _create_value_stream(
        client, org["id"], name="Bli ny invånare",
        stages=[
            {"name": "Anmäl flytt", "description": None, "order": 0},
            {"name": "Folkbokföring", "description": None, "order": 1},
        ],
    )
    assert vs["name"] == "Bli ny invånare"
    assert len(vs["stages"]) == 2

    patch_resp = await client.patch(
        f"/api/v1/value-streams/{vs['id']}",
        json={"description": "Uppdaterad beskrivning"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["description"] == "Uppdaterad beskrivning"

    del_resp = await client.delete(f"/api/v1/value-streams/{vs['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    vs = await _create_value_stream(client, org_a["id"], name="HemligVS")

    resp = await client.get(
        f"/api/v1/value-streams/{vs['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_row_created(client, db_session):
    org = await create_org(client)
    vs = await _create_value_stream(client, org["id"])

    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "value_streams",
            text("record_id = :rid"),
        ).params(rid=vs["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_update_stages(client):
    org = await create_org(client)
    vs = await _create_value_stream(client, org["id"], stages=[])
    resp = await client.patch(
        f"/api/v1/value-streams/{vs['id']}",
        json={"stages": [{"name": "Steg 1", "description": "X", "order": 0}]},
    )
    assert resp.status_code == 200
    assert resp.json()["stages"][0]["name"] == "Steg 1"


@pytest.mark.asyncio
async def test_safe_string_rejects_null_byte(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/value-streams/",
        json={"organization_id": org["id"], "name": "VS\x00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/value-streams/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_org(client):
    org = await create_org(client)
    await _create_value_stream(client, org["id"], name="VS-A")
    resp = await client.get(
        "/api/v1/value-streams/", params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    names = [v["name"] for v in resp.json()["items"]]
    assert "VS-A" in names
