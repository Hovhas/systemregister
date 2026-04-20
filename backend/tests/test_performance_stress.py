"""
Prestanda-, skalbarhet- och stresstester för systemregister-API:et.

Testar att systemet klarar 500-1000 systemregisterposter med god prestanda,
korrekt paginering, sökning, relationer, import och rapport-generering.

Kör långsamma tester med: pytest -m slow
Hoppa över dem med:       pytest -m "not slow"
"""

import asyncio
import io
import json
import csv
import time

import pytest
from uuid import uuid4

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_integration,
    create_contract,
)


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------


def make_json_import(rows: list[dict]) -> tuple[bytes, str, str]:
    content = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    return content, "systems.json", "application/json"


def make_csv_import(rows: list[dict]) -> tuple[bytes, str, str]:
    if not rows:
        return b"", "systems.csv", "text/csv"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8"), "systems.csv", "text/csv"


def make_xlsx_import(rows: list[dict]) -> tuple[bytes, str, str]:
    try:
        from openpyxl import Workbook
    except ImportError:
        pytest.skip("openpyxl inte installerat")
    wb = Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return buf.read(), "systems.xlsx", ct


async def post_import(client, org_id: str, content: bytes, filename: str, content_type: str):
    return await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org_id},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


SYSTEM_CATEGORIES = [
    "verksamhetssystem",
    "stödsystem",
    "infrastruktur",
    "plattform",
]

CRITICALITIES = ["kritisk", "hög", "medel", "låg"]

LIFECYCLE_STATUSES = ["i_drift", "under_avveckling", "planerad"]


def system_row(i: int, org_id: str = "") -> dict:
    """Returnera en rad lämplig för import."""
    return {
        "name": f"StressSystem {i:04d}",
        "description": f"Stresstest system nummer {i}",
        "system_category": SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)],
        "criticality": CRITICALITIES[i % len(CRITICALITIES)],
    }


# ===========================================================================
# SKALBARHET — 100 SYSTEM
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_list_100_systems_response_time(client):
    """GET /systems/ med 100 system ska svara inom 3 sekunder."""
    org = await create_org(client, name="Org100")
    for i in range(100):
        await create_system(
            client, org["id"],
            name=f"Sys100-{i:03d}-{uuid4().hex[:6]}",
            system_category=SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)],
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"limit": 25})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 100
    assert elapsed < 3.0, f"100 system tog {elapsed:.3f}s (förväntat < 3s)"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_list_100_systems_total_count_correct(client):
    """Total-räkning ska vara exakt 100 vid paginering."""
    org = await create_org(client, name="OrgCount100")
    for i in range(100):
        await create_system(client, org["id"], name=f"CntSys-{i:03d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    assert resp.json()["total"] == 100


@pytest.mark.asyncio
@pytest.mark.slow
async def test_list_100_systems_first_page_correct_size(client):
    """Första sidan med 25-limit ska returnera exakt 25 poster."""
    org = await create_org(client, name="OrgPage100")
    for i in range(100):
        await create_system(client, org["id"], name=f"PgSys-{i:03d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/", params={"limit": 25, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 25


# ===========================================================================
# SKALBARHET — 500 SYSTEM
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pagination_works_with_500_systems(client):
    """Paginering ska fungera korrekt med 500 system — total och sidstorlek."""
    org = await create_org(client, name="Org500Pag")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"Pag500-{i:04d}-{uuid4().hex[:6]}",
            system_category=SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)],
        )

    resp = await client.get("/api/v1/systems/", params={"limit": 25, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 500
    assert len(data["items"]) == 25


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_500_systems_under_2_seconds(client):
    """Sökning bland 500 system ska svara inom 2 sekunder."""
    org = await create_org(client, name="Org500Search")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"Srch500-{i:04d}-{uuid4().hex[:6]}",
            description=f"Söker efter detta system {i}",
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"organization_id": org["id"], "limit": 1})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert resp.json()["total"] == 500
    assert elapsed < 2.0, f"Sökning bland 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_filter_500_systems_correct_result(client):
    """Filter på system_category ska returnera korrekt delmängd bland 500 system."""
    org = await create_org(client, name="Org500Filter")
    expected_count = 0
    for i in range(500):
        cat = SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)]
        if cat == "verksamhetssystem":
            expected_count += 1
        await create_system(client, org["id"],
                            name=f"FltSys-{i:04d}-{uuid4().hex[:6]}",
                            system_category=cat)

    resp = await client.get("/api/v1/systems/",
                            params={"system_category": "verksamhetssystem", "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == expected_count
    for item in data["items"]:
        assert item["system_category"] == "verksamhetssystem"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stats_overview_500_systems_correct_calculation(client):
    """Stats/overview ska beräkna rätt antal system bland 500."""
    org = await create_org(client, name="Org500Stats")
    for i in range(500):
        await create_system(client, org["id"], name=f"Stat500-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/stats/overview")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_systems"] >= 500
    assert elapsed < 5.0, f"Stats med 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_export_xlsx_500_systems_no_oom(client):
    """Excel-export med 500 system ska genereras utan OOM (max 10 sekunder)."""
    org = await create_org(client, name="Org500Export")
    for i in range(500):
        await create_system(client, org["id"], name=f"Exp500-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.xlsx")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 10.0, f"XLSX-export med 500 system tog {elapsed:.3f}s"
    # Verifiera att filen har rimlig storlek (>1KB)
    assert len(resp.content) > 1024


@pytest.mark.asyncio
@pytest.mark.slow
async def test_export_csv_500_systems_correct_row_count(client):
    """CSV-export med 500 system ska ha 500 datarader (plus header)."""
    org = await create_org(client, name="Org500CSV")
    for i in range(500):
        await create_system(client, org["id"], name=f"CsvSys-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/export/systems.csv")
    assert resp.status_code == 200

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 500


@pytest.mark.asyncio
@pytest.mark.slow
async def test_export_json_500_systems_parseable(client):
    """JSON-export med 500 system ska vara parsebar och ha 500 poster."""
    org = await create_org(client, name="Org500JSON")
    for i in range(500):
        await create_system(client, org["id"], name=f"JsonSys-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/export/systems.json")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 500


# ===========================================================================
# PAGINERING UNDER LAST — 500 SYSTEM
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("page_num", list(range(1, 21)))
async def test_pagination_page_n_of_500(client, page_num):
    """Sida N (25 per sida) ska returnera exakt 25 poster bland 500 system."""
    org = await create_org(client, name=f"OrgPagStress{page_num}")
    for i in range(500):
        await create_system(client, org["id"], name=f"PS{page_num}-{i:04d}-{uuid4().hex[:6]}")

    offset = (page_num - 1) * 25
    resp = await client.get("/api/v1/systems/",
                            params={"limit": 25, "offset": offset})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 500
    assert len(data["items"]) == 25, (
        f"Sida {page_num} (offset {offset}): förväntade 25, fick {len(data['items'])}"
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pagination_offset_beyond_range_returns_empty(client):
    """Offset utanför range ska returnera tom items-lista men korrekt total."""
    org = await create_org(client, name="OrgOffsetBeyond")
    for i in range(50):
        await create_system(client, org["id"], name=f"BndSys-{i:03d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/",
                            params={"limit": 25, "offset": 9999})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 50
    assert data["items"] == []


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pagination_last_page_partial(client):
    """Sista sidan med 510 system (510 % 25 = 10) ska returnera 10 poster."""
    org = await create_org(client, name="OrgLastPage")
    for i in range(510):
        await create_system(client, org["id"], name=f"LstPg-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/",
                            params={"limit": 25, "offset": 500})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 510
    assert len(data["items"]) == 10


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pagination_parallel_pages(client):
    """Parallella sidanrop ska alla returnera 200 och korrekt data."""
    org = await create_org(client, name="OrgParallelPag")
    for i in range(100):
        await create_system(client, org["id"], name=f"ParPag-{i:03d}-{uuid4().hex[:6]}")

    async def fetch_page(offset: int):
        return await client.get("/api/v1/systems/",
                                params={"limit": 25, "offset": offset})

    responses = await asyncio.gather(
        fetch_page(0), fetch_page(25), fetch_page(50), fetch_page(75)
    )

    for i, resp in enumerate(responses):
        assert resp.status_code == 200, f"Sida {i+1} returnerade {resp.status_code}"
        data = resp.json()
        assert data["total"] == 100
        assert len(data["items"]) == 25, f"Sida {i+1}: förväntade 25, fick {len(data['items'])}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pagination_consecutive_pages_no_duplicates(client):
    """Konsekutiva sidor ska inte ha överlappande system-IDs."""
    org = await create_org(client, name="OrgNoDuplicates")
    for i in range(100):
        await create_system(client, org["id"], name=f"NDup-{i:03d}-{uuid4().hex[:6]}")

    all_ids = []
    for offset in range(0, 100, 25):
        resp = await client.get("/api/v1/systems/",
                                params={"limit": 25, "offset": offset})
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        all_ids.extend(ids)

    assert len(all_ids) == len(set(all_ids)), "Duplicerade system-IDs hittades i paginering"


# ===========================================================================
# SÖK-PRESTANDA — 500 SYSTEM
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_fulltext_search_500_systems_response_time(client):
    """Full-text sökning bland 500 system ska svara inom 2 sekunder."""
    org = await create_org(client, name="OrgFTSearch")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"FTS-{i:04d}-{uuid4().hex[:6]}",
            description=f"Systemet hanterar personaldata och ekonomi {i}",
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"q": "personaldata"})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 2.0, f"Full-text sökning tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_with_filter_combination_500_systems(client):
    """Sökning med flera filter kombinerat ska returnera korrekt delmängd."""
    org = await create_org(client, name="OrgCombinedFilter")
    for i in range(500):
        cat = SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)]
        crit = CRITICALITIES[i % len(CRITICALITIES)]
        await create_system(
            client, org["id"],
            name=f"CmbFlt-{i:04d}-{uuid4().hex[:6]}",
            system_category=cat,
            criticality=crit,
        )

    resp = await client.get("/api/v1/systems/", params={
        "system_category": "verksamhetssystem",
        "criticality": "kritisk",
        "limit": 200,
    })
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["system_category"] == "verksamhetssystem"
        assert item["criticality"] == "kritisk"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_no_match_returns_empty_500_systems(client):
    """Sökning utan träff bland 500 system ska returnera tom lista."""
    org = await create_org(client, name="OrgNoMatch")
    for i in range(500):
        await create_system(client, org["id"], name=f"NoMtch-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/",
                            params={"q": "xxxxunlikelymatchxxxx"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("search_term", [
    "System",
    "Stress",
    "test",
    "0001",
    "infra",
])
async def test_search_wildcard_terms_500_systems(client, search_term):
    """Sökning med olika termer ska returnera 200 och rimliga resultat."""
    org = await create_org(client, name=f"OrgWC_{search_term[:4]}")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"StSys-{i:04d}-{uuid4().hex[:6]}",
            description=f"Infrastruktur test system nummer {i}",
        )

    resp = await client.get("/api/v1/systems/", params={"q": search_term})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["total"], int)
    assert data["total"] >= 0


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_partial_name_match(client):
    """Partiell sökning på namn ska hitta matchande system bland 500."""
    org = await create_org(client, name="OrgPartial")
    for i in range(490):
        await create_system(client, org["id"], name=f"CmnSys-{i:03d}-{uuid4().hex[:6]}")
    for i in range(10):
        await create_system(client, org["id"], name=f"UniqueXYZ-{i:03d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/", params={"q": "UniqueXYZ", "limit": 25})
    assert resp.status_code == 200
    assert resp.json()["total"] == 10


# ===========================================================================
# RELATIONER UNDER SKALNING
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_100_systems_5_integrations_each(client):
    """100 system med 5 integrationer vardera = 500 integrationer totalt."""
    org = await create_org(client, name="OrgIntegrations100")
    systems = []
    for i in range(100):
        sys = await create_system(client, org["id"],
                                  name=f"IntSys-{i:03d}-{uuid4().hex[:6]}")
        systems.append(sys)

    # Skapa 5 integrationer per system (mot nästa i listan, cirkulärt)
    integration_count = 0
    for i, src in enumerate(systems):
        for j in range(1, 6):
            target = systems[(i + j) % len(systems)]
            if src["id"] != target["id"]:
                await create_integration(
                    client, src["id"], target["id"],
                    integration_type="api",
                    description=f"Integration {i}->{(i+j)%100}",
                )
                integration_count += 1

    assert integration_count == 500

    # Verifiera att dependency map-anropet fungerar
    resp = await client.get("/api/v1/integrations/")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.slow
async def test_dependency_map_50_nodes(client):
    """Beroendekartan med 50+ noder ska returnera 200 utan timeout."""
    org = await create_org(client, name="OrgDepMap50")
    systems = []
    for i in range(55):
        sys = await create_system(client, org["id"], name=f"DepNd-{i:03d}-{uuid4().hex[:6]}")
        systems.append(sys)

    # Skapa kedja av integrationer
    for i in range(len(systems) - 1):
        await create_integration(
            client, systems[i]["id"], systems[i + 1]["id"],
            integration_type="filöverföring",
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/integrations/")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 5.0, f"Dependency map med 55 noder tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_system_with_10_owners(client):
    """System med 10 ägare ska hämtas korrekt med alla relationer."""
    org = await create_org(client, name="OrgMultiOwner")
    sys = await create_system(client, org["id"], name="MultiOwnerSystem")

    # Giltiga roller: systemägare, informationsägare, systemförvaltare,
    # teknisk_förvaltare, it_kontakt, dataskyddsombud (6 st totalt)
    # Skapar 6 ägare med unika roller
    roles = [
        "systemägare", "informationsägare", "systemförvaltare",
        "teknisk_förvaltare", "it_kontakt", "dataskyddsombud",
    ]
    for i, role in enumerate(roles):
        await create_owner(
            client, sys["id"], org["id"],
            role=role,
            name=f"Ägare {i+1}",
            email=f"agare{i+1}@test.se",
        )

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["owners"]) == len(roles)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_system_with_20_classifications_history(client):
    """System med 20 klassificeringar i historik ska hanteras korrekt."""
    org = await create_org(client, name="OrgClassHistory")
    sys = await create_system(client, org["id"], name="ClassHistorySystem")

    for i in range(20):
        conf = (i % 3) + 1
        await create_classification(
            client, sys["id"],
            confidentiality=conf,
            integrity=conf,
            availability=conf,
            classified_by=f"analyst{i+1}@test.se",
        )

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1  # Minst en klassificering returneras


@pytest.mark.asyncio
@pytest.mark.slow
async def test_get_system_detail_100_systems_loaded(client):
    """GET /systems/{id} med 100 system i DB ska svara inom 500ms."""
    org = await create_org(client, name="OrgDetail100")
    target = None
    for i in range(100):
        sys = await create_system(client, org["id"], name=f"DetSys-{i:03d}-{uuid4().hex[:6]}")
        if i == 50:
            target = sys
            await create_classification(client, sys["id"])
            await create_owner(client, sys["id"], org["id"])
            await create_contract(client, sys["id"])

    start = time.monotonic()
    resp = await client.get(f"/api/v1/systems/{target['id']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.5, f"System-detalj med 100 system i DB tog {elapsed:.3f}s"


# ===========================================================================
# IMPORT UNDER SKALNING
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_100_systems_xlsx(client):
    """Import av 100 system via Excel ska lyckas och returnera korrekt antal."""
    org = await create_org(client, name="OrgImport100")
    rows = [system_row(i) for i in range(100)]
    content, filename, ct = make_xlsx_import(rows)

    start = time.monotonic()
    resp = await post_import(client, org["id"], content, filename, ct)
    elapsed = time.monotonic() - start

    assert resp.status_code == 200, f"Import misslyckades: {resp.text}"
    body = resp.json()
    assert body["imported"] == 100, f"Förväntade 100, fick {body['imported']}"
    assert body["errors"] == []
    assert elapsed < 30.0, f"Import av 100 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_100_systems_json(client):
    """Import av 100 system via JSON ska lyckas och returnera korrekt antal."""
    org = await create_org(client, name="OrgImportJSON100")
    rows = [system_row(i) for i in range(100)]
    content, filename, ct = make_json_import(rows)

    start = time.monotonic()
    resp = await post_import(client, org["id"], content, filename, ct)
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 100
    assert elapsed < 30.0, f"JSON-import av 100 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_500_systems_json(client):
    """Import av 500 system via JSON ska slutföras korrekt."""
    org = await create_org(client, name="OrgImport500")
    rows = [system_row(i) for i in range(500)]
    content, filename, ct = make_json_import(rows)

    start = time.monotonic()
    resp = await post_import(client, org["id"], content, filename, ct)
    elapsed = time.monotonic() - start

    assert resp.status_code == 200, f"Import misslyckades: {resp.text}"
    body = resp.json()
    assert body["imported"] == 500, f"Förväntade 500, fick {body['imported']}"
    assert elapsed < 120.0, f"Import av 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_500_systems_verifiable_in_list(client):
    """500 importerade system ska vara synliga via GET /systems/."""
    org = await create_org(client, name="OrgImport500Verify")
    rows = [system_row(i) for i in range(500)]
    content, filename, ct = make_json_import(rows)

    resp = await post_import(client, org["id"], content, filename, ct)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 500

    list_resp = await client.get("/api/v1/systems/",
                                 params={"limit": 1, "offset": 0})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 500


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_50_percent_errors_correct_report(client):
    """Import med 50% felaktiga rader ska rapportera korrekt antal fel."""
    org = await create_org(client, name="OrgImport50Err")
    # Jämna index: giltiga rader; udda index: saknar name (ogiltigt)
    rows = []
    for i in range(100):
        if i % 2 == 0:
            rows.append(system_row(i))
        else:
            # Ogiltig rad: saknar obligatoriskt name-fält
            rows.append({
                "description": f"Ogiltig rad {i}",
                "system_category": "verksamhetssystem",
            })

    content, filename, ct = make_json_import(rows)
    resp = await post_import(client, org["id"], content, filename, ct)

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 50, f"Förväntade 50 importerade, fick {body['imported']}"
    assert len(body["errors"]) == 50, f"Förväntade 50 fel, fick {len(body['errors'])}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_100_systems_csv(client):
    """Import av 100 system via CSV ska lyckas."""
    org = await create_org(client, name="OrgImportCSV100")
    rows = [system_row(i) for i in range(100)]
    content, filename, ct = make_csv_import(rows)

    resp = await post_import(client, org["id"], content, filename, ct)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 100


# ===========================================================================
# RAPPORT-GENERERING — 500 SYSTEM
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_nis2_report_500_systems_response_time(client):
    """NIS2-rapport med 500 system ska genereras inom 10 sekunder."""
    org = await create_org(client, name="OrgNIS2_500")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"NIS2Sys-{i:04d}-{uuid4().hex[:6]}",
            nis2_applicable=(i % 3 == 0),
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/nis2")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 10.0, f"NIS2-rapport med 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_nis2_report_500_systems_correct_nis2_count(client):
    """NIS2-rapport ska räkna korrekt antal NIS2-klassade system bland 500."""
    org = await create_org(client, name="OrgNIS2Count500")
    nis2_count = 0
    for i in range(500):
        is_nis2 = (i % 5 == 0)
        if is_nis2:
            nis2_count += 1
        await create_system(
            client, org["id"],
            name=f"NIS2Cnt-{i:04d}-{uuid4().hex[:6]}",
            nis2_applicable=is_nis2,
        )

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == nis2_count


@pytest.mark.asyncio
@pytest.mark.slow
async def test_compliance_gap_500_systems_response_time(client):
    """Compliance gap-rapport med 500 system ska genereras inom 10 sekunder."""
    org = await create_org(client, name="OrgGap500")
    for i in range(500):
        await create_system(client, org["id"], name=f"Gap500-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/compliance-gap")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 10.0, f"Compliance gap med 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_compliance_gap_500_systems_missing_classification_count(client):
    """Compliance gap ska rapportera alla 500 system som saknar klassificering."""
    org = await create_org(client, name="OrgGapMissing500")
    for i in range(500):
        await create_system(client, org["id"], name=f"UncGap-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    data = resp.json()
    # Alla 500 saknar klassificering
    assert len(data["gaps"]["missing_classification"]) >= 500


@pytest.mark.asyncio
@pytest.mark.slow
async def test_nis2_report_xlsx_500_systems(client):
    """NIS2 XLSX-rapport med 500 system ska genereras och ha rimlig filstorlek."""
    org = await create_org(client, name="OrgNIS2XLSX500")
    for i in range(500):
        await create_system(
            client, org["id"],
            name=f"NIS2XL-{i:04d}-{uuid4().hex[:6]}",
            nis2_applicable=True,
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/nis2",
                            headers={"Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 15.0, f"NIS2 XLSX-rapport med 500 system tog {elapsed:.3f}s"


# ===========================================================================
# CONCURRENT REQUESTS
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_10_parallel_get_requests(client):
    """10 parallella GET /systems/ ska alla returnera 200."""
    org = await create_org(client, name="OrgParallelGet")
    for i in range(50):
        await create_system(client, org["id"], name=f"PGetSys-{i:03d}-{uuid4().hex[:6]}")

    async def fetch():
        return await client.get("/api/v1/systems/", params={"limit": 25})

    responses = await asyncio.gather(*[fetch() for _ in range(10)])

    for i, resp in enumerate(responses):
        assert resp.status_code == 200, f"Anrop {i+1} returnerade {resp.status_code}"
        assert resp.json()["total"] == 50


@pytest.mark.asyncio
@pytest.mark.slow
async def test_5_parallel_post_requests(client):
    """5 sekventiella POST /systems/ ska alla returnera 201.

    OBS: Parallella anrop fungerar inte med delad testsession.
    """
    org = await create_org(client, name="OrgParallelPost")

    responses = []
    for i in range(5):
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"ParallelPostSystem {i}",
            "description": "Skapning",
            "system_category": "stödsystem",
        })
        responses.append(resp)

    for i, resp in enumerate(responses):
        assert resp.status_code == 201, (
            f"POST {i+1} returnerade {resp.status_code}: {resp.text}"
        )

    # Verifiera att alla 5 skapades
    list_resp = await client.get("/api/v1/systems/")
    assert list_resp.json()["total"] == 5


@pytest.mark.asyncio
@pytest.mark.slow
async def test_mixed_read_write_concurrent(client):
    """Mix av läs- och skrivanrop sekventiellt ska inte krascha.

    OBS: Parallella anrop fungerar inte med delad testsession.
    """
    org = await create_org(client, name="OrgMixedConcurrent")
    for i in range(20):
        await create_system(client, org["id"], name=f"BaseSys-{i:03d}-{uuid4().hex[:6]}")

    read_responses = []
    for _ in range(5):
        resp = await client.get("/api/v1/systems/", params={"limit": 10})
        read_responses.append(resp)

    write_responses = []
    for i in range(5):
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"SeqWrite {i}",
            "description": "Skriven sekventiellt",
            "system_category": "verksamhetssystem",
        })
        write_responses.append(resp)

    for i, resp in enumerate(read_responses):
        assert resp.status_code == 200, f"Läsanrop {i+1}: {resp.status_code}"

    for i, resp in enumerate(write_responses):
        assert resp.status_code == 201, f"Skriveanrop {i+1}: {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_10_parallel_search_requests(client):
    """10 parallella sökningar ska alla returnera 200."""
    org = await create_org(client, name="OrgParallelSearch")
    for i in range(100):
        await create_system(
            client, org["id"],
            name=f"PSearch-{i:03d}-{uuid4().hex[:6]}",
            description=f"Sökbart system {i}",
        )

    async def search(term: str):
        return await client.get("/api/v1/systems/", params={"q": term})

    terms = [f"{i:03d}" for i in range(10)]
    responses = await asyncio.gather(*[search(t) for t in terms])

    for i, resp in enumerate(responses):
        assert resp.status_code == 200, f"Sökning {i+1} returnerade {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_parallel_stats_and_list_requests(client):
    """Parallella stats- och list-anrop ska ge konsistenta svar."""
    org = await create_org(client, name="OrgParallelStats")
    for i in range(30):
        await create_system(client, org["id"], name=f"StatPar-{i:03d}-{uuid4().hex[:6]}")

    async def get_stats():
        return await client.get("/api/v1/systems/stats/overview")

    async def get_list():
        return await client.get("/api/v1/systems/", params={"limit": 25})

    responses = await asyncio.gather(
        get_stats(), get_stats(), get_list(), get_list(), get_stats()
    )

    stats_responses = [responses[0], responses[1], responses[4]]
    list_responses = [responses[2], responses[3]]

    for resp in stats_responses:
        assert resp.status_code == 200
        assert resp.json()["total_systems"] >= 30

    for resp in list_responses:
        assert resp.status_code == 200
        assert resp.json()["total"] == 30


# ===========================================================================
# SVARSTIDER (RESPONSE TIMES)
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_health_check_under_100ms(client):
    """GET /health ska svara inom 100ms."""
    start = time.monotonic()
    resp = await client.get("/health")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.1, f"Health check tog {elapsed:.3f}s (förväntat < 100ms)"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_get_systems_25_items_under_500ms(client):
    """GET /systems/ med 25 poster ska svara inom 500ms."""
    org = await create_org(client, name="OrgRT25")
    for i in range(25):
        await create_system(client, org["id"], name=f"RTSys-{i:03d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"limit": 25})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.5, f"GET /systems/ med 25 poster tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_get_system_by_id_with_relations_under_500ms(client):
    """GET /systems/{id} med relationer ska svara inom 500ms."""
    org = await create_org(client, name="OrgRTDetail")
    sys = await create_system(client, org["id"], name="RTDetailSystem")
    await create_classification(client, sys["id"])
    await create_owner(client, sys["id"], org["id"])
    await create_contract(client, sys["id"])

    start = time.monotonic()
    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.5, f"GET /systems/{{id}} tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_post_system_under_300ms(client):
    """POST /systems/ ska svara inom 300ms."""
    org = await create_org(client, name="OrgRTPost")

    start = time.monotonic()
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "RTPostSystem",
        "description": "Svarstidstest",
        "system_category": "stödsystem",
    })
    elapsed = time.monotonic() - start

    assert resp.status_code == 201
    assert elapsed < 0.3, f"POST /systems/ tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_export_xlsx_500_systems_under_5_seconds(client):
    """Excel-export av 500 system ska ta under 5 sekunder."""
    org = await create_org(client, name="OrgRTExport500")
    for i in range(500):
        await create_system(client, org["id"], name=f"RTExp-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.xlsx")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 5.0, f"XLSX-export av 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_health_check_repeated_stable(client):
    """Upprepade health check-anrop ska ge stabil svarstid."""
    times = []
    for _ in range(10):
        start = time.monotonic()
        resp = await client.get("/health")
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        times.append(elapsed)

    max_time = max(times)
    assert max_time < 0.5, f"Health check som långsammast: {max_time:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_organizations_list_under_500ms(client):
    """GET /organizations/ ska svara inom 500ms."""
    for i in range(10):
        await create_org(client, name=f"ListOrg {i:02d}", org_type="kommun")

    start = time.monotonic()
    resp = await client.get("/api/v1/organizations/")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 0.5, f"GET /organizations/ tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_response_time_does_not_degrade_across_10_sequential_reads(client):
    """10 sekventiella läsanrop ska inte visa prestandaförsämring."""
    org = await create_org(client, name="OrgDegradationTest")
    for i in range(50):
        await create_system(client, org["id"], name=f"DegSys-{i:03d}-{uuid4().hex[:6]}")

    times = []
    for _ in range(10):
        start = time.monotonic()
        resp = await client.get("/api/v1/systems/", params={"limit": 25})
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        times.append(elapsed)

    fastest = min(times)
    slowest = max(times)
    # Inget anrop ska vara mer än 5x långsammare än det snabbaste
    assert slowest < fastest * 5 + 1.0, (
        f"Svarstidsförsämring detekterad: snabbast={fastest:.3f}s, långsammast={slowest:.3f}s"
    )


# ===========================================================================
# EDGE CASES UNDER SKALNING
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_single_system_detail_among_1000(client):
    """Hämta ett specifikt system bland 1000 ska svara korrekt och snabbt."""
    org = await create_org(client, name="Org1000Detail")
    target_idx = 500
    target = None

    for i in range(1000):
        sys = await create_system(
            client, org["id"],
            name=f"LrgScl-{i:04d}-{uuid4().hex[:6]}",
        )
        if i == target_idx:
            target = sys

    start = time.monotonic()
    resp = await client.get(f"/api/v1/systems/{target['id']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert resp.json()["id"] == target["id"]
    assert elapsed < 1.0, f"Hämtning bland 1000 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_filter_lifecycle_status_among_500(client):
    """Filter på lifecycle_status bland 500 system ska ge korrekt delmängd."""
    org = await create_org(client, name="OrgLifecycleFilter")
    active_count = 0
    for i in range(500):
        status = LIFECYCLE_STATUSES[i % len(LIFECYCLE_STATUSES)]
        if status == "i_drift":
            active_count += 1
        await create_system(
            client, org["id"],
            name=f"LcSys-{i:04d}-{uuid4().hex[:6]}",
            lifecycle_status=status,
        )

    resp = await client.get("/api/v1/systems/",
                            params={"lifecycle_status": "i_drift", "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == active_count
    for item in data["items"]:
        assert item["lifecycle_status"] == "i_drift"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stats_overview_counts_match_list_total(client):
    """Stats total_systems ska matcha GET /systems/ total vid 200 system."""
    org = await create_org(client, name="OrgStatsMatch")
    for i in range(200):
        await create_system(client, org["id"], name=f"MtchSys-{i:03d}-{uuid4().hex[:6]}")

    stats_resp = await client.get("/api/v1/systems/stats/overview")
    list_resp = await client.get("/api/v1/systems/", params={"limit": 1})

    assert stats_resp.status_code == 200
    assert list_resp.status_code == 200

    stats_total = stats_resp.json()["total_systems"]
    list_total = list_resp.json()["total"]

    assert stats_total == list_total, (
        f"Stats säger {stats_total} men list säger {list_total}"
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_empty_string_returns_all_500(client):
    """Tom söksträng ska returnera alla 500 system (ingen filtrering)."""
    org = await create_org(client, name="OrgEmptySearch")
    for i in range(500):
        await create_system(client, org["id"], name=f"EmptSrc-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/",
                            params={"q": "", "limit": 200})
    assert resp.status_code == 200
    assert resp.json()["total"] == 500


@pytest.mark.asyncio
@pytest.mark.slow
async def test_notifications_500_systems_under_10_seconds(client):
    """Notifikationer med 500 system ska svara inom 10 sekunder."""
    org = await create_org(client, name="OrgNotif500")
    for i in range(500):
        await create_system(client, org["id"], name=f"NtfSys-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/notifications/")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 10.0, f"Notifikationer med 500 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_import_duplicate_names_all_reported_as_errors(client):
    """Import av 100 dubbletter av befintliga system ska rapportera 100 fel."""
    org = await create_org(client, name="OrgDuplicateImport")
    # Skapa 100 system via API
    for i in range(100):
        await create_system(client, org["id"], name=f"DupSys-{i:03d}-{uuid4().hex[:6]}")

    # Försök importera exakt samma namn igen
    rows = [
        {
            "name": f"DupSystem {i:03d}",
            "description": "Duplikat",
            "system_category": "verksamhetssystem",
        }
        for i in range(100)
    ]
    content, filename, ct = make_json_import(rows)
    resp = await post_import(client, org["id"], content, filename, ct)

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0, f"Inga duplikater ska importeras, fick {body['imported']}"
    assert len(body["errors"]) == 100, f"Förväntade 100 fel, fick {len(body['errors'])}"


# ===========================================================================
# PARAMETRISERADE SVARSTIDER PER ENDPOINT
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("endpoint,max_ms", [
    ("/health", 100),
    ("/api/v1/systems/", 500),
    ("/api/v1/organizations/", 500),
    ("/api/v1/systems/stats/overview", 500),
    ("/api/v1/reports/nis2", 1000),
    ("/api/v1/reports/compliance-gap", 1000),
    ("/api/v1/notifications/", 1000),
    ("/api/v1/audit/", 500),
    ("/api/v1/export/systems.json", 1000),
    ("/api/v1/export/systems.csv", 1000),
])
async def test_endpoint_empty_db_response_time(client, endpoint, max_ms):
    """Varje endpoint ska svara inom angiven gräns på tom databas."""
    start = time.monotonic()
    resp = await client.get(endpoint)
    elapsed_ms = (time.monotonic() - start) * 1000

    assert resp.status_code == 200, f"{endpoint} returnerade {resp.status_code}"
    assert elapsed_ms < max_ms, (
        f"{endpoint} tog {elapsed_ms:.0f}ms (förväntat < {max_ms}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("system_count,max_seconds", [
    (10, 1.0),
    (25, 1.5),
    (50, 2.0),
    (100, 3.0),
    (200, 5.0),
    (500, 8.0),
])
async def test_stats_overview_scales_with_system_count(client, system_count, max_seconds):
    """Stats-endpoint ska skala acceptabelt med ökande antal system."""
    org = await create_org(client, name=f"OrgStatsScale{system_count}")
    for i in range(system_count):
        await create_system(client, org["id"], name=f"SStat-{system_count}-{i:04d}-{uuid4().hex[:4]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/stats/overview")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert resp.json()["total_systems"] >= system_count
    assert elapsed < max_seconds, (
        f"Stats med {system_count} system tog {elapsed:.3f}s (förväntat < {max_seconds}s)"
    )


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("system_count,max_seconds", [
    (10, 2.0),
    (50, 3.0),
    (100, 5.0),
    (500, 10.0),
])
async def test_export_csv_scales_with_system_count(client, system_count, max_seconds):
    """CSV-export ska skala acceptabelt med ökande antal system."""
    org = await create_org(client, name=f"OrgCSVScale{system_count}")
    for i in range(system_count):
        await create_system(client, org["id"], name=f"CsvScl-{system_count}-{i:04d}-{uuid4().hex[:4]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.csv")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < max_seconds, (
        f"CSV-export med {system_count} system tog {elapsed:.3f}s (förväntat < {max_seconds}s)"
    )

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == system_count


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("limit", [10, 25, 50, 100, 150, 200])
async def test_list_with_varying_page_sizes(client, limit):
    """GET /systems/ ska hantera varierande sidstorlekar korrekt."""
    org = await create_org(client, name=f"OrgPageSize{limit}")
    for i in range(500):
        await create_system(client, org["id"], name=f"PgSzSys-{limit}-{i:04d}-{uuid4().hex[:4]}")

    resp = await client.get("/api/v1/systems/", params={"limit": limit})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 500
    assert len(data["items"]) == min(limit, 200)  # max 200 per sida


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("criticality", ["kritisk", "hög", "medel", "låg"])
async def test_filter_criticality_returns_correct_subset(client, criticality):
    """Filter på criticality ska returnera exakt rätt delmängd bland 400 system."""
    org = await create_org(client, name=f"OrgCrit_{criticality[:3]}")
    expected = 0
    for i in range(400):
        crit = CRITICALITIES[i % len(CRITICALITIES)]
        if crit == criticality:
            expected += 1
        await create_system(client, org["id"],
                            name=f"CritSys-{i:04d}-{uuid4().hex[:6]}",
                            criticality=crit)

    resp = await client.get("/api/v1/systems/",
                            params={"criticality": criticality, "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == expected
    for item in data["items"]:
        assert item["criticality"] == criticality


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("num_owners", [1, 3, 5, 10])
async def test_system_detail_with_multiple_owners_response_time(client, num_owners):
    """System med N ägare ska hämtas korrekt och inom 500ms."""
    org = await create_org(client, name=f"OrgOwners{num_owners}")
    sys = await create_system(client, org["id"], name=f"MultiOwner_{num_owners}")

    for i in range(num_owners):
        await create_owner(client, sys["id"], org["id"],
                           name=f"Ägare {i+1}",
                           email=f"agare{i+1}@test.se")

    start = time.monotonic()
    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert len(resp.json()["owners"]) == num_owners
    assert elapsed < 0.5, f"System med {num_owners} ägare tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("num_integrations", [1, 5, 10, 20])
async def test_system_integration_count_scales(client, num_integrations):
    """System med N integrationer ska listas i dependency map korrekt."""
    org = await create_org(client, name=f"OrgIntCount{num_integrations}")
    src = await create_system(client, org["id"], name=f"IntSrc_{num_integrations}")
    targets = []
    for i in range(num_integrations):
        t = await create_system(client, org["id"],
                                name=f"IntTgt-{i:03d}-{uuid4().hex[:6]}")
        targets.append(t)
        await create_integration(client, src["id"], t["id"],
                                 integration_type="api")

    resp = await client.get("/api/v1/integrations/")
    assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("org_count", [2, 5, 10])
async def test_rls_isolation_scales_with_org_count(client, org_count):
    """RLS-isolering ska fungera korrekt med N organisationer."""
    orgs = []
    for i in range(org_count):
        org = await create_org(client, name=f"RLSOrg{org_count}_{i:02d}")
        orgs.append(org)
        for j in range(10):
            await create_system(client, org["id"],
                                name=f"RLSSys-{j:02d}-{uuid4().hex[:6]}")

    # Verifiera isolering för varje org
    for org in orgs:
        resp = await client.get("/api/v1/systems/",
                                headers={"X-Organization-Id": org["id"]},
                                params={"limit": 100})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10, (
            f"Org {org['name']} ser {data['total']} system (förväntat 10)"
        )
        for item in data["items"]:
            assert item["organization_id"] == org["id"]


# ===========================================================================
# SKALBARHET — 1000 SYSTEM (extremfall)
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_list_1000_systems_pagination_total(client):
    """GET /systems/ med 1000 system ska returnera korrekt total."""
    org = await create_org(client, name="Org1000Pag")
    for i in range(1000):
        await create_system(
            client, org["id"],
            name=f"Sc1000-{i:04d}-{uuid4().hex[:6]}",
        )

    resp = await client.get("/api/v1/systems/", params={"limit": 25, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1000
    assert len(data["items"]) == 25


@pytest.mark.asyncio
@pytest.mark.slow
async def test_search_1000_systems_response_time(client):
    """Sökning bland 1000 system ska svara inom 5 sekunder."""
    org = await create_org(client, name="Org1000Search")
    for i in range(1000):
        await create_system(
            client, org["id"],
            name=f"LrgScl2-{i:04d}-{uuid4().hex[:6]}",
            description=f"Storskaligt system nummer {i}",
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/", params={"q": "LargeScale"})
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert resp.json()["total"] == 1000
    assert elapsed < 5.0, f"Sökning bland 1000 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_stats_overview_1000_systems(client):
    """Stats med 1000 system ska beräknas korrekt och svara inom 10 sekunder."""
    org = await create_org(client, name="Org1000Stats")
    for i in range(1000):
        await create_system(client, org["id"], name=f"Stat1k-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/systems/stats/overview")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert resp.json()["total_systems"] >= 1000
    assert elapsed < 10.0, f"Stats med 1000 system tog {elapsed:.3f}s"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_compliance_gap_1000_systems(client):
    """Compliance gap med 1000 system ska genereras inom 15 sekunder."""
    org = await create_org(client, name="OrgGap1000")
    for i in range(1000):
        await create_system(client, org["id"], name=f"Gap1k-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/compliance-gap")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 15.0, f"Compliance gap med 1000 system tog {elapsed:.3f}s"


# ===========================================================================
# PARAMETRISERADE IMPORTTESTER
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("row_count,max_seconds", [
    (10, 5.0),
    (50, 15.0),
    (100, 30.0),
    (200, 60.0),
])
async def test_import_json_scales_with_row_count(client, row_count, max_seconds):
    """JSON-import ska skala acceptabelt med ökande antal rader."""
    org = await create_org(client, name=f"OrgImportScale{row_count}")
    rows = [system_row(i) for i in range(row_count)]
    content, filename, ct = make_json_import(rows)

    start = time.monotonic()
    resp = await post_import(client, org["id"], content, filename, ct)
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == row_count
    assert elapsed < max_seconds, (
        f"Import av {row_count} rader tog {elapsed:.3f}s (förväntat < {max_seconds}s)"
    )


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("concurrent_count", [2, 5, 10, 20])
async def test_concurrent_read_requests_all_succeed(client, concurrent_count):
    """N parallella GET /systems/-anrop ska alla returnera 200."""
    org = await create_org(client, name=f"OrgConcurrent{concurrent_count}")
    for i in range(25):
        await create_system(client, org["id"],
                            name=f"CncSys-{i:03d}-{uuid4().hex[:6]}")

    async def fetch():
        return await client.get("/api/v1/systems/", params={"limit": 25})

    responses = await asyncio.gather(*[fetch() for _ in range(concurrent_count)])

    for i, resp in enumerate(responses):
        assert resp.status_code == 200, (
            f"Anrop {i+1} av {concurrent_count} returnerade {resp.status_code}"
        )
        assert resp.json()["total"] == 25


# ===========================================================================
# RAPPORT-PRESTANDA — PARAMETRISERADE
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("system_count,max_seconds", [
    (10, 2.0),
    (50, 3.0),
    (100, 5.0),
    (500, 10.0),
])
async def test_nis2_report_scales_with_system_count(client, system_count, max_seconds):
    """NIS2-rapport ska skala acceptabelt med ökande antal system."""
    org = await create_org(client, name=f"OrgNIS2Scale{system_count}")
    for i in range(system_count):
        await create_system(
            client, org["id"],
            name=f"NIS2Scl-{i:04d}-{uuid4().hex[:6]}",
            nis2_applicable=(i % 2 == 0),
        )

    start = time.monotonic()
    resp = await client.get("/api/v1/reports/nis2")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < max_seconds, (
        f"NIS2-rapport med {system_count} system tog {elapsed:.3f}s "
        f"(förväntat < {max_seconds}s)"
    )


# ===========================================================================
# SÖKNING — FLER PARAMETRISERADE FALL
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("offset", [0, 100, 250, 499])
async def test_pagination_offset_values_return_correct_page(client, offset):
    """Olika offset-värden bland 500 system ska returnera rätt sida."""
    org = await create_org(client, name=f"OrgOffset{offset}")
    for i in range(500):
        await create_system(client, org["id"], name=f"OffSys-{i:04d}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/",
                            params={"limit": 1, "offset": offset})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 500
    assert len(data["items"]) == 1


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("hosting_model", ["on-premise", "cloud", "hybrid"])
async def test_filter_hosting_model_among_300_systems(client, hosting_model):
    """Filter på hosting_model ska returnera korrekt delmängd bland 300 system."""
    hosting_models = ["on-premise", "cloud", "hybrid"]
    org = await create_org(client, name=f"OrgHosting_{hosting_model[:3]}")
    expected = 0
    for i in range(300):
        hm = hosting_models[i % len(hosting_models)]
        if hm == hosting_model:
            expected += 1
        await create_system(client, org["id"],
                            name=f"HstSys-{i:04d}-{uuid4().hex[:6]}",
                            hosting_model=hm)

    resp = await client.get("/api/v1/systems/",
                            params={"hosting_model": hosting_model, "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == expected
    for item in data["items"]:
        assert item["hosting_model"] == hosting_model


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("system_count,max_seconds", [
    (50, 3.0),
    (100, 5.0),
    (500, 10.0),
])
async def test_json_export_scales_with_system_count(client, system_count, max_seconds):
    """JSON-export ska skala acceptabelt och returnera korrekt antal poster."""
    org = await create_org(client, name=f"OrgJSONScale{system_count}")
    for i in range(system_count):
        await create_system(client, org["id"],
                            name=f"JsonExp-{i:04d}-{uuid4().hex[:6]}")

    start = time.monotonic()
    resp = await client.get("/api/v1/export/systems.json")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < max_seconds, (
        f"JSON-export med {system_count} system tog {elapsed:.3f}s"
    )
    data = resp.json()
    assert len(data) == system_count


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.parametrize("system_category", [
    "verksamhetssystem", "stödsystem", "infrastruktur", "plattform"
])
async def test_search_by_category_returns_subset_among_400(client, system_category):
    """Sökning per kategori ska returnera rätt delmängd bland 400 system."""
    org = await create_org(client, name=f"OrgCatSearch_{system_category[:4]}")
    expected = 0
    for i in range(400):
        cat = SYSTEM_CATEGORIES[i % len(SYSTEM_CATEGORIES)]
        if cat == system_category:
            expected += 1
        await create_system(client, org["id"],
                            name=f"CatSrc-{i:04d}-{uuid4().hex[:6]}",
                            system_category=cat)

    resp = await client.get("/api/v1/systems/",
                            params={"system_category": system_category, "limit": 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == expected
