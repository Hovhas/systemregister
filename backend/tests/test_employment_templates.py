"""Tester för /api/v1/employment-templates/ (Paket C)."""
import pytest

from tests.factories import create_org, create_system


FAKE_UUID = "00000000-0000-0000-0000-000000000099"


async def _create_role(client, org_id: str, name: str = "Roll") -> dict:
    resp = await client.post(
        "/api/v1/business-roles/",
        json={"organization_id": str(org_id), "name": name},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_position(client, org_id: str, title: str = "Befattning") -> dict:
    resp = await client.post(
        "/api/v1/positions/",
        json={"organization_id": str(org_id), "title": title},
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_template(client, org_id: str, role_ids: list[str], **overrides) -> dict:
    payload = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Standardmall"),
        "role_ids": role_ids,
    }
    payload.update({k: v for k, v in overrides.items() if v is not None})
    resp = await client.post("/api/v1/employment-templates/", json=payload)
    assert resp.status_code == 201, f"create_template failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    template = await _create_template(client, org["id"], [role["id"]])
    assert role["id"] in template["role_ids"]

    patch_resp = await client.patch(
        f"/api/v1/employment-templates/{template['id']}",
        json={"is_active": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False

    del_resp = await client.delete(f"/api/v1/employment-templates/{template['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_link_to_position(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    pos = await _create_position(client, org["id"], title="Bygglovshandläggare")
    template = await _create_template(
        client, org["id"], [role["id"]], position_id=pos["id"],
    )
    assert template["position_id"] == pos["id"]


@pytest.mark.asyncio
async def test_resolved_access_basic(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"], name="Lärare")
    system = await create_system(client, org["id"], name="IST")
    await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "skriv",
            "access_type": "grundbehörighet",
        },
    )
    template = await _create_template(client, org["id"], [role["id"]])

    resp = await client.get(
        f"/api/v1/employment-templates/{template['id']}/resolved-access"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is True
    assert len(body["entries"]) == 1
    assert body["entries"][0]["system_name"] == "IST"
    assert body["entries"][0]["access_level"] == "skriv"


@pytest.mark.asyncio
async def test_resolved_access_inactive_returns_empty(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    system = await create_system(client, org["id"])
    await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "läs",
        },
    )
    template = await _create_template(client, org["id"], [role["id"]], is_active=False)
    resp = await client.get(
        f"/api/v1/employment-templates/{template['id']}/resolved-access"
    )
    assert resp.status_code == 200
    assert resp.json()["entries"] == []
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_resolved_access_csv(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    system = await create_system(client, org["id"], name="ByggR")
    await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "skriv",
        },
    )
    template = await _create_template(client, org["id"], [role["id"]])
    resp = await client.get(
        f"/api/v1/employment-templates/{template['id']}/resolved-access.csv"
    )
    assert resp.status_code == 200
    body = resp.text
    assert "system_namn" in body
    assert "ByggR" in body


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    role = await _create_role(client, org_a["id"])
    template = await _create_template(client, org_a["id"], [role["id"]])
    resp = await client.get(
        f"/api/v1/employment-templates/{template['id']}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_remove_role(client):
    org = await create_org(client)
    role_a = await _create_role(client, org["id"], name="A")
    role_b = await _create_role(client, org["id"], name="B")
    template = await _create_template(client, org["id"], [role_a["id"]])

    add_resp = await client.post(
        f"/api/v1/employment-templates/{template['id']}/roles",
        json={"role_id": role_b["id"]},
    )
    assert add_resp.status_code == 201

    rem_resp = await client.delete(
        f"/api/v1/employment-templates/{template['id']}/roles/{role_a['id']}"
    )
    assert rem_resp.status_code == 204
