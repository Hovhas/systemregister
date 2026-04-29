"""Tester för /api/v1/role-access/ (Paket C)."""
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


@pytest.mark.asyncio
async def test_happy_path_crud(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    system = await create_system(client, org["id"])

    create_resp = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "skriv",
            "access_type": "grundbehörighet",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    access = create_resp.json()
    assert access["access_level"] == "skriv"

    patch_resp = await client.patch(
        f"/api/v1/role-access/{access['id']}",
        json={"access_level": "administratör", "justification": "Förvaltningsansvar"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["access_level"] == "administratör"

    del_resp = await client.delete(f"/api/v1/role-access/{access['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_unique_constraint_role_system(client):
    """Samma (roll, system) får bara finnas en gång."""
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    system = await create_system(client, org["id"])

    first = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "läs",
        },
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "skriv",
        },
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_multi_org_isolation(client):
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    role = await _create_role(client, org_a["id"])
    system = await create_system(client, org_a["id"])
    create_resp = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role["id"],
            "system_id": system["id"],
            "access_level": "läs",
        },
    )
    assert create_resp.status_code == 201
    access_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/role-access/{access_id}",
        headers={"X-Organization-Id": org_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_role_rejected(client):
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": FAKE_UUID,
            "system_id": system["id"],
            "access_level": "läs",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_filter_by_role(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"])
    sys_a = await create_system(client, org["id"], name="A")
    sys_b = await create_system(client, org["id"], name="B")
    for sid in [sys_a["id"], sys_b["id"]]:
        await client.post(
            "/api/v1/role-access/",
            json={
                "business_role_id": role["id"],
                "system_id": sid,
                "access_level": "läs",
            },
        )

    resp = await client.get(
        "/api/v1/role-access/",
        params={"business_role_id": role["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get(f"/api/v1/role-access/{FAKE_UUID}")
    assert resp.status_code == 404
