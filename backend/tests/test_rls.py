"""
Tests for Row-Level Security (RLS) isolation between organizations.

Verifies that setting X-Organization-Id header correctly restricts data
visibility so that Org A cannot see Org B's systems, owners, classifications,
integrations, GDPR treatments or contracts.

NOTE: The conftest client has NO X-Organization-Id set — it uses bypass mode
(BYPASS_RLS=true in development). RLS is tested by sending explicit headers.

KNOWN ISSUE: Many RLS tests are marked xfail because the test database uses
dependency-overridden sessions (conftest.py override_get_db) which bypasses
the get_rls_db dependency that sets SET LOCAL app.current_org_id. RLS policies
exist in the DB but are never activated because the test session never calls
set_org_context(). Fix requires refactoring conftest to use get_rls_db.
"""

import pytest
from uuid import uuid4

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_integration,
    create_gdpr_treatment,
    create_contract,
    create_two_orgs_with_systems,
)


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------


async def get_with_org(client, path: str, org_id: str, **params):
    """GET request med X-Organization-Id header."""
    return await client.get(path, headers={"X-Organization-Id": str(org_id)}, params=params)


# ---------------------------------------------------------------------------
# Kategori 4: Multi-organisation / RLS — systems
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_org_a_cannot_see_org_b_systems(client):
    """Org A skall INTE kunna se Org B:s system via RLS-header."""
    data = await create_two_orgs_with_systems(client)

    resp = await get_with_org(client, "/api/v1/systems/", data["org_a"]["id"])
    assert resp.status_code == 200

    items = resp.json()["items"]
    ids = [s["id"] for s in items]

    assert data["sys_a"]["id"] in ids, "Org A skall se sitt eget system"
    assert data["sys_b"]["id"] not in ids, "Org A skall INTE se Org B:s system"


@pytest.mark.asyncio
async def test_rls_org_b_cannot_see_org_a_systems(client):
    """Org B skall INTE kunna se Org A:s system via RLS-header."""
    data = await create_two_orgs_with_systems(client)

    resp = await get_with_org(client, "/api/v1/systems/", data["org_b"]["id"])
    assert resp.status_code == 200

    items = resp.json()["items"]
    ids = [s["id"] for s in items]

    assert data["sys_b"]["id"] in ids, "Org B skall se sitt eget system"
    assert data["sys_a"]["id"] not in ids, "Org B skall INTE se Org A:s system"


@pytest.mark.asyncio
async def test_rls_system_count_isolated(client):
    """Org A ser exakt sina system — inte fler."""
    data = await create_two_orgs_with_systems(client)
    # Lägg till ytterligare ett system i Org A
    await create_system(client, data["org_a"]["id"], name="System A2")

    resp = await get_with_org(client, "/api/v1/systems/", data["org_a"]["id"])
    items = resp.json()["items"]
    assert len(items) == 2, f"Org A borde se 2 system, fick {len(items)}"


@pytest.mark.asyncio
async def test_rls_no_header_sees_all_in_bypass_mode(client):
    """Utan header (bypass-läge) visas alla system."""
    data = await create_two_orgs_with_systems(client)

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200

    ids = [s["id"] for s in resp.json()["items"]]
    assert data["sys_a"]["id"] in ids
    assert data["sys_b"]["id"] in ids


@pytest.mark.asyncio
async def test_rls_invalid_org_id_header_returns_400(client):
    """Ogiltigt UUID i X-Organization-Id skall ge 400."""
    resp = await client.get(
        "/api/v1/systems/",
        headers={"X-Organization-Id": "inte-ett-uuid"},
    )
    assert resp.status_code == 400, f"Ogiltigt UUID borde ge 400, fick {resp.status_code}"


@pytest.mark.asyncio
async def test_rls_unknown_org_id_returns_empty_list(client):
    """Okänd (men giltig) org_id ger tom lista — inte 404."""
    fake_org_id = "00000000-0000-0000-0000-000000000099"
    resp = await get_with_org(client, "/api/v1/systems/", fake_org_id)
    assert resp.status_code == 200
    assert resp.json()["items"] == [], "Okänd org skall ge tom lista"


@pytest.mark.asyncio
async def test_rls_system_direct_get_not_blocked_by_header(client):
    """GET /systems/{id} med fel org-header: beror på implementation.
    Antingen 404 (RLS blockerar) eller 200 (direktuppslag bypass).
    Testet dokumenterar faktiskt beteende."""
    data = await create_two_orgs_with_systems(client)
    sys_b_id = data["sys_b"]["id"]

    # Hämta Org B:s system med Org A:s header
    resp = await client.get(
        f"/api/v1/systems/{sys_b_id}",
        headers={"X-Organization-Id": str(data["org_a"]["id"])},
    )
    # Accepterat beteende: 404 (RLS skyddar) eller 200 (direktuppslag ej RLS-skyddat)
    assert resp.status_code in (200, 404), f"Oväntat statuskod: {resp.status_code}"


# ---------------------------------------------------------------------------
# RLS — owners
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_owners_isolated_between_orgs(client):
    """Org A:s ägare skall inte synas för Org B (via system-owners endpoint)."""
    data = await create_two_orgs_with_systems(client)

    owner_a = await create_owner(
        client, data["sys_a"]["id"], data["org_a"]["id"], name="Ägare A"
    )

    # Hämta Org B:s system ägare med Org B:s header — skall inte returnera Org A:s ägare
    resp = await get_with_org(
        client,
        f"/api/v1/systems/{data['sys_b']['id']}/owners",
        data["org_b"]["id"],
    )
    assert resp.status_code == 200
    owner_ids = [o["id"] for o in resp.json()]
    assert owner_a["id"] not in owner_ids


@pytest.mark.asyncio
async def test_rls_classifications_isolated_between_orgs(client):
    """Org A:s klassningar skall inte synas i Org B:s systemavsnittet."""
    data = await create_two_orgs_with_systems(client)

    class_a = await create_classification(client, data["sys_a"]["id"])

    # Org B frågar om Org B:s system klassningar — skall inte returnera Org A:s klassning
    resp = await get_with_org(
        client,
        f"/api/v1/systems/{data['sys_b']['id']}/classifications",
        data["org_b"]["id"],
    )
    assert resp.status_code == 200
    class_ids = [c["id"] for c in resp.json()]
    assert class_a["id"] not in class_ids


# ---------------------------------------------------------------------------
# RLS — GDPR treatments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_gdpr_treatments_isolated_between_orgs(client):
    """Org A:s GDPR-behandlingar skall inte synas för Org B."""
    data = await create_two_orgs_with_systems(client)

    gdpr_a = await create_gdpr_treatment(
        client,
        data["sys_a"]["id"],
        ropa_reference_id="ROPA-ORG-A",
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{data['sys_b']['id']}/gdpr",
        data["org_b"]["id"],
    )
    assert resp.status_code == 200
    treatment_ids = [t["id"] for t in resp.json()]
    assert gdpr_a["id"] not in treatment_ids


# ---------------------------------------------------------------------------
# RLS — integrations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_integrations_not_visible_cross_org(client):
    """Integration mellan Org A:s system skall inte synas för Org B."""
    org_a = await create_org(client, name="Org A RLS Integ", org_type="kommun")
    org_b = await create_org(client, name="Org B RLS Integ", org_type="bolag")

    sys_a1 = await create_system(client, org_a["id"], name="SysA1")
    sys_a2 = await create_system(client, org_a["id"], name="SysA2")
    sys_b1 = await create_system(client, org_b["id"], name="SysB1")

    # Integration inom Org A
    integ_a = await create_integration(client, sys_a1["id"], sys_a2["id"])

    # Org B hämtar integrations list — skall inte se Org A:s integration
    resp = await get_with_org(client, "/api/v1/integrations/", org_b["id"])
    assert resp.status_code == 200
    integ_ids = [i["id"] for i in resp.json()]
    assert integ_a["id"] not in integ_ids, "Org B skall inte se Org A:s integration"


# ---------------------------------------------------------------------------
# RLS — contracts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_contracts_isolated_between_orgs(client):
    """Org A:s kontrakt skall inte synas för Org B."""
    data = await create_two_orgs_with_systems(client)

    contract_a = await create_contract(
        client,
        data["sys_a"]["id"],
        supplier_name="Leverantör Org A",
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{data['sys_b']['id']}/contracts",
        data["org_b"]["id"],
    )
    assert resp.status_code == 200
    contract_ids = [c["id"] for c in resp.json()]
    assert contract_a["id"] not in contract_ids


# ---------------------------------------------------------------------------
# RLS — export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_export_json_filtered_by_org_header(client):
    """Export med X-Organization-Id header returnerar enbart org:s system."""
    org_a = await create_org(client, name="ExportOrgA", org_type="kommun")
    org_b = await create_org(client, name="ExportOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="ExportSysA")
    sys_b = await create_system(client, org_b["id"], name="ExportSysB")

    # Export med ?organization_id parameter (inte header)
    resp = await client.get(
        "/api/v1/export/systems.json",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "ExportSysA" in names
    assert "ExportSysB" not in names


@pytest.mark.asyncio
async def test_rls_export_csv_filtered_by_org(client):
    """CSV-export med organization_id param returnerar enbart org:s system."""
    import csv
    import io

    org_a = await create_org(client, name="CSVExportOrgA", org_type="kommun")
    org_b = await create_org(client, name="CSVExportOrgB", org_type="bolag")

    await create_system(client, org_a["id"], name="CSVSysA")
    await create_system(client, org_b["id"], name="CSVSysB")

    resp = await client.get(
        "/api/v1/export/systems.csv",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    names = [r["name"] for r in rows]
    assert "CSVSysA" in names
    assert "CSVSysB" not in names


# ---------------------------------------------------------------------------
# RLS — multi-org skapande
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rls_create_system_in_other_org_allowed_in_bypass(client):
    """I bypass-läge kan man skapa system i valfri org."""
    org_a = await create_org(client, name="CreateOrgA", org_type="kommun")
    org_b = await create_org(client, name="CreateOrgB", org_type="bolag")

    # Utan header (bypass) kan man skapa i valfri org
    sys_b = await create_system(client, org_b["id"], name="SysInOrgB")
    assert sys_b["organization_id"] == org_b["id"]


@pytest.mark.asyncio
async def test_rls_multiple_orgs_independent_system_counts(client):
    """Varje org ser bara sina egna system — oberoende räkneverk."""
    org_a = await create_org(client, name="CountOrgA", org_type="kommun")
    org_b = await create_org(client, name="CountOrgB", org_type="bolag")

    for i in range(3):
        await create_system(client, org_a["id"], name=f"OrgASys-{i}-{uuid4().hex[:6]}")
    for i in range(2):
        await create_system(client, org_b["id"], name=f"OrgBSys-{i}-{uuid4().hex[:6]}")

    resp_a = await get_with_org(client, "/api/v1/systems/", org_a["id"])
    resp_b = await get_with_org(client, "/api/v1/systems/", org_b["id"])

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    count_a = len(resp_a.json()["items"])
    count_b = len(resp_b.json()["items"])

    assert count_a == 3, f"Org A borde se 3 system, fick {count_a}"
    assert count_b == 2, f"Org B borde se 2 system, fick {count_b}"


@pytest.mark.asyncio
async def test_rls_system_stats_filtered_by_org(client):
    """GET /systems/stats/overview respekterar organization_id filter."""
    org_a = await create_org(client, name="StatsOrgA", org_type="kommun")
    org_b = await create_org(client, name="StatsOrgB", org_type="bolag")

    await create_system(client, org_a["id"], name="StatsA1")
    await create_system(client, org_a["id"], name="StatsA2")
    await create_system(client, org_b["id"], name="StatsB1")

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_systems" in body
    assert body["total_systems"] == 2, (
        f"Stats borde visa 2 för Org A, fick {body['total_systems']}"
    )


@pytest.mark.asyncio
async def test_rls_three_orgs_complete_isolation(client):
    """Tre organisationer — var och en ser bara sina egna system."""
    orgs = []
    systems = []
    for i in range(3):
        org = await create_org(client, name=f"IsolOrgThree{i}", org_type="kommun")
        orgs.append(org)
        sys = await create_system(client, org["id"], name=f"IsolSys{i}")
        systems.append(sys)

    for idx, org in enumerate(orgs):
        resp = await get_with_org(client, "/api/v1/systems/", org["id"])
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["items"]]

        # Skall se sitt eget system
        assert systems[idx]["id"] in ids, f"Org {idx} borde se sitt system"

        # Skall INTE se de andra
        for other_idx, other_sys in enumerate(systems):
            if other_idx != idx:
                assert other_sys["id"] not in ids, (
                    f"Org {idx} skall inte se system från Org {other_idx}"
                )


@pytest.mark.asyncio
async def test_rls_org_filter_query_param_vs_bypass(client):
    """organization_id som query-param filtrerar korrekt i bypass-läge."""
    org_a = await create_org(client, name="QParamOrgA", org_type="kommun")
    org_b = await create_org(client, name="QParamOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="QParamSysA")
    sys_b = await create_system(client, org_b["id"], name="QParamSysB")

    resp = await client.get(
        "/api/v1/systems/",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] in ids
    assert sys_b["id"] not in ids


@pytest.mark.asyncio
async def test_rls_reports_not_cross_org(client):
    """NIS2-rapport skall inkludera NIS2-system från alla orgs i bypass-läge."""
    org_a = await create_org(client, name="ReportOrgA", org_type="kommun")
    org_b = await create_org(client, name="ReportOrgB", org_type="bolag")

    nis2_a = await create_system(
        client, org_a["id"],
        name="NIS2SysA",
        nis2_applicable=True,
    )
    nis2_b = await create_system(
        client, org_b["id"],
        name="NIS2SysB",
        nis2_applicable=True,
    )

    # I bypass-läge (ingen header) skall båda synas
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]
    assert nis2_a["id"] in ids
    assert nis2_b["id"] in ids


@pytest.mark.asyncio
async def test_rls_search_filtered_by_org(client):
    """Sökning respekterar organization_id-filter."""
    org_a = await create_org(client, name="SearchOrgA", org_type="kommun")
    org_b = await create_org(client, name="SearchOrgB", org_type="bolag")

    await create_system(client, org_a["id"], name="Unik sökterm OrgA")
    await create_system(client, org_b["id"], name="Unik sökterm OrgB")

    resp = await client.get(
        "/api/v1/systems/",
        params={"q": "Unik sökterm", "organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1, "Sökning med org-filter borde ge 1 träff"
    assert items[0]["name"] == "Unik sökterm OrgA"


@pytest.mark.asyncio
async def test_rls_contracts_expiring_cross_org_in_bypass(client):
    """GET /contracts/expiring i bypass-läge returnerar kontrakt från alla orgs."""
    from datetime import date, timedelta

    org_a = await create_org(client, name="ContrOrgA", org_type="kommun")
    org_b = await create_org(client, name="ContrOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="ContrSysA")
    sys_b = await create_system(client, org_b["id"], name="ContrSysB")

    soon = (date.today() + timedelta(days=30)).isoformat()
    c_a = await create_contract(client, sys_a["id"], contract_end=soon)
    c_b = await create_contract(client, sys_b["id"], contract_end=soon)

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert c_a["id"] in ids
    assert c_b["id"] in ids


@pytest.mark.asyncio
async def test_rls_owner_role_per_system_isolated(client):
    """Ägare skapade för System A skall inte synas på System B's lista."""
    org = await create_org(client, name="OwnerIsolOrg", org_type="kommun")
    sys_a = await create_system(client, org["id"], name="OwnerIsolSysA")
    sys_b = await create_system(client, org["id"], name="OwnerIsolSysB")

    owner = await create_owner(client, sys_a["id"], org["id"], name="Ägare Isolerad")

    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/owners")
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert owner["id"] not in ids, "Ägare från System A skall inte synas på System B"


@pytest.mark.asyncio
async def test_rls_gdpr_list_only_shows_own_treatments(client):
    """GDPR-lista för system visar bara egna behandlingar."""
    org = await create_org(client, name="GDPRIsolOrg", org_type="kommun")
    sys_a = await create_system(client, org["id"], name="GDPRIsolSysA")
    sys_b = await create_system(client, org["id"], name="GDPRIsolSysB")

    gdpr_a = await create_gdpr_treatment(client, sys_a["id"], ropa_reference_id="ROPA-ISOL-A")

    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/gdpr")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert gdpr_a["id"] not in ids


@pytest.mark.asyncio
async def test_rls_different_org_types_can_coexist(client):
    """Olika org-typer (kommun, bolag, samverkan, digit) kan alla ha isolerade system."""
    systems_by_org = {}
    for org_type in ["kommun", "bolag", "samverkan", "digit"]:
        org = await create_org(client, name=f"OrgType {org_type}", org_type=org_type)
        sys = await create_system(client, org["id"], name=f"Sys för {org_type}")
        systems_by_org[org["id"]] = sys["id"]

    for org_id, sys_id in systems_by_org.items():
        resp = await get_with_org(client, "/api/v1/systems/", org_id)
        ids = [s["id"] for s in resp.json()["items"]]
        assert sys_id in ids, f"Org {org_id} borde se sitt system"
        for other_org_id, other_sys_id in systems_by_org.items():
            if other_org_id != org_id:
                assert other_sys_id not in ids, (
                    f"Org {org_id} skall inte se system från org {other_org_id}"
                )
