"""Tester för template_service.resolve_template_access (Paket C.2)."""
import pytest

from tests.factories import create_org, create_system


async def _create_role(client, org_id: str, name: str) -> dict:
    resp = await client.post(
        "/api/v1/business-roles/",
        json={"organization_id": str(org_id), "name": name},
    )
    assert resp.status_code == 201
    return resp.json()


async def _grant(client, role_id: str, system_id: str, level: str, access_type: str = "grundbehörighet"):
    resp = await client.post(
        "/api/v1/role-access/",
        json={
            "business_role_id": role_id,
            "system_id": system_id,
            "access_level": level,
            "access_type": access_type,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_template(client, org_id: str, role_ids: list[str], is_active: bool = True) -> dict:
    resp = await client.post(
        "/api/v1/employment-templates/",
        json={
            "organization_id": str(org_id),
            "name": "T",
            "role_ids": role_ids,
            "is_active": is_active,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _resolve(client, template_id: str) -> dict:
    resp = await client.get(
        f"/api/v1/employment-templates/{template_id}/resolved-access"
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_one_role_one_system(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"], "Roll1")
    system = await create_system(client, org["id"], name="Sys1")
    await _grant(client, role["id"], system["id"], "läs")
    template = await _create_template(client, org["id"], [role["id"]])

    resolved = await _resolve(client, template["id"])
    assert len(resolved["entries"]) == 1
    assert resolved["entries"][0]["access_level"] == "läs"


@pytest.mark.asyncio
async def test_two_roles_overlapping_levels_highest_wins(client):
    org = await create_org(client)
    role_a = await _create_role(client, org["id"], "RollA")
    role_b = await _create_role(client, org["id"], "RollB")
    system = await create_system(client, org["id"], name="DelatSys")

    await _grant(client, role_a["id"], system["id"], "läs")
    await _grant(client, role_b["id"], system["id"], "administratör")

    template = await _create_template(client, org["id"], [role_a["id"], role_b["id"]])
    resolved = await _resolve(client, template["id"])
    assert len(resolved["entries"]) == 1
    entry = resolved["entries"][0]
    assert entry["access_level"] == "administratör"
    assert set(entry["contributing_role_names"]) == {"RollA", "RollB"}


@pytest.mark.asyncio
async def test_birthright_beats_conditional(client):
    org = await create_org(client)
    role_a = await _create_role(client, org["id"], "RollA")
    role_b = await _create_role(client, org["id"], "RollB")
    system = await create_system(client, org["id"], name="DelatSys")

    await _grant(client, role_a["id"], system["id"], "läs", access_type="grundbehörighet")
    await _grant(client, role_b["id"], system["id"], "läs", access_type="villkorad")

    template = await _create_template(client, org["id"], [role_a["id"], role_b["id"]])
    resolved = await _resolve(client, template["id"])
    assert len(resolved["entries"]) == 1
    assert resolved["entries"][0]["access_type"] == "grundbehörighet"


@pytest.mark.asyncio
async def test_inactive_template_returns_empty(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"], "R")
    system = await create_system(client, org["id"])
    await _grant(client, role["id"], system["id"], "läs")
    template = await _create_template(client, org["id"], [role["id"]], is_active=False)

    resolved = await _resolve(client, template["id"])
    assert resolved["entries"] == []
    assert resolved["is_active"] is False


@pytest.mark.asyncio
async def test_no_roles_returns_empty(client):
    org = await create_org(client)
    template = await _create_template(client, org["id"], [])
    resolved = await _resolve(client, template["id"])
    assert resolved["entries"] == []


@pytest.mark.asyncio
async def test_multiple_systems_aggregated(client):
    org = await create_org(client)
    role = await _create_role(client, org["id"], "Bred-roll")
    sys_a = await create_system(client, org["id"], name="Alpha")
    sys_b = await create_system(client, org["id"], name="Beta")
    await _grant(client, role["id"], sys_a["id"], "skriv")
    await _grant(client, role["id"], sys_b["id"], "läs")

    template = await _create_template(client, org["id"], [role["id"]])
    resolved = await _resolve(client, template["id"])
    assert len(resolved["entries"]) == 2
    names = {e["system_name"] for e in resolved["entries"]}
    assert names == {"Alpha", "Beta"}
