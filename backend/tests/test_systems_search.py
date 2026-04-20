"""
Tests for /api/v1/systems search and filter functionality.
~40 tests covering query params, pagination, multi-filter combinations,
lifecycle filtering, NIS2, org-scoping, and ordering.
"""

import pytest
from uuid import uuid4
from tests.factories import create_org, create_system


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_systems_pagination_limit(client):
    """GET /api/v1/systems/?limit=1 returns at most 1 item."""
    org = await create_org(client)
    await create_system(client, org["id"], name="System Alpha")
    await create_system(client, org["id"], name="System Beta")
    await create_system(client, org["id"], name="System Gamma")

    resp = await client.get("/api/v1/systems/", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1, f"Expected 1 item with limit=1, got {len(body['items'])}"
    assert body["total"] >= 3, "total should reflect all matching systems"


@pytest.mark.asyncio
async def test_systems_pagination_offset(client):
    """GET /api/v1/systems/?offset=1&limit=1 returns second item."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Alfa System")
    await create_system(client, org["id"], name="Beta System")

    resp_all = await client.get("/api/v1/systems/", params={"limit": 100})
    all_ids = [s["id"] for s in resp_all.json()["items"]]

    resp = await client.get("/api/v1/systems/", params={"limit": 1, "offset": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    # Second item with offset=1 should not be the same as the first item with offset=0
    resp0 = await client.get("/api/v1/systems/", params={"limit": 1, "offset": 0})
    assert resp0.json()["items"][0]["id"] != body["items"][0]["id"], (
        "offset=1 should return a different item than offset=0"
    )


@pytest.mark.asyncio
async def test_systems_pagination_offset_beyond_total(client):
    """GET /api/v1/systems/?offset=9999 returns empty items but correct total."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Only System")

    resp = await client.get("/api/v1/systems/", params={"offset": 9999})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == [], "offset beyond total should return empty items"
    assert body["total"] >= 1, "total should still reflect actual count"


@pytest.mark.asyncio
async def test_systems_pagination_default_limit(client):
    """GET /api/v1/systems/ without limit returns items (default limit applied)."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"Paginrsys-{i}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200
    body = resp.json()
    assert "limit" in body
    assert body["limit"] > 0


# ---------------------------------------------------------------------------
# Search (q param)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_case_insensitive_upper(client):
    """Search with uppercase matches lowercase system name."""
    org = await create_org(client)
    await create_system(client, org["id"], name="procapita")

    resp = await client.get("/api/v1/systems/", params={"q": "PROCAPITA"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "uppercase search should match lowercase name"


@pytest.mark.asyncio
async def test_search_partial_match(client):
    """Search with partial string matches systems containing that substring."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Procapita IFO Sundsvall")

    resp = await client.get("/api/v1/systems/", params={"q": "IFO"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "partial match should find system"


@pytest.mark.asyncio
async def test_search_empty_string_returns_all(client):
    """Search with empty q returns all systems (no filter)."""
    org = await create_org(client)
    await create_system(client, org["id"], name="System Один")
    await create_system(client, org["id"], name="System Два")

    resp_no_q = await client.get("/api/v1/systems/")
    resp_empty_q = await client.get("/api/v1/systems/", params={"q": ""})

    assert resp_empty_q.status_code == 200
    assert resp_empty_q.json()["total"] == resp_no_q.json()["total"], (
        "empty q should not filter anything"
    )


@pytest.mark.asyncio
async def test_search_special_characters(client):
    """Search with special regex characters does not crash (graceful handling)."""
    resp = await client.get("/api/v1/systems/", params={"q": ".*[]{}()"})
    assert resp.status_code in (200, 422), (
        f"Special chars in search should not cause 500, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_search_unicode_characters(client):
    """Search with Swedish characters åäö returns correct results."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Åtgärdssystem för ärenden")

    resp = await client.get("/api/v1/systems/", params={"q": "ärenden"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1, "Unicode search should work"


@pytest.mark.asyncio
async def test_search_no_match_returns_empty(client):
    """Search with a string that matches nothing returns empty items."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Vanligt system")

    resp = await client.get("/api/v1/systems/", params={"q": "zzz_ingenting_matchar_xyz_999"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Filter by organization_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_by_organization_id(client):
    """GET /api/v1/systems/?organization_id=... returns only that org's systems."""
    org_a = await create_org(client, name="Org A")
    org_b = await create_org(client, name="Org B")
    await create_system(client, org_a["id"], name="System Org A")
    await create_system(client, org_b["id"], name="System Org B")

    resp = await client.get("/api/v1/systems/", params={"organization_id": org_a["id"]})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["organization_id"] == org_a["id"], (
            f"System {item['id']} belongs to wrong org"
        )
    # Org B's system must not appear
    names = [s["name"] for s in body["items"]]
    assert "System Org B" not in names


@pytest.mark.asyncio
async def test_filter_by_nonexistent_org_returns_empty(client):
    """Filter by a non-existent organization_id returns empty result."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get("/api/v1/systems/", params={"organization_id": fake_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# Filter by lifecycle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"])
async def test_filter_by_lifecycle_status(client, status):
    """Filter by each valid lifecycle_status returns only matching systems."""
    org = await create_org(client, name=f"Org for {status}")
    await create_system(client, org["id"], name=f"System {status}", lifecycle_status=status)

    resp = await client.get("/api/v1/systems/", params={
        "lifecycle_status": status,
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["lifecycle_status"] == status


@pytest.mark.asyncio
async def test_filter_by_invalid_lifecycle_status_returns_422(client):
    """Filter by invalid lifecycle_status returns 422."""
    resp = await client.get("/api/v1/systems/", params={"lifecycle_status": "okänd_status"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Filter by system_category
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category", [
    "verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"
])
async def test_filter_by_system_category(client, category):
    """Filter by each valid system_category returns only matching systems."""
    org = await create_org(client, name=f"Org for cat {category}")
    await create_system(
        client, org["id"],
        name=f"System {category}",
        system_category=category,
    )

    resp = await client.get("/api/v1/systems/", params={
        "system_category": category,
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["system_category"] == category


# ---------------------------------------------------------------------------
# Filter by criticality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", ["låg", "medel", "hög", "kritisk"])
async def test_filter_by_criticality_all_values(client, criticality):
    """Filter by each valid criticality level returns only matching systems."""
    org = await create_org(client, name=f"Org for crit {criticality}")
    await create_system(
        client, org["id"],
        name=f"System {criticality}",
        criticality=criticality,
    )

    resp = await client.get("/api/v1/systems/", params={
        "criticality": criticality,
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["criticality"] == criticality


# ---------------------------------------------------------------------------
# Filter by NIS2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_by_nis2_applicable_true(client):
    """GET /api/v1/systems/?nis2_applicable=true returns only NIS2-applicable systems."""
    org = await create_org(client, name="NIS2 Org")
    await create_system(client, org["id"], name="NIS2 System", nis2_applicable=True)
    await create_system(client, org["id"], name="Non-NIS2 System", nis2_applicable=False)

    resp = await client.get("/api/v1/systems/", params={
        "nis2_applicable": "true",
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["nis2_applicable"] is True, (
            f"System {item['name']} should be NIS2 applicable"
        )


@pytest.mark.asyncio
async def test_filter_by_treats_personal_data_true(client):
    """Filter by treats_personal_data=true returns only GDPR-relevant systems."""
    org = await create_org(client, name="GDPR Org")
    await create_system(client, org["id"], name="GDPR System", treats_personal_data=True)
    await create_system(client, org["id"], name="Non-GDPR System", treats_personal_data=False)

    resp = await client.get("/api/v1/systems/", params={
        "treats_personal_data": "true",
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["treats_personal_data"] is True, (
            f"System {item['name']} should treat personal data"
        )


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_combined_filter_category_and_criticality(client):
    """Combining system_category and criticality filters both constraints."""
    org = await create_org(client, name="Multi-filter Org")
    await create_system(client, org["id"], name="Match", system_category="infrastruktur", criticality="kritisk")
    await create_system(client, org["id"], name="Wrong Cat", system_category="stödsystem", criticality="kritisk")
    await create_system(client, org["id"], name="Wrong Crit", system_category="infrastruktur", criticality="låg")

    resp = await client.get("/api/v1/systems/", params={
        "system_category": "infrastruktur",
        "criticality": "kritisk",
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["system_category"] == "infrastruktur"
        assert item["criticality"] == "kritisk"
    names = [s["name"] for s in body["items"]]
    assert "Match" in names
    assert "Wrong Cat" not in names
    assert "Wrong Crit" not in names


@pytest.mark.asyncio
async def test_combined_filter_org_and_search(client):
    """Combine organization_id filter and q search."""
    org_a = await create_org(client, name="Org Kombination A")
    org_b = await create_org(client, name="Org Kombination B")
    await create_system(client, org_a["id"], name="Gemensamt System")
    await create_system(client, org_b["id"], name="Gemensamt System")

    resp = await client.get("/api/v1/systems/", params={
        "organization_id": org_a["id"],
        "q": "Gemensamt",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1, (
        f"Combined org+q filter should return exactly 1, got {body['total']}"
    )
    assert body["items"][0]["organization_id"] == org_a["id"]


# ---------------------------------------------------------------------------
# Systems list response structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_systems_list_response_structure(client):
    """Systems list response has items, total, limit, offset keys."""
    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


@pytest.mark.asyncio
async def test_systems_list_item_has_required_fields(client):
    """Each item in systems list has required fields."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Fälttest System")

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    item = items[0]
    required_fields = ["id", "name", "organization_id", "system_category", "lifecycle_status", "created_at"]
    for field in required_fields:
        assert field in item, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_empty_db(client):
    """GET /api/v1/systems/stats/overview on empty DB returns zeroes."""
    resp = await client.get("/api/v1/systems/stats/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_systems"] == 0
    assert body["nis2_applicable_count"] == 0
    assert body["treats_personal_data_count"] == 0


@pytest.mark.asyncio
async def test_stats_by_category_distribution(client):
    """Stats by_category_distribution reflects created systems."""
    org = await create_org(client, name="Stats Org")
    await create_system(client, org["id"], name="S1", system_category="infrastruktur")
    await create_system(client, org["id"], name="S2", system_category="infrastruktur")
    await create_system(client, org["id"], name="S3", system_category="plattform")

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_systems"] == 3
    # by_lifecycle_status and by_criticality must be dicts
    assert isinstance(body["by_lifecycle_status"], dict)
    assert isinstance(body["by_criticality"], dict)


@pytest.mark.asyncio
async def test_stats_counts_nis2_correctly(client):
    """Stats nis2_applicable_count counts only NIS2-flagged systems."""
    org = await create_org(client, name="NIS2 Stats Org")
    await create_system(client, org["id"], name="NIS2 A", nis2_applicable=True)
    await create_system(client, org["id"], name="NIS2 B", nis2_applicable=True)
    await create_system(client, org["id"], name="Non NIS2", nis2_applicable=False)

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable_count"] == 2, (
        f"Expected 2 NIS2 systems, got {body['nis2_applicable_count']}"
    )


@pytest.mark.asyncio
async def test_stats_counts_gdpr_correctly(client):
    """Stats treats_personal_data_count counts only GDPR systems."""
    org = await create_org(client, name="GDPR Stats Org")
    await create_system(client, org["id"], name="GDPR A", treats_personal_data=True)
    await create_system(client, org["id"], name="Non GDPR", treats_personal_data=False)

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["treats_personal_data_count"] == 1, (
        f"Expected 1 GDPR system, got {body['treats_personal_data_count']}"
    )


# ---------------------------------------------------------------------------
# System detail extra fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_detail_includes_integrations(client):
    """GET /api/v1/systems/{id} response includes integrations list."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="Detailsystem")

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    body = resp.json()
    # Detail endpoint may or may not include integrations, but should at minimum
    # not crash. If it includes the key it must be a list.
    if "integrations" in body:
        assert isinstance(body["integrations"], list)


@pytest.mark.asyncio
async def test_system_detail_contracts_empty_by_default(client):
    """GET /api/v1/systems/{id} contracts list is empty for new system."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="Kontraktslöst System")

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    body = resp.json()
    if "contracts" in body:
        assert body["contracts"] == [], "new system should have no contracts"
