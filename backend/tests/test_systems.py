"""
Tests for /api/v1/systems endpoints.
"""

import pytest

from tests.factories import create_org, create_system


# ---------------------------------------------------------------------------
# Constants used in direct POST calls within tests
# ---------------------------------------------------------------------------

SYSTEM_BASE = {
    "name": "Procapita",
    "description": "Verksamhetssystem för individ- och familjeomsorg",
    "system_category": "verksamhetssystem",
    "criticality": "hög",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system(client):
    """POST /api/v1/systems/ returns 201 with correct fields."""
    org = await create_org(client)

    payload = {**SYSTEM_BASE, "organization_id": org["id"]}
    resp = await client.post("/api/v1/systems/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["name"] == SYSTEM_BASE["name"], "name mismatch"
    assert body["description"] == SYSTEM_BASE["description"], "description mismatch"
    assert body["system_category"] == SYSTEM_BASE["system_category"], "category mismatch"
    assert body["criticality"] == SYSTEM_BASE["criticality"], "criticality mismatch"
    assert body["organization_id"] == org["id"], "organization_id mismatch"
    assert "id" in body, "response must include id"
    assert "created_at" in body
    assert "updated_at" in body
    # Verify defaults
    assert body["lifecycle_status"] == "i_drift", "default lifecycle_status should be i_drift"
    assert body["treats_personal_data"] is False, "default treats_personal_data should be False"
    assert body["dr_plan_exists"] is False, "default dr_plan_exists should be False"


@pytest.mark.asyncio
async def test_create_system_invalid_category(client):
    """POST with unknown system_category returns 422."""
    org = await create_org(client)
    payload = {**SYSTEM_BASE, "organization_id": org["id"], "system_category": "invalid"}

    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_system_invalid_org(client):
    """POST with non-existent organization_id should return 422.

    FK-violation fångas av systems.py (IntegrityError → 422) med
    ett beskrivande felmeddelande.
    """
    fake_org_id = "00000000-0000-0000-0000-000000000000"
    payload = {**SYSTEM_BASE, "organization_id": fake_org_id}

    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 422, (
        f"FK-violation borde ge 422, fick {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "detail" in body, "Svaret borde innehålla 'detail' med felmeddelande"


@pytest.mark.asyncio
async def test_list_systems(client):
    """GET /api/v1/systems/ returns paginated response with items."""
    org = await create_org(client)
    await create_system(client, org["id"])
    await create_system(client, org["id"], name="Pulsen Combine")

    resp = await client.get("/api/v1/systems/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body, "response should have items key"
    assert "total" in body, "response should have total key"
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2, f"expected at least 2 systems, got {body['total']}"
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_list_systems_empty(client):
    """GET /api/v1/systems/ on empty DB returns empty paginated response."""
    resp = await client.get("/api/v1/systems/")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_filter_systems_by_category(client):
    """GET /api/v1/systems/?system_category=... filters correctly."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Verksamhetssystem A", system_category="verksamhetssystem")
    await create_system(client, org["id"], name="Infrastruktur B", system_category="infrastruktur")

    resp = await client.get("/api/v1/systems/", params={"system_category": "infrastruktur"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["system_category"] == "infrastruktur", (
            f"Expected infrastruktur, got {item['system_category']}"
        )


@pytest.mark.asyncio
async def test_filter_systems_by_criticality(client):
    """GET /api/v1/systems/?criticality=... filters correctly."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Kritiskt system", criticality="kritisk")
    await create_system(client, org["id"], name="Låg prio", criticality="låg")

    resp = await client.get("/api/v1/systems/", params={"criticality": "kritisk"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["criticality"] == "kritisk", (
            f"Expected kritisk, got {item['criticality']}"
        )


@pytest.mark.asyncio
async def test_search_systems_by_name(client):
    """GET /api/v1/systems/?q=... filters by name (case-insensitive)."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Procapita IFO", description="IFO-system")
    await create_system(client, org["id"], name="Visma Lön", description="Lönesystem")

    resp = await client.get("/api/v1/systems/", params={"q": "procapita"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    names = [item["name"] for item in body["items"]]
    assert any("Procapita" in n for n in names), f"Expected Procapita in results, got {names}"


@pytest.mark.asyncio
async def test_search_systems_by_description(client):
    """GET /api/v1/systems/?q=... also matches description text."""
    org = await create_org(client)
    await create_system(client, org["id"],
        name="Obskyr produkt",
        description="Hanterar patientjournaler i vården",
    )

    resp = await client.get("/api/v1/systems/", params={"q": "patientjournaler"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "search in description should return results"


@pytest.mark.asyncio
async def test_search_no_results(client):
    """GET /api/v1/systems/?q=<nonsense> returns empty list."""
    resp = await client.get("/api/v1/systems/", params={"q": "xyzzy_no_match_12345"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_get_system_detail(client):
    """GET /api/v1/systems/{id} returns system with classifications and owners lists."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    resp = await client.get(f"/api/v1/systems/{system_id}")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["id"] == system_id
    assert body["name"] == system["name"]
    # Detail response includes relationship lists
    assert "classifications" in body, "detail response should include classifications"
    assert "owners" in body, "detail response should include owners"
    assert isinstance(body["classifications"], list)
    assert isinstance(body["owners"], list)


@pytest.mark.asyncio
async def test_get_system_not_found(client):
    """GET /api/v1/systems/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/systems/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_system(client):
    """PATCH /api/v1/systems/{id} updates fields without touching others."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    patch = {
        "name": "Procapita v2",
        "lifecycle_status": "under_avveckling",
        "criticality": "medel",
    }
    resp = await client.patch(f"/api/v1/systems/{system_id}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["name"] == "Procapita v2"
    assert body["lifecycle_status"] == "under_avveckling"
    assert body["criticality"] == "medel"
    # Unchanged field
    assert body["organization_id"] == org["id"]
    assert body["description"] == system["description"]


@pytest.mark.asyncio
async def test_update_system_not_found(client):
    """PATCH on non-existent system returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/systems/{fake_id}", json={"name": "X"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_system(client):
    """DELETE /api/v1/systems/{id} removes the system and returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    delete_resp = await client.delete(f"/api/v1/systems/{system_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    get_resp = await client.get(f"/api/v1/systems/{system_id}")
    assert get_resp.status_code == 404, "system should be gone after delete"


@pytest.mark.asyncio
async def test_delete_system_not_found(client):
    """DELETE on non-existent system returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/systems/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_system_stats_overview(client):
    """GET /api/v1/systems/stats/overview returns correct structure."""
    org = await create_org(client)
    await create_system(client, org["id"],
        name="System A",
        criticality="kritisk",
        lifecycle_status="i_drift",
        nis2_applicable=True,
        treats_personal_data=True,
    )
    await create_system(client, org["id"],
        name="System B",
        criticality="låg",
        lifecycle_status="planerad",
    )

    resp = await client.get("/api/v1/systems/stats/overview")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()

    assert "total_systems" in body, "stats must include total_systems"
    assert "by_lifecycle_status" in body, "stats must include by_lifecycle_status"
    assert "by_criticality" in body, "stats must include by_criticality"
    assert "nis2_applicable_count" in body, "stats must include nis2_applicable_count"
    assert "treats_personal_data_count" in body, "stats must include treats_personal_data_count"

    assert body["total_systems"] >= 2
    assert body["nis2_applicable_count"] >= 1, "should count NIS2-flagged systems"
    assert body["treats_personal_data_count"] >= 1, "should count GDPR systems"

    assert isinstance(body["by_lifecycle_status"], dict)
    assert isinstance(body["by_criticality"], dict)


@pytest.mark.asyncio
async def test_system_stats_filtered_by_org(client):
    """GET /api/v1/systems/stats/overview?organization_id=... scopes to that org."""
    org1 = await create_org(client)
    org2_resp = await client.post("/api/v1/organizations/", json={
        "name": "Annan organisation",
        "org_type": "bolag",
    })
    assert org2_resp.status_code == 201
    org2 = org2_resp.json()

    await create_system(client, org1["id"], name="Org1 System")
    await create_system(client, org2["id"], name="Org2 System")

    resp = await client.get("/api/v1/systems/stats/overview", params={"organization_id": org1["id"]})

    assert resp.status_code == 200
    body = resp.json()
    # Stats should only count org1's system
    assert body["total_systems"] == 1, (
        f"Stats should only include org1's systems, got total={body['total_systems']}"
    )


# ---------------------------------------------------------------------------
# Extended tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category,criticality,lifecycle", [
    ("verksamhetssystem", "kritisk", "i_drift"),
    ("stödsystem", "medel", "under_avveckling"),
    ("infrastruktur", "hög", "planerad"),
    ("plattform", "låg", "avvecklad"),
    ("iot", "kritisk", "under_inforande"),
])
async def test_create_system_enum_combinations(client, category, criticality, lifecycle):
    """POST system accepts all valid enum combinations."""
    org = await create_org(client)
    payload = {
        **SYSTEM_BASE,
        "organization_id": org["id"],
        "name": f"System {category} {criticality}",
        "system_category": category,
        "criticality": criticality,
        "lifecycle_status": lifecycle,
    }
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 201, f"Expected 201 for {category}/{criticality}/{lifecycle}: {resp.text}"
    body = resp.json()
    assert body["system_category"] == category
    assert body["criticality"] == criticality
    assert body["lifecycle_status"] == lifecycle


@pytest.mark.asyncio
async def test_system_extended_attributes_jsonb_persisted(client):
    """POST system with extended_attributes stores and retrieves JSONB correctly."""
    org = await create_org(client)
    ext_attrs = {"leverantör": "CGI", "version": "21.3", "kunder": 500}
    resp = await client.post("/api/v1/systems/", json={
        **SYSTEM_BASE,
        "organization_id": org["id"],
        "name": "JSONB System",
        "extended_attributes": ext_attrs,
    })
    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    system_id = resp.json()["id"]

    # Fetch and verify
    get_resp = await client.get(f"/api/v1/systems/{system_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["extended_attributes"]["leverantör"] == "CGI"
    assert body["extended_attributes"]["kunder"] == 500


@pytest.mark.asyncio
async def test_system_extended_attributes_null_by_default(client):
    """POST system without extended_attributes has null/empty extended_attributes."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        **SYSTEM_BASE,
        "organization_id": org["id"],
        "name": "System utan ext attrs",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body.get("extended_attributes") in (None, {})


@pytest.mark.asyncio
async def test_system_stats_empty_db_returns_zeros(client):
    """GET /api/v1/systems/stats/overview on empty DB returns all zeros."""
    resp = await client.get("/api/v1/systems/stats/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_systems"] == 0
    assert body["nis2_applicable_count"] == 0
    assert body["treats_personal_data_count"] == 0


@pytest.mark.asyncio
async def test_system_stats_by_lifecycle_status_distribution(client):
    """Stats by_lifecycle_status accurately reflects created systems per status."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Plan 1", lifecycle_status="planerad")
    await create_system(client, org["id"], name="Plan 2", lifecycle_status="planerad")
    await create_system(client, org["id"], name="Drift 1", lifecycle_status="i_drift")

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    lifecycle = body["by_lifecycle_status"]
    assert lifecycle.get("planerad", 0) >= 2, (
        f"Expected at least 2 planerad systems, got {lifecycle.get('planerad', 0)}"
    )
    assert lifecycle.get("i_drift", 0) >= 1


@pytest.mark.asyncio
async def test_system_stats_by_criticality_distribution(client):
    """Stats by_criticality accurately reflects created systems per criticality."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Krit A", criticality="kritisk")
    await create_system(client, org["id"], name="Krit B", criticality="kritisk")
    await create_system(client, org["id"], name="Låg A", criticality="låg")

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    criticality = body["by_criticality"]
    assert criticality.get("kritisk", 0) >= 2
    assert criticality.get("låg", 0) >= 1


@pytest.mark.asyncio
async def test_update_system_nis2_fields(client):
    """PATCH system can update nis2_applicable and nis2_classification."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    resp = await client.patch(f"/api/v1/systems/{system_id}", json={
        "nis2_applicable": True,
        "nis2_classification": "väsentlig",
    })
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "väsentlig"


@pytest.mark.asyncio
async def test_create_system_preserves_all_optional_fields(client):
    """POST system with all optional fields preserves them correctly."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        **SYSTEM_BASE,
        "organization_id": org["id"],
        "name": "Komplett System",
        "lifecycle_status": "planerad",
        "criticality": "hög",
        "nis2_applicable": True,
        "nis2_classification": "viktig",
        "treats_personal_data": True,
        "treats_sensitive_data": True,
        "hosting_model": "on_premise",
        "business_area": "socialtjänst",
    })
    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["lifecycle_status"] == "planerad"
    assert body["criticality"] == "hög"
    assert body["nis2_applicable"] is True
    assert body["treats_personal_data"] is True
    assert body["business_area"] == "socialtjänst"


@pytest.mark.asyncio
async def test_delete_system_removes_from_list(client):
    """After DELETE, system no longer appears in GET /systems/ list."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="Ska Tas Bort")
    system_id = system["id"]

    await client.delete(f"/api/v1/systems/{system_id}")

    resp = await client.get("/api/v1/systems/")
    ids = [s["id"] for s in resp.json()["items"]]
    assert system_id not in ids, "Deleted system should not appear in list"


@pytest.mark.asyncio
async def test_filter_systems_by_organization_returns_correct_count(client):
    """Filter by organization_id returns exactly that org's systems."""
    org_a = await create_org(client)
    org_b_resp = await client.post("/api/v1/organizations/", json={"name": "Org B Filter", "org_type": "bolag"})
    assert org_b_resp.status_code == 201
    org_b = org_b_resp.json()

    await create_system(client, org_a["id"], name="A-system 1")
    await create_system(client, org_a["id"], name="A-system 2")
    await create_system(client, org_b["id"], name="B-system 1")

    resp = await client.get("/api/v1/systems/", params={"organization_id": org_a["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2, f"Expected 2 systems for org_a, got {body['total']}"
    for item in body["items"]:
        assert item["organization_id"] == org_a["id"]
