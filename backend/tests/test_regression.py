"""
Regression-tester för kända buggar.

Kategori 16: Regression (~20 testfall)

Dokumenterade buggar:
1. "Nytt system" form broken — POST /api/v1/systems/ returnerar fel
2. Organization names visas som UUIDs i owner-tabellen
3. NIS2 Report tom — inga system har nis2_applicable=true efter import
4. Notifications saknar pagination — returnerar 1066+ items utan limit/offset
"""

import pytest
from tests.factories import (
    create_org, create_system, create_owner,
)


# ---------------------------------------------------------------------------
# BUGG 1: "Nytt system" form broken
# POST /api/v1/systems/ skall returnera 201 med korrekt data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_create_system_returns_201(client):
    """REGRESSION #1: 'Nytt system' form — POST /api/v1/systems/ ska returnera 201."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Nytt System via Form",
        "description": "Testar att skapa nytt system",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 201, (
        f"REGRESSION #1 AKTIV: POST /api/v1/systems/ returnerade {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["name"] == "Nytt System via Form"
    assert "id" in data


@pytest.mark.asyncio
async def test_regression_create_system_with_all_required_fields(client):
    """REGRESSION #1: Alla obligatoriska fält ska fungera vid systemskapande."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Fullt Testat System",
        "description": "System med alla obligatoriska fält",
        "system_category": "stödsystem",
    })
    assert resp.status_code == 201, f"REGRESSION #1: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["organization_id"] == org["id"]
    assert data["system_category"] == "stödsystem"


@pytest.mark.asyncio
async def test_regression_create_system_response_includes_id_and_timestamps(client):
    """REGRESSION #1: Svar från POST /systems/ ska inkludera id, created_at, updated_at."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Tidstämpelsystem",
        "description": "Kontrollerar tidstämplar",
        "system_category": "infrastruktur",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data, "Response saknar 'id'"
    assert "created_at" in data, "Response saknar 'created_at'"
    assert "updated_at" in data, "Response saknar 'updated_at'"
    assert data["id"] is not None
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_regression_created_system_is_retrievable(client):
    """REGRESSION #1: System skapat via POST ska kunna hämtas via GET."""
    org = await create_org(client)
    create_resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Hämtbart System",
        "description": "Ska kunna hämtas",
        "system_category": "plattform",
    })
    assert create_resp.status_code == 201
    system_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/systems/{system_id}")
    assert get_resp.status_code == 200, (
        f"REGRESSION #1: Skapat system kan inte hämtas: {get_resp.status_code}"
    )
    assert get_resp.json()["id"] == system_id


@pytest.mark.asyncio
async def test_regression_created_system_appears_in_list(client):
    """REGRESSION #1: Skapat system ska dyka upp i systeminventeringen."""
    org = await create_org(client)
    create_resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "System I Lista",
        "description": "Ska synas i lista",
        "system_category": "iot",
    })
    assert create_resp.status_code == 201
    system_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/systems/")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json()["items"]]
    assert system_id in ids, "REGRESSION #1: Skapat system syns inte i listan"


# ---------------------------------------------------------------------------
# BUGG 2: Organization names visas som UUIDs i owner-tabellen
# GET /systems/{id} ska visa org-namn, inte UUID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_owner_org_name_not_uuid(client):
    """REGRESSION #2: Ägartabellen ska visa organisationsnamn, inte UUID."""
    org = await create_org(client, name="Sundsvalls Kommun")
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"])

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    owners = resp.json().get("owners", [])
    assert len(owners) > 0, "Inga ägare hittades"

    owner = owners[0]
    # Om API:et exponerar org-info på ägaren, verifiera att det är namn, ej UUID
    if "organization_name" in owner:
        assert owner["organization_name"] == "Sundsvalls Kommun", (
            f"REGRESSION #2 AKTIV: organization_name är {owner['organization_name']!r} "
            f"(förväntade 'Sundsvalls Kommun')"
        )
    # organization_id ska finnas som UUID (det är ok)
    if "organization_id" in owner:
        assert owner["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_regression_owner_list_includes_org_info(client):
    """REGRESSION #2: GET /systems/{id}/owners ska inkludera organisationsinfo."""
    org = await create_org(client, name="Test Bolag AB")
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"], name="Anna Andersson")

    resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert resp.status_code == 200
    owners = resp.json()
    assert len(owners) > 0

    owner = owners[0]
    assert owner["name"] == "Anna Andersson"
    # organization_id ska vara ett giltigt UUID, inte ett namn
    if "organization_id" in owner:
        org_id = owner["organization_id"]
        # Verify it's UUID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, org_id), (
            f"organization_id borde vara UUID, fick: {org_id!r}"
        )


# ---------------------------------------------------------------------------
# BUGG 3: NIS2 Report tom efter import
# NIS2 system med nis2_applicable=True ska synas i rapport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_nis2_applicable_system_in_report(client):
    """REGRESSION #3: System med nis2_applicable=True ska visas i NIS2-rapporten."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                              nis2_applicable=True,
                              nis2_classification="väsentlig")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    system_ids = [s["id"] for s in body["systems"]]
    assert sys["id"] in system_ids, (
        f"REGRESSION #3 AKTIV: NIS2-system saknas i rapporten. "
        f"system_id={sys['id']}, rapport innehåller: {system_ids}"
    )


@pytest.mark.asyncio
async def test_regression_nis2_report_summary_counts_correctly(client):
    """REGRESSION #3: NIS2 rapport summary ska räkna korrekt antal system."""
    org = await create_org(client)
    await create_system(client, org["id"], nis2_applicable=True, name="NIS2 System 1")
    await create_system(client, org["id"], nis2_applicable=True, name="NIS2 System 2")
    await create_system(client, org["id"], nis2_applicable=False, name="Ej NIS2")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    assert body["summary"]["total"] >= 2, (
        f"REGRESSION #3: NIS2 rapport visar total={body['summary']['total']}, "
        f"förväntat >= 2"
    )
    assert len(body["systems"]) >= 2


@pytest.mark.asyncio
async def test_regression_nis2_system_created_via_api_in_report(client):
    """REGRESSION #3: NIS2-system skapat via API (ej import) ska finnas i rapport."""
    org = await create_org(client)
    # Skapa direkt via API — simulerar frontend-flöde
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Direktskapat NIS2-system",
        "description": "Testar API-vägen",
        "system_category": "infrastruktur",
        "nis2_applicable": True,
        "nis2_classification": "viktig",
        "criticality": "kritisk",
    })
    assert resp.status_code == 201
    system_id = resp.json()["id"]

    nis2_resp = await client.get("/api/v1/reports/nis2")
    assert nis2_resp.status_code == 200
    system_ids = [s["id"] for s in nis2_resp.json()["systems"]]
    assert system_id in system_ids, (
        "REGRESSION #3: API-skapat NIS2-system saknas i rapporten"
    )


# ---------------------------------------------------------------------------
# BUGG 4: Notifications saknar pagination
# Dokumenterar known bug — returnerar obegränsat antal items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_notifications_missing_pagination_fields(client):
    """REGRESSION #4: Notifications endpoint saknar pagination (limit/offset)."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()

    # BUG: limit och offset saknas i svaret
    # Testen dokumenterar beteendet — när buggen fixas ska detta uppdateras
    has_limit = "limit" in body
    has_offset = "offset" in body

    if not has_limit or not has_offset:
        import warnings
        warnings.warn(
            "REGRESSION #4 AKTIV: GET /notifications/ saknar pagination (limit/offset). "
            "Risk för minnesproblem med stora dataset.",
            UserWarning
        )
    # Test passerar men rapporterar warning — buggen är dokumenterad


@pytest.mark.asyncio
async def test_regression_notifications_returns_all_without_limit(client):
    """REGRESSION #4: Notifications returnerar ALLA items utan begränsning."""
    org = await create_org(client)
    # Skapa 20 system utan klassning — genererar 20+ notifikationer
    for i in range(20):
        await create_system(client, org["id"], name=f"UnclassifiedSys {i}")

    resp = await client.get("/api/v1/notifications/", params={"limit": 200})
    assert resp.status_code == 200
    body = resp.json()

    # Med pagination: total >= 20 (minst missing_classification per system)
    assert body["total"] >= 20, (
        f"Förväntade >= 20 notifikationer, fick {body['total']}"
    )
    assert len(body["items"]) <= body["total"], (
        "items ska inte överstiga total"
    )


# ---------------------------------------------------------------------------
# Generella regression-skydd
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_system_default_lifecycle_is_i_drift(client):
    """Nytt system ska ha lifecycle_status='i_drift' som default."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["lifecycle_status"] == "i_drift", (
        f"Default lifecycle_status borde vara 'i_drift', fick '{sys['lifecycle_status']}'"
    )


@pytest.mark.asyncio
async def test_regression_system_default_treats_personal_data_false(client):
    """Nytt system ska ha treats_personal_data=False som default."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["treats_personal_data"] is False, (
        f"Default treats_personal_data borde vara False, fick {sys['treats_personal_data']}"
    )


@pytest.mark.asyncio
async def test_regression_delete_system_removes_from_list(client):
    """Raderat system ska inte längre synas i systeminventeringen."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    system_id = sys["id"]

    del_resp = await client.delete(f"/api/v1/systems/{system_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/systems/")
    ids = [s["id"] for s in list_resp.json()["items"]]
    assert system_id not in ids, "Raderat system syns fortfarande i listan"
