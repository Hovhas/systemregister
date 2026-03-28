"""
Prestandatester för systemregister-API:et.

Kategori 13: Prestanda (~30 testfall)

Testar svarstider under belastning, pagination-effektivitet,
och att stora datamängder inte orsakar timeouts.
"""

import time
import pytest
from tests.factories import (
    create_org, create_system, create_classification,
    create_owner, create_contract, create_integration,
)


# ---------------------------------------------------------------------------
# Responstime - grundläggande endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_fast(client):
    """GET /health should respond within 200ms."""
    start = time.monotonic()
    resp = await client.get("/health")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.2, f"Health endpoint too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_list_systems_empty_db_fast(client):
    """GET /systems/ on empty DB should respond within 500ms."""
    start = time.monotonic()
    resp = await client.get("/api/v1/systems/")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.5, f"Empty systems list too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_list_orgs_empty_db_fast(client):
    """GET /organizations/ on empty DB should respond within 500ms."""
    start = time.monotonic()
    resp = await client.get("/api/v1/organizations/")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.5, f"Empty orgs list too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_notifications_empty_db_fast(client):
    """GET /notifications/ on empty DB should respond within 1 second."""
    start = time.monotonic()
    resp = await client.get("/api/v1/notifications/")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"Notifications on empty DB too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_stats_overview_empty_db_fast(client):
    """GET /systems/stats/overview should respond within 500ms."""
    start = time.monotonic()
    resp = await client.get("/api/v1/systems/stats/overview")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.5, f"Stats overview too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Prestanda med data - liten mängd (10 system)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_10_systems_fast(client):
    """GET /systems/ with 10 systems should respond within 1 second."""
    org = await create_org(client)
    for i in range(10):
        await create_system(client, org["id"], name=f"System {i:03d}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"limit": 50})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 1.0, f"Listing 10 systems took {elapsed:.3f}s (expected < 1s)"
    assert resp.json()["total"] == 10


@pytest.mark.asyncio
async def test_create_system_fast(client):
    """POST /systems/ should respond within 500ms."""
    org = await create_org(client)
    start = time.monotonic()
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Snabbsystem",
        "description": "Prestandatest",
        "system_category": "stödsystem",
    })
    elapsed = time.monotonic() - start
    assert resp.status_code == 201
    assert elapsed < 0.5, f"Create system took {elapsed:.3f}s (expected < 500ms)"


@pytest.mark.asyncio
async def test_get_system_detail_with_relations_fast(client):
    """GET /systems/{id} with classifications and owners should respond within 1s."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"])
    await create_owner(client, sys["id"], org["id"])
    await create_contract(client, sys["id"])

    start = time.monotonic()
    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 1.0, f"System detail took {elapsed:.3f}s (expected < 1s)"


# ---------------------------------------------------------------------------
# Prestanda med data - medium mängd (50 system)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_50_systems_under_2_seconds(client):
    """GET /systems/ with 50 systems should respond within 2 seconds."""
    org = await create_org(client)
    for i in range(50):
        await create_system(client, org["id"], name=f"PerfSystem {i:03d}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"limit": 50})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"Listing 50 systems took {elapsed:.3f}s (expected < 2s)"


@pytest.mark.asyncio
async def test_search_50_systems_under_2_seconds(client):
    """Search across 50 systems should respond within 2 seconds."""
    org = await create_org(client)
    for i in range(50):
        await create_system(client, org["id"], name=f"SearchSystem {i:03d}",
                           description=f"Beschrivning för system nummer {i}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"q": "SearchSystem"})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"Searching 50 systems took {elapsed:.3f}s"
    assert resp.json()["total"] >= 50


@pytest.mark.asyncio
async def test_stats_with_50_systems_under_2_seconds(client):
    """Stats endpoint with 50 systems should respond within 2 seconds."""
    org = await create_org(client)
    for i in range(50):
        await create_system(client, org["id"], name=f"StatsSystem {i:03d}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/stats/overview")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"Stats with 50 systems took {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_notifications_with_50_unclassified_systems(client):
    """Notifications with 50 unclassified systems should respond within 5 seconds."""
    org = await create_org(client)
    for i in range(50):
        await create_system(client, org["id"], name=f"UnclassifiedSys {i:03d}")

    start = time.monotonic()
    resp = await client.get("/api/v1/notifications/")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 5.0, f"Notifications with 50 systems took {elapsed:.3f}s"
    # Should report at least missing_classification for each
    types = [n["type"] for n in resp.json()["items"]]
    missing_count = types.count("missing_classification")
    assert missing_count >= 50


# ---------------------------------------------------------------------------
# Pagination effektivitet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pagination_page_1_vs_page_2_similar_speed(client):
    """First and second page should have similar response times."""
    org = await create_org(client)
    for i in range(30):
        await create_system(client, org["id"], name=f"PagSystem {i:03d}")

    start1 = time.monotonic()
    resp1 = await client.get("/api/v1/systems/", params={"limit": 10, "offset": 0})
    elapsed1 = time.monotonic() - start1

    start2 = time.monotonic()
    resp2 = await client.get("/api/v1/systems/", params={"limit": 10, "offset": 10})
    elapsed2 = time.monotonic() - start2

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    # Page 2 should not be more than 3x slower than page 1
    if elapsed1 > 0:
        assert elapsed2 < elapsed1 * 3 + 0.5, (
            f"Page 2 ({elapsed2:.3f}s) much slower than page 1 ({elapsed1:.3f}s)"
        )


@pytest.mark.asyncio
async def test_large_offset_not_slower_than_small_offset(client):
    """Querying at large offset should not be significantly slower."""
    org = await create_org(client)
    for i in range(30):
        await create_system(client, org["id"], name=f"OffsetSystem {i:03d}")

    start1 = time.monotonic()
    await client.get("/api/v1/systems/", params={"limit": 10, "offset": 0})
    elapsed1 = time.monotonic() - start1

    start2 = time.monotonic()
    await client.get("/api/v1/systems/", params={"limit": 10, "offset": 20})
    elapsed2 = time.monotonic() - start2

    # Should not be more than 5x slower for larger offset
    assert elapsed2 < max(elapsed1 * 5, 1.0), (
        f"Large offset ({elapsed2:.3f}s) much slower than small offset ({elapsed1:.3f}s)"
    )


# ---------------------------------------------------------------------------
# Concurrent-style tests (sequential approximation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_sequential_reads_stable_time(client):
    """Repeated reads should not degrade significantly."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    times = []
    for _ in range(5):
        start = time.monotonic()
        resp = await client.get(f"/api/v1/systems/{sys['id']}")
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        times.append(elapsed)

    # No single request should be > 5x the fastest
    fastest = min(times)
    for t in times:
        assert t < fastest * 5 + 0.5, (
            f"Response time degraded: {t:.3f}s vs fastest {fastest:.3f}s"
        )


# ---------------------------------------------------------------------------
# Prestanda - export endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_json_empty_db_fast(client):
    """GET /export/systems.json should respond within 1 second on empty DB."""
    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.json")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"JSON export too slow on empty DB: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_export_csv_empty_db_fast(client):
    """GET /export/systems.csv should respond within 1 second on empty DB."""
    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.csv")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"CSV export too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_export_json_10_systems_fast(client):
    """JSON export with 10 systems should complete within 2 seconds."""
    org = await create_org(client)
    for i in range(10):
        await create_system(client, org["id"], name=f"ExportSystem {i}")

    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.json")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"JSON export with 10 systems took {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Rapport-prestanda
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_report_fast_on_empty_db(client):
    """NIS2 report should respond within 1 second on empty DB."""
    start = time.monotonic()
    resp = await client.get("/api/v1/reports/nis2")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"NIS2 report too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_compliance_gap_report_fast_on_empty_db(client):
    """Compliance gap report should respond within 1 second on empty DB."""
    start = time.monotonic()
    resp = await client.get("/api/v1/reports/compliance-gap")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"Compliance gap report too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_audit_list_fast_on_empty_db(client):
    """GET /audit/ should respond within 500ms on empty DB."""
    start = time.monotonic()
    resp = await client.get("/api/v1/audit/")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.5, f"Audit list too slow: {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_compliance_gap_with_10_systems(client):
    """Compliance gap with 10 systems should complete within 3 seconds."""
    org = await create_org(client)
    for i in range(10):
        await create_system(client, org["id"], name=f"GapSystem {i}")

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/compliance-gap")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 3.0, f"Compliance gap with 10 systems took {elapsed:.3f}s"
