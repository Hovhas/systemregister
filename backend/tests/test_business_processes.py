"""Tester för /api/v1/processes/ — verksamhetsprocesser (Paket A)."""
from sqlalchemy import select, text

import pytest

from app.models import AuditLog
from tests.factories import create_org, create_system, create_information_asset


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_process(client, org_id: str, **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testprocess"),
        "description": overrides.pop("description", None),
        "parent_process_id": overrides.pop("parent_process_id", None),
        "process_owner": overrides.pop("process_owner", None),
        "criticality": overrides.pop("criticality", None),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    resp = await client.post("/api/v1/processes/", json=payload)
    assert resp.status_code == 201, f"create_process failed: {resp.status_code} {resp.text}"
    return resp.json()


async def _create_capability(client, org_id: str, name: str = "Förmåga") -> dict:
    resp = await client.post(
        "/api/v1/capabilities/",
        json={"organization_id": str(org_id), "name": name},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"], name="Bygglovshantering")
    assert proc["name"] == "Bygglovshantering"

    get_resp = await client.get(f"/api/v1/processes/{proc['id']}")
    assert get_resp.status_code == 200

    patch_resp = await client.patch(
        f"/api/v1/processes/{proc['id']}",
        json={"criticality": "hög"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["criticality"] == "hög"

    del_resp = await client.delete(f"/api/v1/processes/{proc['id']}")
    assert del_resp.status_code == 204
    assert (await client.get(f"/api/v1/processes/{proc['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    proc_a = await _create_process(client, org_a["id"], name="HemligProc")

    resp = await client.get(
        f"/api/v1/processes/{proc_a['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_row_created_on_create(client, db_session):
    org = await create_org(client)
    proc = await _create_process(client, org["id"], name="Audited")

    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.table_name == "business_processes",
            text("record_id = :rid"),
        ).params(rid=proc["id"])
    )).scalars().all()
    assert any(r.action.value == "create" for r in rows)


@pytest.mark.asyncio
async def test_hierarchy_parent_child(client):
    org = await create_org(client)
    parent = await _create_process(client, org["id"], name="Huvudprocess")
    child = await _create_process(
        client, org["id"], name="Delprocess",
        parent_process_id=parent["id"],
    )
    assert child["parent_process_id"] == parent["id"]


@pytest.mark.asyncio
async def test_link_process_to_system(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"], name="Process A")
    system = await create_system(client, org["id"])

    link = await client.post(
        f"/api/v1/processes/{proc['id']}/systems",
        json={"system_id": system["id"]},
    )
    assert link.status_code == 201

    listed = await client.get(f"/api/v1/processes/{proc['id']}/systems")
    assert listed.status_code == 200
    assert system["id"] in [s["id"] for s in listed.json()]


@pytest.mark.asyncio
async def test_link_process_to_capability(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"])
    cap = await _create_capability(client, org["id"])

    link = await client.post(
        f"/api/v1/processes/{proc['id']}/capabilities",
        json={"capability_id": cap["id"]},
    )
    assert link.status_code == 201

    listed = await client.get(f"/api/v1/processes/{proc['id']}/capabilities")
    assert listed.status_code == 200
    assert cap["id"] in [c["id"] for c in listed.json()]


@pytest.mark.asyncio
async def test_link_process_to_information_asset(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"])
    asset = await create_information_asset(client, org["id"])

    link = await client.post(
        f"/api/v1/processes/{proc['id']}/information-assets",
        json={"information_asset_id": asset["id"]},
    )
    assert link.status_code == 201

    listed = await client.get(f"/api/v1/processes/{proc['id']}/information-assets")
    assert listed.status_code == 200
    assert asset["id"] in [a["id"] for a in listed.json()]


@pytest.mark.asyncio
async def test_safe_string_rejects_null_byte(client):
    org = await create_org(client)
    resp = await client.post(
        "/api/v1/processes/",
        json={"organization_id": org["id"], "name": "Process\x00"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unlink(client):
    org = await create_org(client)
    proc = await _create_process(client, org["id"])
    system = await create_system(client, org["id"])
    await client.post(
        f"/api/v1/processes/{proc['id']}/systems",
        json={"system_id": system["id"]},
    )
    resp = await client.delete(
        f"/api/v1/processes/{proc['id']}/systems/{system['id']}"
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/processes/{FAKE_UUID}")
    assert resp.status_code == 404
