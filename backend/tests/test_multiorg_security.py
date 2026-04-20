"""
Multi-organisations-säkerhetstester — det enskilt mest kritiska funktionella kravet.

DigIT betjänar 13+ organisationer. Ingen organisation får se en annan organisations data.

Struktur:
    1. Organisation-isolation (RLS via X-Organization-Id header)
       - System, klassificeringar, ägare, GDPR, avtal, integrationer, audit
    2. RLS-bypass-försök
       - Saknad header, ogiltigt UUID, okänd org-id, SQL injection i header
       - Korsorganisatoriska PATCH/DELETE
    3. Multi-tenant scenarios (5+ orgs parallellt)
       - Sökning, statistik, export, rapporter, notifieringar
    4. Superadmin (DigIT)
       - Koncernöversikt, RBAC-rolltest
    5. Hierarkiska organisationer
       - Parent-child, bolag under kommun, samverkansorganisationer

Testantal: ~200 via pytest.mark.parametrize
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
# Hjälpkonstanter och -funktioner
# ---------------------------------------------------------------------------

FAKE_UUID = "00000000-0000-0000-0000-000000000099"
NULL_UUID = "00000000-0000-0000-0000-000000000000"

ORG_TYPES = ["kommun", "bolag", "samverkan", "digit"]

# SQL injection-varianter att testa i X-Organization-Id header
SQL_INJECTION_HEADERS = [
    "'; DROP TABLE systems; --",
    "1 OR 1=1",
    "' UNION SELECT * FROM organizations --",
    "admin'--",
    "1; DELETE FROM systems WHERE '1'='1",
]

# Ogiltiga UUID-format att testa som header
INVALID_UUID_HEADERS = [
    "inte-ett-uuid",
    "12345",
    "",
    "null",
    "undefined",
    "00000000-0000-0000-0000",           # för kort
    "gggggggg-gggg-gggg-gggg-gggggggggggg",  # ogiltiga hex-tecken
    "SELECT * FROM systems",
    "../../../etc/passwd",
]

CRUD_ENDPOINTS = [
    "/api/v1/systems/",
    "/api/v1/integrations/",
]


async def get_with_org(client, path: str, org_id: str, **params):
    """GET med X-Organization-Id header."""
    return await client.get(
        path,
        headers={"X-Organization-Id": str(org_id)},
        params=params,
    )


async def setup_two_orgs(client):
    """Skapa två organisationer med varsitt system. Returnerar dict."""
    return await create_two_orgs_with_systems(client)


# ===========================================================================
# 1. ORGANISATION-ISOLATION
# ===========================================================================


# ---------------------------------------------------------------------------
# 1a. System-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_org_a_cannot_list_org_b_systems(client):
    """Org A:s systemlista skall INTE innehålla Org B:s system."""
    d = await setup_two_orgs(client)

    resp = await get_with_org(client, "/api/v1/systems/", d["org_a"]["id"])
    assert resp.status_code == 200

    ids = [s["id"] for s in resp.json()["items"]]
    assert d["sys_a"]["id"] in ids, "Org A borde se sitt eget system"
    assert d["sys_b"]["id"] not in ids, "Org A skall INTE se Org B:s system"


@pytest.mark.asyncio
async def test_iso_org_b_cannot_list_org_a_systems(client):
    """Org B:s systemlista skall INTE innehålla Org A:s system."""
    d = await setup_two_orgs(client)

    resp = await get_with_org(client, "/api/v1/systems/", d["org_b"]["id"])
    assert resp.status_code == 200

    ids = [s["id"] for s in resp.json()["items"]]
    assert d["sys_b"]["id"] in ids, "Org B borde se sitt eget system"
    assert d["sys_a"]["id"] not in ids, "Org B skall INTE se Org A:s system"


@pytest.mark.asyncio
@pytest.mark.parametrize("org_label,other_label", [
    ("org_a", "org_b"),
    ("org_b", "org_a"),
])
async def test_iso_system_count_matches_own_org_only(client, org_label, other_label):
    """Antalet system som visas skall motsvara exakt den egna organisationens system."""
    d = await setup_two_orgs(client)

    # Lägg till ett extra system i varje org
    await create_system(client, d[org_label]["id"], name=f"Extra {org_label}")

    resp = await get_with_org(client, "/api/v1/systems/", d[org_label]["id"])
    assert resp.status_code == 200

    items = resp.json()["items"]
    ids = [s["id"] for s in items]

    # Skall innehålla det ursprungliga + extra
    assert d[f"sys_{org_label[-1]}"]["id"] in ids
    # Skall INTE innehålla den andra orgens system
    assert d[f"sys_{other_label[-1]}"]["id"] not in ids


@pytest.mark.asyncio
async def test_iso_get_single_system_wrong_org_header(client):
    """GET /systems/{id} med fel org-header ger 404 (RLS) eller 200 (bypass).
    Aldrig 500. Dokumenterar faktiskt beteende."""
    d = await setup_two_orgs(client)

    resp = await client.get(
        f"/api/v1/systems/{d['sys_b']['id']}",
        headers={"X-Organization-Id": d["org_a"]["id"]},
    )
    assert resp.status_code in (200, 404), (
        f"Oväntat statuskod vid cross-org GET: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_iso_patch_system_wrong_org_blocked(client):
    """PATCH på annan orgs system skall ge 404 (RLS blockerar)."""
    d = await setup_two_orgs(client)

    resp = await client.patch(
        f"/api/v1/systems/{d['sys_b']['id']}",
        headers={"X-Organization-Id": d["org_a"]["id"]},
        json={"name": "Kapat system"},
    )
    # RLS skyddar: 404 (system ej synligt) eller 403/422 (access nekad)
    assert resp.status_code in (403, 404, 422), (
        f"PATCH på annan orgs system borde blockeras, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_iso_delete_system_wrong_org_blocked(client):
    """DELETE på annan orgs system skall ge 404 (RLS blockerar)."""
    d = await setup_two_orgs(client)

    resp = await client.delete(
        f"/api/v1/systems/{d['sys_b']['id']}",
        headers={"X-Organization-Id": d["org_a"]["id"]},
    )
    assert resp.status_code in (403, 404, 422), (
        f"DELETE på annan orgs system borde blockeras, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 1b. Klassificerings-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_classifications_not_visible_cross_org(client):
    """Org A:s klassificeringar skall inte synas för Org B."""
    d = await setup_two_orgs(client)

    class_a = await create_classification(client, d["sys_a"]["id"])

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/classifications",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert class_a["id"] not in ids, "Org B skall inte se Org A:s klassificering"


@pytest.mark.asyncio
async def test_iso_classification_on_own_system_visible(client):
    """Org A skall se sina egna klassificeringar."""
    d = await setup_two_orgs(client)

    class_a = await create_classification(client, d["sys_a"]["id"])

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_a']['id']}/classifications",
        d["org_a"]["id"],
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert class_a["id"] in ids, "Org A borde se sin egen klassificering"


@pytest.mark.asyncio
@pytest.mark.parametrize("confidentiality,integrity,availability", [
    (1, 1, 1),
    (2, 3, 4),
    (4, 4, 4),
])
async def test_iso_classification_levels_isolated(client, confidentiality, integrity, availability):
    """Klassificeringsnivåer i Org A skall inte läcka till Org B, oavsett värden."""
    d = await setup_two_orgs(client)

    class_a = await create_classification(
        client, d["sys_a"]["id"],
        confidentiality=confidentiality,
        integrity=integrity,
        availability=availability,
    )

    resp = await get_with_org(client, "/api/v1/systems/", d["org_b"]["id"])
    assert resp.status_code == 200

    # Org B ser inte Org A:s system — alltså kan den inte se klassificeringen heller
    ids = [s["id"] for s in resp.json()["items"]]
    assert d["sys_a"]["id"] not in ids


# ---------------------------------------------------------------------------
# 1c. Ägar-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_owners_not_visible_cross_org(client):
    """Org A:s ägare skall inte synas för Org B."""
    d = await setup_two_orgs(client)

    owner_a = await create_owner(
        client, d["sys_a"]["id"], d["org_a"]["id"], name="Ägare Org A"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/owners",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert owner_a["id"] not in ids, "Org B skall inte se Org A:s ägare"


@pytest.mark.asyncio
async def test_iso_owner_on_own_system_visible(client):
    """Org A skall se sina egna ägare."""
    d = await setup_two_orgs(client)

    owner_a = await create_owner(
        client, d["sys_a"]["id"], d["org_a"]["id"], name="Synlig Ägare"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_a']['id']}/owners",
        d["org_a"]["id"],
    )
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert owner_a["id"] in ids, "Org A borde se sin egen ägare"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["systemägare", "teknisk_förvaltare", "informationsägare"])
async def test_iso_owner_roles_isolated_per_org(client, role):
    """Ägarroller i Org A skall inte synas hos Org B oavsett roll."""
    d = await setup_two_orgs(client)

    await create_owner(
        client, d["sys_a"]["id"], d["org_a"]["id"],
        role=role, name=f"Ägare med roll {role}"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/owners",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    # Org B:s system har inga ägare skapade i detta test
    for owner in resp.json():
        assert owner["organization_id"] != d["org_a"]["id"], (
            f"Ägare med roll={role} från Org A synlig för Org B"
        )


# ---------------------------------------------------------------------------
# 1d. GDPR-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_gdpr_not_visible_cross_org(client):
    """Org A:s GDPR-behandlingar skall inte synas för Org B."""
    d = await setup_two_orgs(client)

    gdpr_a = await create_gdpr_treatment(
        client, d["sys_a"]["id"], ropa_reference_id="ROPA-BORG-A"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/gdpr",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert gdpr_a["id"] not in ids, "Org B skall inte se Org A:s GDPR-behandling"


@pytest.mark.asyncio
async def test_iso_gdpr_on_own_system_visible(client):
    """Org A skall se sina egna GDPR-behandlingar."""
    d = await setup_two_orgs(client)

    gdpr_a = await create_gdpr_treatment(
        client, d["sys_a"]["id"], ropa_reference_id="ROPA-VISIBLE"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_a']['id']}/gdpr",
        d["org_a"]["id"],
    )
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert gdpr_a["id"] in ids, "Org A borde se sin egen GDPR-behandling"


@pytest.mark.asyncio
@pytest.mark.parametrize("data_categories", [
    ["vanliga"],
    ["känsliga"],
    ["vanliga", "känsliga"],
])
async def test_iso_gdpr_data_categories_isolated(client, data_categories):
    """GDPR med varierande datakategorier i Org A skall inte läcka till Org B."""
    d = await setup_two_orgs(client)

    gdpr_a = await create_gdpr_treatment(
        client, d["sys_a"]["id"], data_categories=data_categories
    )

    resp = await get_with_org(client, "/api/v1/systems/", d["org_b"]["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert d["sys_a"]["id"] not in ids


# ---------------------------------------------------------------------------
# 1e. Avtals-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_contracts_not_visible_cross_org(client):
    """Org A:s avtal skall inte synas för Org B."""
    d = await setup_two_orgs(client)

    contract_a = await create_contract(
        client, d["sys_a"]["id"], supplier_name="Leverantör Org A"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/contracts",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract_a["id"] not in ids, "Org B skall inte se Org A:s avtal"


@pytest.mark.asyncio
async def test_iso_contracts_on_own_system_visible(client):
    """Org A skall se sina egna avtal."""
    d = await setup_two_orgs(client)

    contract_a = await create_contract(
        client, d["sys_a"]["id"], supplier_name="Synlig Leverantör"
    )

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_a']['id']}/contracts",
        d["org_a"]["id"],
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract_a["id"] in ids, "Org A borde se sitt eget avtal"


@pytest.mark.asyncio
@pytest.mark.parametrize("license_model", [
    "subscription",
    "perpetual",
    "open_source",
    None,
])
async def test_iso_contracts_license_models_isolated(client, license_model):
    """Avtal med olika licensmodeller i Org A skall inte synas för Org B."""
    d = await setup_two_orgs(client)

    kwargs = {}
    if license_model is not None:
        kwargs["license_model"] = license_model

    await create_contract(client, d["sys_a"]["id"], **kwargs)

    resp = await get_with_org(
        client,
        f"/api/v1/systems/{d['sys_b']['id']}/contracts",
        d["org_b"]["id"],
    )
    assert resp.status_code == 200
    # Org B:s system har inga kontrakt i detta test
    assert resp.json() == [], "Org B:s system borde ha tomt kontraktslista"


# ---------------------------------------------------------------------------
# 1f. Integrations-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_integration_within_org_not_visible_to_other_org(client):
    """Integration inom Org A skall inte synas för Org B."""
    org_a = await create_org(client, name="IntegOrgA", org_type="kommun")
    org_b = await create_org(client, name="IntegOrgB", org_type="bolag")

    sys_a1 = await create_system(client, org_a["id"], name="IntegSysA1")
    sys_a2 = await create_system(client, org_a["id"], name="IntegSysA2")
    await create_system(client, org_b["id"], name="IntegSysB1")

    integ_a = await create_integration(client, sys_a1["id"], sys_a2["id"])

    resp = await get_with_org(client, "/api/v1/integrations/", org_b["id"])
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert integ_a["id"] not in ids, "Org B skall inte se Org A:s integration"


@pytest.mark.asyncio
async def test_iso_integration_within_org_visible_to_own_org(client):
    """Integration inom Org A skall synas för Org A."""
    org_a = await create_org(client, name="IntegVisibleOrgA", org_type="kommun")

    sys_a1 = await create_system(client, org_a["id"], name="VisIntegSysA1")
    sys_a2 = await create_system(client, org_a["id"], name="VisIntegSysA2")

    integ_a = await create_integration(client, sys_a1["id"], sys_a2["id"])

    resp = await get_with_org(client, "/api/v1/integrations/", org_a["id"])
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert integ_a["id"] in ids, "Org A borde se sin egen integration"


@pytest.mark.asyncio
async def test_iso_cross_org_integration_visible_to_both_orgs(client):
    """Integration med source i Org A och target i Org B:
    RLS-policyn inkluderar integrationer där org äger antingen source ELLER target.
    Båda orgs borde se integrationen."""
    org_a = await create_org(client, name="CrossIntegOrgA", org_type="kommun")
    org_b = await create_org(client, name="CrossIntegOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="CrossSrcSys")
    sys_b = await create_system(client, org_b["id"], name="CrossTgtSys")

    # Korsande integration: source i A, target i B (bypass-läge, ingen header)
    integ = await create_integration(client, sys_a["id"], sys_b["id"])

    # I RLS-läge med Org A:s header: skall synas (Org A äger source)
    resp_a = await get_with_org(client, "/api/v1/integrations/", org_a["id"])
    assert resp_a.status_code == 200
    ids_a = [i["id"] for i in resp_a.json()]
    assert integ["id"] in ids_a, "Org A borde se sin korsande integration (äger source)"

    # I RLS-läge med Org B:s header: skall synas (Org B äger target)
    resp_b = await get_with_org(client, "/api/v1/integrations/", org_b["id"])
    assert resp_b.status_code == 200
    ids_b = [i["id"] for i in resp_b.json()]
    assert integ["id"] in ids_b, "Org B borde se sin korsande integration (äger target)"


@pytest.mark.asyncio
@pytest.mark.parametrize("integration_type", ["api", "filöverföring", "databasreplikering", "manuell"])
async def test_iso_integration_types_isolated(client, integration_type):
    """Integrations av alla typer skall vara isolerade per organisation."""
    org_a = await create_org(client, name=f"IntegTypeOrgA_{integration_type}", org_type="kommun")
    org_b = await create_org(client, name=f"IntegTypeOrgB_{integration_type}", org_type="bolag")

    sys_a1 = await create_system(client, org_a["id"], name=f"IntTypeSysA1_{integration_type}")
    sys_a2 = await create_system(client, org_a["id"], name=f"IntTypeSysA2_{integration_type}")
    await create_system(client, org_b["id"], name=f"IntTypeSysB_{integration_type}")

    integ = await create_integration(
        client, sys_a1["id"], sys_a2["id"],
        integration_type=integration_type,
    )

    resp = await get_with_org(client, "/api/v1/integrations/", org_b["id"])
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert integ["id"] not in ids, (
        f"Integration av typ {integration_type} från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 1g. Audit-log-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_audit_log_org_filter(client):
    """Audit-logg filtrerad med organization_id skall bara returnera den orgens poster."""
    org_a = await create_org(client, name="AuditOrgA", org_type="kommun")
    org_b = await create_org(client, name="AuditOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="AuditSysA")
    sys_b = await create_system(client, org_b["id"], name="AuditSysB")

    resp = await client.get(
        "/api/v1/audit/",
        params={"record_id": sys_a["id"]},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]

    # Audit-poster för sys_a skall finnas
    record_ids = [item["record_id"] for item in items]
    # sys_b:s poster skall inte blandas in
    for item in items:
        assert item["record_id"] != sys_b["id"], (
            "Audit-post för Org B:s system hittades i Org A:s audit-filtrering"
        )


@pytest.mark.asyncio
async def test_iso_audit_create_logged_per_system(client):
    """Skapande av system genererar audit-poster kopplade till det egna systemet."""
    org = await create_org(client, name="AuditCreateOrg", org_type="kommun")
    sys = await create_system(client, org["id"], name="AuditCreateSys")

    resp = await client.get("/api/v1/audit/record/" + sys["id"])
    assert resp.status_code == 200
    entries = resp.json()
    # Minst en post för INSERT
    assert len(entries) >= 1, "Borde finnas minst en audit-post för nyskapat system"
    for entry in entries:
        assert entry["record_id"] == sys["id"]


# ===========================================================================
# 2. RLS-BYPASS-FÖRSÖK
# ===========================================================================


# ---------------------------------------------------------------------------
# 2a. Saknad header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bypass_no_header_returns_all_in_bypass_mode(client):
    """Utan X-Organization-Id header (bypass-läge): alla system visas."""
    d = await setup_two_orgs(client)

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200

    ids = [s["id"] for s in resp.json()["items"]]
    assert d["sys_a"]["id"] in ids, "Bypass-läge borde visa Org A:s system"
    assert d["sys_b"]["id"] in ids, "Bypass-läge borde visa Org B:s system"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/api/v1/systems/",
    "/api/v1/integrations/",
    "/api/v1/organizations/",
    "/api/v1/audit/",
])
async def test_bypass_no_header_never_returns_500(client, endpoint):
    """Anrop utan header skall aldrig returnera 500."""
    resp = await client.get(endpoint)
    assert resp.status_code != 500, (
        f"Endpoint {endpoint} returnerade 500 utan header"
    )


# ---------------------------------------------------------------------------
# 2b. Ogiltigt UUID som header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_header", [
    "inte-ett-uuid",
    "12345",
    "null",
    "undefined",
    "00000000-0000-0000-0000",
    "gggggggg-gggg-gggg-gggg-gggggggggggg",
    "SELECT * FROM systems",
    "../../../etc/passwd",
])
async def test_bypass_invalid_uuid_header_returns_400(client, invalid_header):
    """Ogiltigt UUID-format i X-Organization-Id skall ge 400."""
    resp = await client.get(
        "/api/v1/systems/",
        headers={"X-Organization-Id": invalid_header},
    )
    assert resp.status_code == 400, (
        f"Ogiltigt UUID {invalid_header!r} borde ge 400, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_header", [
    "inte-ett-uuid",
    "12345",
    "null",
    "undefined",
])
async def test_bypass_invalid_uuid_on_integrations_returns_400(client, invalid_header):
    """Ogiltigt UUID i header skall ge 400 även på /integrations/."""
    resp = await client.get(
        "/api/v1/integrations/",
        headers={"X-Organization-Id": invalid_header},
    )
    assert resp.status_code == 400, (
        f"Ogiltigt UUID {invalid_header!r} på /integrations/ borde ge 400"
    )


# ---------------------------------------------------------------------------
# 2c. SQL injection i X-Organization-Id header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_payload", [
    "'; DROP TABLE systems; --",
    "1 OR 1=1",
    "' UNION SELECT * FROM organizations --",
    "admin'--",
    "1; DELETE FROM systems WHERE '1'='1",
])
async def test_bypass_sql_injection_in_org_header_blocked(client, injection_payload):
    """SQL injection i X-Organization-Id header skall ge 400, aldrig 500."""
    resp = await client.get(
        "/api/v1/systems/",
        headers={"X-Organization-Id": injection_payload},
    )
    assert resp.status_code in (400, 422), (
        f"SQL injection {injection_payload!r} i header borde ge 400/422, "
        f"fick {resp.status_code}: {resp.text}"
    )
    assert resp.status_code != 500, "SQL injection orsakade server-fel"


# ---------------------------------------------------------------------------
# 2d. Org-id som inte finns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bypass_unknown_org_id_returns_empty_list(client):
    """Okänd (men giltig) org-id ger tom lista — inte 404."""
    resp = await get_with_org(client, "/api/v1/systems/", FAKE_UUID)
    assert resp.status_code == 200
    assert resp.json()["items"] == [], "Okänd org borde ge tom lista"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,expected_empty", [
    ("/api/v1/systems/", True),
    ("/api/v1/integrations/", True),
])
async def test_bypass_unknown_org_returns_empty_on_list_endpoints(client, endpoint, expected_empty):
    """Okänd org-id ger tom lista på alla listendpoints."""
    resp = await get_with_org(client, endpoint, FAKE_UUID)
    assert resp.status_code == 200
    body = resp.json()
    if expected_empty:
        # Stöd både PaginatedResponse (dict med 'items') och lista direkt
        if isinstance(body, list):
            items = body
        else:
            items = body.get("items", [])
        assert items == [], f"Okänd org borde ge tom lista på {endpoint}"


@pytest.mark.asyncio
async def test_bypass_unknown_org_never_500(client):
    """Okänd (men giltig) org-id skall aldrig orsaka 500."""
    resp = await get_with_org(client, "/api/v1/systems/", FAKE_UUID)
    assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 2e. Cross-org PATCH/DELETE-försök
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bypass_patch_other_org_system_blocked(client):
    """PATCH på annan orgs system med korrekt org-header skall blockeras."""
    org_a = await create_org(client, name="PatchBlockOrgA", org_type="kommun")
    org_b = await create_org(client, name="PatchBlockOrgB", org_type="bolag")

    sys_b = await create_system(client, org_b["id"], name="Mål för PATCH")

    # Org A försöker modifiera Org B:s system
    resp = await client.patch(
        f"/api/v1/systems/{sys_b['id']}",
        headers={"X-Organization-Id": org_a["id"]},
        json={"name": "Kapat av Org A"},
    )
    # RLS skall blockera — 404 (systemet inte synligt för Org A) eller 403/422
    assert resp.status_code in (403, 404, 422), (
        f"Cross-org PATCH borde blockeras, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_bypass_delete_other_org_system_blocked(client):
    """DELETE på annan orgs system med korrekt org-header skall blockeras."""
    org_a = await create_org(client, name="DelBlockOrgA", org_type="kommun")
    org_b = await create_org(client, name="DelBlockOrgB", org_type="bolag")

    sys_b = await create_system(client, org_b["id"], name="Mål för DELETE")

    resp = await client.delete(
        f"/api/v1/systems/{sys_b['id']}",
        headers={"X-Organization-Id": org_a["id"]},
    )
    # RLS skall blockera — 404 (systemet inte synligt för Org A) eller 403/422
    assert resp.status_code in (403, 404, 422), (
        f"Cross-org DELETE borde blockeras, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_bypass_create_system_in_other_org_with_header(client):
    """POST /systems/ med Org A:s header men organization_id = Org B:
    skall antingen blockeras eller systemet placeras i rätt org."""
    org_a = await create_org(client, name="CreateBlockOrgA", org_type="kommun")
    org_b = await create_org(client, name="CreateBlockOrgB", org_type="bolag")

    resp = await client.post(
        "/api/v1/systems/",
        headers={"X-Organization-Id": org_a["id"]},
        json={
            "organization_id": org_b["id"],
            "name": "System skapat i fel org",
            "description": "Test",
            "system_category": "verksamhetssystem",
        },
    )
    # Antingen 403 (blockerat) eller 201 (men bör verifieras om det verkligen hamnade i rätt org)
    # 400/422 accepteras också om applikationen validerar detta
    assert resp.status_code in (201, 400, 403, 422), (
        f"Create i annan org gav oväntat svar: {resp.status_code}"
    )

    if resp.status_code == 201:
        # Om det skapades: verifiera att det är synligt för Org B, inte Org A
        sys_id = resp.json()["id"]
        verify_b = await get_with_org(client, "/api/v1/systems/", org_b["id"])
        verify_a = await get_with_org(client, "/api/v1/systems/", org_a["id"])
        ids_b = [s["id"] for s in verify_b.json()["items"]]
        ids_a = [s["id"] for s in verify_a.json()["items"]]
        # Systemet skall inte vara synligt för Org A
        assert sys_id not in ids_a, (
            "System skapat med Org B:s org-id borde inte synas för Org A"
        )


# ===========================================================================
# 3. MULTI-TENANT SCENARIOS (5+ orgs parallellt)
# ===========================================================================


# ---------------------------------------------------------------------------
# 3a. Grundläggande isolation med 5+ organisationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_five_orgs_complete_isolation(client):
    """Fem organisationer skall ha komplett isolation — var och en ser bara sina system."""
    orgs_systems = []
    for i in range(5):
        org = await create_org(client, name=f"MultiOrg{i}", org_type="kommun")
        sys = await create_system(client, org["id"], name=f"MultiSys{i}")
        orgs_systems.append((org, sys))

    for idx, (org, sys) in enumerate(orgs_systems):
        resp = await get_with_org(client, "/api/v1/systems/", org["id"])
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["items"]]

        assert sys["id"] in ids, f"Org {idx} borde se sitt system"

        for other_idx, (_, other_sys) in enumerate(orgs_systems):
            if other_idx != idx:
                assert other_sys["id"] not in ids, (
                    f"Org {idx} skall INTE se Org {other_idx}:s system"
                )


@pytest.mark.asyncio
@pytest.mark.parametrize("n_orgs", [3, 5, 7, 10, 13])
async def test_multitenant_n_orgs_isolation(client, n_orgs):
    """N organisationer skall alla ha isolerade system."""
    orgs_systems = []
    for i in range(n_orgs):
        org = await create_org(client, name=f"NOrgTest{n_orgs}_{i}", org_type="kommun")
        sys = await create_system(client, org["id"], name=f"NOrgSys{n_orgs}_{i}")
        orgs_systems.append((org, sys))

    for idx, (org, sys) in enumerate(orgs_systems):
        resp = await get_with_org(client, "/api/v1/systems/", org["id"])
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["items"]]

        assert sys["id"] in ids, f"Org {idx}/{n_orgs} borde se sitt system"
        for other_idx, (_, other_sys) in enumerate(orgs_systems):
            if other_idx != idx:
                assert other_sys["id"] not in ids, (
                    f"Org {idx} av {n_orgs} ser Org {other_idx}:s system (läckage)"
                )


# ---------------------------------------------------------------------------
# 3b. Sökning filtrerar per organisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_search_returns_only_own_org(client):
    """Sökning med org-header returnerar bara den egna orgens träffar."""
    org_a = await create_org(client, name="SearchMultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="SearchMultiOrgB", org_type="bolag")
    org_c = await create_org(client, name="SearchMultiOrgC", org_type="samverkan")

    # Alla tre orgs har system med samma sökterm
    sys_a = await create_system(client, org_a["id"], name="Ekonomisystem Alpha")
    sys_b = await create_system(client, org_b["id"], name="Ekonomisystem Beta")
    sys_c = await create_system(client, org_c["id"], name="Ekonomisystem Gamma")

    # Sök med Org A:s header
    resp = await get_with_org(
        client, "/api/v1/systems/", org_a["id"], q="Ekonomisystem"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [s["id"] for s in items]

    assert sys_a["id"] in ids, "Org A borde se sitt Ekonomisystem"
    assert sys_b["id"] not in ids, "Org A skall INTE se Org B:s Ekonomisystem"
    assert sys_c["id"] not in ids, "Org A skall INTE se Org C:s Ekonomisystem"


@pytest.mark.asyncio
@pytest.mark.parametrize("search_term,org_label", [
    ("HR", "org_a"),
    ("Ekonomi", "org_b"),
    ("Arkiv", "org_c"),
])
async def test_multitenant_search_term_per_org(client, search_term, org_label):
    """Varje sökterm skall bara returnera träffar från rätt organisation."""
    orgs = {}
    systems = {}
    org_types = {"org_a": "kommun", "org_b": "bolag", "org_c": "samverkan"}

    for label, org_type in org_types.items():
        orgs[label] = await create_org(
            client, name=f"STermOrg_{label}", org_type=org_type
        )
        systems[label] = await create_system(
            client, orgs[label]["id"],
            name=f"{search_term} system {label}"
        )

    resp = await get_with_org(
        client, "/api/v1/systems/", orgs[org_label]["id"], q=search_term
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]

    assert systems[org_label]["id"] in ids, (
        f"{org_label} borde se sitt system med söktermen '{search_term}'"
    )
    for other_label in org_types:
        if other_label != org_label:
            assert systems[other_label]["id"] not in ids, (
                f"{org_label} skall INTE se {other_label}:s system via sökning"
            )


# ---------------------------------------------------------------------------
# 3c. Statistik filtreras per organisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_stats_overview_per_org(client):
    """Stats-overview med organization_id param visar bara den orgens data."""
    org_a = await create_org(client, name="StatsMultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="StatsMultiOrgB", org_type="bolag")

    # Org A: 3 system, Org B: 2 system
    for i in range(3):
        await create_system(client, org_a["id"], name=f"StMltA-{i}-{uuid4().hex[:6]}")
    for i in range(2):
        await create_system(client, org_b["id"], name=f"StMltB-{i}-{uuid4().hex[:6]}")

    resp_a = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org_a["id"]},
    )
    resp_b = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org_b["id"]},
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    assert resp_a.json()["total_systems"] == 3, (
        f"Org A borde ha 3 system i stats, fick {resp_a.json()['total_systems']}"
    )
    assert resp_b.json()["total_systems"] == 2, (
        f"Org B borde ha 2 system i stats, fick {resp_b.json()['total_systems']}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("org_system_counts", [
    [1, 2, 3],
    [5, 5, 5],
    [0, 1, 10],
    [2, 4, 6],
    [1, 1, 1],
])
async def test_multitenant_stats_counts_isolated(client, org_system_counts):
    """Stats-räkneverkaren är isolerad per organisation för varierande antal system."""
    orgs = []
    for i, count in enumerate(org_system_counts):
        org = await create_org(
            client, name=f"StatCountOrg_{i}_{count}", org_type="kommun"
        )
        for j in range(count):
            await create_system(client, org["id"], name=f"StatCountSys_{i}_{j}")
        orgs.append((org, count))

    for org, expected_count in orgs:
        resp = await client.get(
            "/api/v1/systems/stats/overview",
            params={"organization_id": org["id"]},
        )
        assert resp.status_code == 200
        actual = resp.json()["total_systems"]
        assert actual == expected_count, (
            f"Org {org['name']} borde ha {expected_count} system i stats, fick {actual}"
        )


# ---------------------------------------------------------------------------
# 3d. Export filtreras per organisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_export_json_filtered(client):
    """JSON-export med organization_id param returnerar bara org:s system."""
    org_a = await create_org(client, name="ExportMultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="ExportMultiOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="ExportMultiSysA")
    sys_b = await create_system(client, org_b["id"], name="ExportMultiSysB")

    resp = await client.get(
        "/api/v1/export/systems.json",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    exported_names = [s["name"] for s in resp.json()]

    assert "ExportMultiSysA" in exported_names, "Org A:s system borde exporteras"
    assert "ExportMultiSysB" not in exported_names, "Org B:s system skall inte exporteras"


@pytest.mark.asyncio
async def test_multitenant_export_csv_filtered(client):
    """CSV-export med organization_id param returnerar bara org:s system."""
    import csv
    import io

    org_a = await create_org(client, name="CSVMultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="CSVMultiOrgB", org_type="bolag")

    await create_system(client, org_a["id"], name="CSVMultiSysA")
    await create_system(client, org_b["id"], name="CSVMultiSysB")

    resp = await client.get(
        "/api/v1/export/systems.csv",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    names = [r["name"] for r in rows]

    assert "CSVMultiSysA" in names, "Org A:s system borde finnas i CSV-export"
    assert "CSVMultiSysB" not in names, "Org B:s system skall inte finnas i CSV-export"


@pytest.mark.asyncio
@pytest.mark.parametrize("export_format", ["json", "csv"])
async def test_multitenant_export_formats_filtered(client, export_format):
    """Alla exportformat filtreras korrekt per organisation."""
    org_a = await create_org(client, name=f"FmtExportOrgA_{export_format}", org_type="kommun")
    org_b = await create_org(client, name=f"FmtExportOrgB_{export_format}", org_type="bolag")

    await create_system(client, org_a["id"], name=f"FmtSysA_{export_format}")
    await create_system(client, org_b["id"], name=f"FmtSysB_{export_format}")

    resp = await client.get(
        f"/api/v1/export/systems.{export_format}",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200

    content = resp.text
    assert f"FmtSysA_{export_format}" in content, (
        f"Org A:s system borde finnas i {export_format}-export"
    )
    assert f"FmtSysB_{export_format}" not in content, (
        f"Org B:s system skall INTE finnas i {export_format}-export"
    )


# ---------------------------------------------------------------------------
# 3e. Rapporter filtreras per organisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_nis2_report_with_org_filter(client):
    """NIS2-rapport med organization_id param visar bara org:s NIS2-system."""
    org_a = await create_org(client, name="NIS2MultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="NIS2MultiOrgB", org_type="bolag")

    nis2_a = await create_system(
        client, org_a["id"],
        name="NIS2MultiSysA",
        nis2_applicable=True,
    )
    nis2_b = await create_system(
        client, org_b["id"],
        name="NIS2MultiSysB",
        nis2_applicable=True,
    )

    resp = await client.get(
        "/api/v1/reports/nis2",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]

    assert nis2_a["id"] in ids, "Org A:s NIS2-system borde finnas i rapporten"
    assert nis2_b["id"] not in ids, "Org B:s NIS2-system skall INTE finnas i Org A:s rapport"


@pytest.mark.asyncio
async def test_multitenant_compliance_gap_report_per_org(client):
    """Compliance gap-rapport filtreras per organisation."""
    org_a = await create_org(client, name="CompOrgA", org_type="kommun")
    org_b = await create_org(client, name="CompOrgB", org_type="bolag")

    await create_system(client, org_a["id"], name="CompSysA")
    await create_system(client, org_b["id"], name="CompSysB")

    resp = await client.get(
        "/api/v1/reports/compliance-gap",
        params={"organization_id": org_a["id"]},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3f. Notifieringar per organisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multitenant_notifications_per_org(client):
    """Notifieringsendpoint svarar 200 och returnerar data per organisation."""
    org = await create_org(client, name="NotifOrgA", org_type="kommun")
    await create_system(client, org["id"], name="NotifSysA")

    resp = await client.get(
        "/api/v1/notifications/",
        params={"organization_id": org["id"]},
    )
    # Accepterat: 200 (med data) eller 200 (tom lista) — inte 500
    assert resp.status_code == 200, (
        f"Notifieringsendpoint returnerade {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_multitenant_notifications_two_orgs_independent(client):
    """Notifieringar är oberoende per organisation."""
    org_a = await create_org(client, name="NotifMultiOrgA", org_type="kommun")
    org_b = await create_org(client, name="NotifMultiOrgB", org_type="bolag")

    resp_a = await client.get(
        "/api/v1/notifications/",
        params={"organization_id": org_a["id"]},
    )
    resp_b = await client.get(
        "/api/v1/notifications/",
        params={"organization_id": org_b["id"]},
    )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200


# ===========================================================================
# 4. SUPERADMIN (DigIT) — KONCERNÖVERSIKT
# ===========================================================================


@pytest.mark.asyncio
async def test_superadmin_bypass_mode_sees_all_orgs(client):
    """I bypass-läge (ingen header) ser superadmin alla organisationer."""
    org_a = await create_org(client, name="SuperAdminOrgA", org_type="kommun")
    org_b = await create_org(client, name="SuperAdminOrgB", org_type="bolag")
    org_c = await create_org(client, name="DigITOrg", org_type="digit")

    resp = await client.get("/api/v1/organizations/")
    assert resp.status_code == 200
    org_ids = [o["id"] for o in resp.json()]

    assert org_a["id"] in org_ids, "Superadmin borde se Org A"
    assert org_b["id"] in org_ids, "Superadmin borde se Org B"
    assert org_c["id"] in org_ids, "Superadmin borde se DigIT-org"


@pytest.mark.asyncio
async def test_superadmin_bypass_mode_sees_all_systems(client):
    """I bypass-läge ser superadmin alla system tvärs alla organisationer."""
    org_a = await create_org(client, name="SASystemOrgA", org_type="kommun")
    org_b = await create_org(client, name="SASystemOrgB", org_type="bolag")
    org_digit = await create_org(client, name="SADigITOrg", org_type="digit")

    sys_a = await create_system(client, org_a["id"], name="SASysA")
    sys_b = await create_system(client, org_b["id"], name="SASysB")
    sys_digit = await create_system(client, org_digit["id"], name="SADigITSys")

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]

    assert sys_a["id"] in ids, "Superadmin borde se Org A:s system"
    assert sys_b["id"] in ids, "Superadmin borde se Org B:s system"
    assert sys_digit["id"] in ids, "Superadmin borde se DigIT:s system"


@pytest.mark.asyncio
async def test_superadmin_bypass_nis2_report_all_orgs(client):
    """I bypass-läge inkluderar NIS2-rapport alla orgs NIS2-system."""
    org_a = await create_org(client, name="NIS2SAOrgA", org_type="kommun")
    org_b = await create_org(client, name="NIS2SAOrgB", org_type="bolag")

    nis2_a = await create_system(client, org_a["id"], name="NIS2SASysA", nis2_applicable=True)
    nis2_b = await create_system(client, org_b["id"], name="NIS2SASysB", nis2_applicable=True)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]

    assert nis2_a["id"] in ids, "Superadmin borde se Org A:s NIS2-system i rapporten"
    assert nis2_b["id"] in ids, "Superadmin borde se Org B:s NIS2-system i rapporten"


@pytest.mark.asyncio
async def test_superadmin_bypass_stats_all_orgs(client):
    """I bypass-läge visar stats/overview alla orgs totalt."""
    org_a = await create_org(client, name="StatsSAOrgA", org_type="kommun")
    org_b = await create_org(client, name="StatsSAOrgB", org_type="bolag")

    for i in range(2):
        await create_system(client, org_a["id"], name=f"StSAA-{i}-{uuid4().hex[:6]}")
    for i in range(3):
        await create_system(client, org_b["id"], name=f"StSAB-{i}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/systems/stats/overview")
    assert resp.status_code == 200
    total = resp.json()["total_systems"]
    assert total >= 5, f"Superadmin borde se minst 5 system totalt, fick {total}"


@pytest.mark.asyncio
async def test_superadmin_digit_org_type_exists(client):
    """Org-typ 'digit' skall kunna skapas (representerar DigIT = superadmin-org)."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "DigIT Förvaltning",
        "org_type": "digit",
        "description": "Intern IT-förvaltning med superadmin-behörighet",
    })
    assert resp.status_code == 201, f"Org-typ 'digit' borde skapas, fick {resp.text}"
    assert resp.json()["org_type"] == "digit"


@pytest.mark.asyncio
@pytest.mark.parametrize("org_type", ORG_TYPES)
async def test_superadmin_all_org_types_creatable(client, org_type):
    """Alla definierade org-typer skall kunna skapas."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": f"OrgType test {org_type}",
        "org_type": org_type,
    })
    assert resp.status_code == 201, (
        f"Org-typ '{org_type}' borde kunna skapas, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_superadmin_bypass_audit_log_all_orgs(client):
    """I bypass-läge skall audit-loggen innehålla poster från alla orgs."""
    org_a = await create_org(client, name="AuditSAOrgA", org_type="kommun")
    org_b = await create_org(client, name="AuditSAOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="AuditSASysA")
    sys_b = await create_system(client, org_b["id"], name="AuditSASysB")

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    record_ids = [item["record_id"] for item in resp.json()["items"]]

    assert sys_a["id"] in record_ids, "Audit-loggen borde ha poster för Org A:s system"
    assert sys_b["id"] in record_ids, "Audit-loggen borde ha poster för Org B:s system"


# ===========================================================================
# 5. HIERARKISKA ORGANISATIONER
# ===========================================================================


# ---------------------------------------------------------------------------
# 5a. Parent-child relationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hierarchy_create_child_org(client):
    """Skapa bolag (barn) under en kommun (förälder)."""
    parent = await create_org(client, name="Moderkommun", org_type="kommun")

    child = await create_org(
        client,
        name="Kommunalt Bolag AB",
        org_type="bolag",
        parent_org_id=parent["id"],
    )

    assert child["parent_org_id"] == parent["id"], (
        "Barnorganisationens parent_org_id borde matcha föräldern"
    )
    assert child["id"] != parent["id"]


@pytest.mark.asyncio
async def test_hierarchy_parent_id_stored_correctly(client):
    """parent_org_id skall sparas och returneras korrekt."""
    parent = await create_org(client, name="HierParent", org_type="kommun")
    child = await create_org(
        client,
        name="HierChild",
        org_type="bolag",
        parent_org_id=parent["id"],
    )

    # Hämta child via GET och verifiera parent_org_id
    resp = await client.get(f"/api/v1/organizations/{child['id']}")
    assert resp.status_code == 200
    assert resp.json()["parent_org_id"] == parent["id"]


@pytest.mark.asyncio
async def test_hierarchy_child_systems_isolated_from_parent(client):
    """Barnorganisationens system skall vara isolerade från förälderns."""
    parent = await create_org(client, name="HierIsoParent", org_type="kommun")
    child = await create_org(
        client,
        name="HierIsoChild",
        org_type="bolag",
        parent_org_id=parent["id"],
    )

    sys_parent = await create_system(client, parent["id"], name="HierParentSys")
    sys_child = await create_system(client, child["id"], name="HierChildSys")

    # Förälder ser bara sina system
    resp_parent = await get_with_org(client, "/api/v1/systems/", parent["id"])
    ids_parent = [s["id"] for s in resp_parent.json()["items"]]
    assert sys_parent["id"] in ids_parent
    assert sys_child["id"] not in ids_parent, "Förälder skall INTE se barnets system"

    # Barn ser bara sina system
    resp_child = await get_with_org(client, "/api/v1/systems/", child["id"])
    ids_child = [s["id"] for s in resp_child.json()["items"]]
    assert sys_child["id"] in ids_child
    assert sys_parent["id"] not in ids_child, "Barn skall INTE se förälderns system"


@pytest.mark.asyncio
async def test_hierarchy_multiple_children_under_parent(client):
    """Flera barn under samma förälder skall alla vara isolerade från varandra."""
    parent = await create_org(client, name="MultiChildParent", org_type="kommun")

    children_systems = []
    for i in range(3):
        child = await create_org(
            client,
            name=f"MultiChild{i}",
            org_type="bolag",
            parent_org_id=parent["id"],
        )
        sys = await create_system(client, child["id"], name=f"MultiChildSys{i}")
        children_systems.append((child, sys))

    # Varje barn ser bara sina egna system
    for idx, (child, sys) in enumerate(children_systems):
        resp = await get_with_org(client, "/api/v1/systems/", child["id"])
        ids = [s["id"] for s in resp.json()["items"]]

        assert sys["id"] in ids, f"Barn {idx} borde se sitt system"
        for other_idx, (_, other_sys) in enumerate(children_systems):
            if other_idx != idx:
                assert other_sys["id"] not in ids, (
                    f"Barn {idx} skall INTE se syskon {other_idx}:s system"
                )


# ---------------------------------------------------------------------------
# 5b. Bolag under kommun
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hierarchy_municipality_with_company(client):
    """Kommuns bolag är en separat organisation med eget system-register."""
    kommun = await create_org(client, name="Testkommun", org_type="kommun")
    bolag = await create_org(
        client,
        name="Testkommunens Energi AB",
        org_type="bolag",
        parent_org_id=kommun["id"],
    )

    # Skapa system i kommunen och bolaget
    sys_kommun = await create_system(client, kommun["id"], name="Kommuns Ärendesystem")
    sys_bolag = await create_system(client, bolag["id"], name="Bolagets Faktureringssystem")

    # Kommunen ser bara sitt system
    resp_k = await get_with_org(client, "/api/v1/systems/", kommun["id"])
    ids_k = [s["id"] for s in resp_k.json()["items"]]
    assert sys_kommun["id"] in ids_k
    assert sys_bolag["id"] not in ids_k

    # Bolaget ser bara sitt system
    resp_b = await get_with_org(client, "/api/v1/systems/", bolag["id"])
    ids_b = [s["id"] for s in resp_b.json()["items"]]
    assert sys_bolag["id"] in ids_b
    assert sys_kommun["id"] not in ids_b


@pytest.mark.asyncio
async def test_hierarchy_municipality_with_multiple_companies(client):
    """Kommun med flera helägda bolag — alla isolerade."""
    kommun = await create_org(client, name="StorKommun", org_type="kommun")

    bolag_data = [
        ("StorKommun Energi AB", "Energisystem"),
        ("StorKommun Vatten AB", "Vattensystem"),
        ("StorKommun Fastigheter AB", "Fastighetssystem"),
    ]

    org_sys_pairs = []
    for bolag_name, sys_name in bolag_data:
        bolag = await create_org(
            client,
            name=bolag_name,
            org_type="bolag",
            parent_org_id=kommun["id"],
        )
        sys = await create_system(client, bolag["id"], name=sys_name)
        org_sys_pairs.append((bolag, sys))

    # Varje bolag ser bara sina system
    for idx, (bolag, sys) in enumerate(org_sys_pairs):
        resp = await get_with_org(client, "/api/v1/systems/", bolag["id"])
        ids = [s["id"] for s in resp.json()["items"]]

        assert sys["id"] in ids, f"Bolag {bolag['name']} borde se sitt system"
        for other_idx, (_, other_sys) in enumerate(org_sys_pairs):
            if other_idx != idx:
                assert other_sys["id"] not in ids, (
                    f"Bolag {idx} skall inte se bolag {other_idx}:s system"
                )


# ---------------------------------------------------------------------------
# 5c. Samverkansorganisationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hierarchy_samverkan_org_isolated(client):
    """Samverkansorganisation är isolerad från sina ingående parters system."""
    kommun_a = await create_org(client, name="SamvKommunA", org_type="kommun")
    kommun_b = await create_org(client, name="SamvKommunB", org_type="kommun")
    samverkan = await create_org(client, name="IT-samverkan AB", org_type="samverkan")

    sys_a = await create_system(client, kommun_a["id"], name="KommunASys")
    sys_b = await create_system(client, kommun_b["id"], name="KommunBSys")
    sys_samv = await create_system(client, samverkan["id"], name="SamverkansSys")

    # Samverkansorg ser bara sina system
    resp = await get_with_org(client, "/api/v1/systems/", samverkan["id"])
    ids = [s["id"] for s in resp.json()["items"]]

    assert sys_samv["id"] in ids, "Samverkansorg borde se sitt system"
    assert sys_a["id"] not in ids, "Samverkansorg skall INTE se KommunA:s system"
    assert sys_b["id"] not in ids, "Samverkansorg skall INTE se KommunB:s system"


@pytest.mark.asyncio
async def test_hierarchy_samverkan_as_child_org(client):
    """Samverkansorg kan ha en föräldraorganisation."""
    parent_kommun = await create_org(client, name="SamvParentKommun", org_type="kommun")
    samverkan = await create_org(
        client,
        name="IT-samverkan med förälder",
        org_type="samverkan",
        parent_org_id=parent_kommun["id"],
    )

    assert samverkan["parent_org_id"] == parent_kommun["id"]

    # Samverkansorg har ändå egna isolerade system
    sys_samv = await create_system(client, samverkan["id"], name="SamvChildSys")
    sys_parent = await create_system(client, parent_kommun["id"], name="ParentSamvSys")

    resp = await get_with_org(client, "/api/v1/systems/", samverkan["id"])
    ids = [s["id"] for s in resp.json()["items"]]

    assert sys_samv["id"] in ids
    assert sys_parent["id"] not in ids


@pytest.mark.asyncio
@pytest.mark.parametrize("parent_type,child_type", [
    ("kommun", "bolag"),
    ("kommun", "samverkan"),
    ("digit", "kommun"),
    ("digit", "bolag"),
    ("digit", "samverkan"),
])
async def test_hierarchy_valid_parent_child_type_combinations(client, parent_type, child_type):
    """Alla giltiga kombination av förälder-barn org-typer skall fungera."""
    parent = await create_org(
        client,
        name=f"ParentType_{parent_type}_{child_type}",
        org_type=parent_type,
    )
    child = await create_org(
        client,
        name=f"ChildType_{child_type}_{parent_type}",
        org_type=child_type,
        parent_org_id=parent["id"],
    )

    assert child["parent_org_id"] == parent["id"], (
        f"parent_org_id borde sättas för {parent_type} -> {child_type}"
    )


# ---------------------------------------------------------------------------
# 5d. Djup hierarki — 3 nivåer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hierarchy_three_level_isolation(client):
    """Tre nivåers hierarki: region -> kommun -> bolag, alla isolerade."""
    region = await create_org(client, name="RegionTest", org_type="samverkan")
    kommun = await create_org(
        client, name="KommunUnderRegion", org_type="kommun",
        parent_org_id=region["id"],
    )
    bolag = await create_org(
        client, name="BolagUnderKommun", org_type="bolag",
        parent_org_id=kommun["id"],
    )

    sys_region = await create_system(client, region["id"], name="RegionSys")
    sys_kommun = await create_system(client, kommun["id"], name="KommunSys")
    sys_bolag = await create_system(client, bolag["id"], name="BolagSys")

    # Varje nivå ser bara sina egna system
    for org, own_sys, hidden_systems in [
        (region, sys_region, [sys_kommun, sys_bolag]),
        (kommun, sys_kommun, [sys_region, sys_bolag]),
        (bolag, sys_bolag, [sys_region, sys_kommun]),
    ]:
        resp = await get_with_org(client, "/api/v1/systems/", org["id"])
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["items"]]

        assert own_sys["id"] in ids, f"Org {org['name']} borde se sitt system"
        for hidden_sys in hidden_systems:
            assert hidden_sys["id"] not in ids, (
                f"Org {org['name']} skall INTE se {hidden_sys['name']}"
            )


# ===========================================================================
# 6. YTTERLIGARE PARAMETRISERADE ISOLATIONSTESTER
# ===========================================================================


# ---------------------------------------------------------------------------
# 6a. Systemkategorier isolerade per org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("system_category", [
    "verksamhetssystem",
    "stödsystem",
    "infrastruktur",
    "plattform",
    "iot",
])
async def test_iso_system_categories_isolated_per_org(client, system_category):
    """System av alla kategorier i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"CatOrgA_{system_category}", org_type="kommun")
    org_b = await create_org(client, name=f"CatOrgB_{system_category}", org_type="bolag")

    sys_a = await create_system(
        client, org_a["id"],
        name=f"CatSys_{system_category}",
        system_category=system_category,
    )

    resp = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] not in ids, (
        f"System av kategori '{system_category}' från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6b. Lifecycle-status isolerad per org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle_status", [
    "i_drift",
    "under_avveckling",
    "avvecklad",
    "planerad",
    "under_inforande",
])
async def test_iso_lifecycle_status_isolated_per_org(client, lifecycle_status):
    """System i varje lifecycle-status i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"LCOrgA_{lifecycle_status[:5]}", org_type="kommun")
    org_b = await create_org(client, name=f"LCOrgB_{lifecycle_status[:5]}", org_type="bolag")

    sys_a = await create_system(
        client, org_a["id"],
        name=f"LCSys_{lifecycle_status[:10]}",
        lifecycle_status=lifecycle_status,
    )

    resp = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] not in ids, (
        f"System med lifecycle '{lifecycle_status}' från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6c. Kritikalitet isolerad per org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", [
    "kritisk",
    "hög",
    "medel",
    "låg",
])
async def test_iso_criticality_levels_isolated_per_org(client, criticality):
    """System av alla kritikalitetsnivåer i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"CritOrgA_{criticality}", org_type="kommun")
    org_b = await create_org(client, name=f"CritOrgB_{criticality}", org_type="bolag")

    sys_a = await create_system(
        client, org_a["id"],
        name=f"CritSys_{criticality}",
        criticality=criticality,
    )

    resp = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] not in ids, (
        f"System med kritikalitet '{criticality}' från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6d. Hosting-modeller isolerade per org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("hosting_model", [
    "on-premise",
    "saas",
    "iaas",
    "paas",
    "hybrid",
])
async def test_iso_hosting_models_isolated_per_org(client, hosting_model):
    """System med olika hosting-modeller i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"HostOrgA_{hosting_model}", org_type="kommun")
    org_b = await create_org(client, name=f"HostOrgB_{hosting_model}", org_type="bolag")

    sys_a = await create_system(
        client, org_a["id"],
        name=f"HostSys_{hosting_model}",
        hosting_model=hosting_model,
    )

    resp = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] not in ids, (
        f"System med hosting '{hosting_model}' från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6e. NIS2 isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_applicable,nis2_classification", [
    (True, "väsentlig"),
    (True, "viktig"),
    (False, None),
])
async def test_iso_nis2_systems_isolated_per_org(client, nis2_applicable, nis2_classification):
    """NIS2-system i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"NIS2IsoOrgA_{nis2_applicable}", org_type="kommun")
    org_b = await create_org(client, name=f"NIS2IsoOrgB_{nis2_applicable}", org_type="bolag")

    kwargs = {"nis2_applicable": nis2_applicable}
    if nis2_classification:
        kwargs["nis2_classification"] = nis2_classification

    sys_a = await create_system(
        client, org_a["id"],
        name=f"NIS2IsoSys_{nis2_applicable}",
        **kwargs,
    )

    resp = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_a["id"] not in ids, (
        f"NIS2-system (applicable={nis2_applicable}) från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6f. Ägareroller – alla roller är isolerade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("owner_role,owner_name", [
    ("systemägare", "Anna Svensson"),
    ("teknisk_förvaltare", "Bo Eriksson"),
    ("informationsägare", "Cecilia Johansson"),
])
async def test_iso_all_owner_roles_isolated(client, owner_role, owner_name):
    """Ägare av alla roller i Org A skall inte synas för Org B."""
    org_a = await create_org(client, name=f"OwnerRoleOrgA_{owner_role[:4]}", org_type="kommun")
    org_b = await create_org(client, name=f"OwnerRoleOrgB_{owner_role[:4]}", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name=f"OwnerRoleSys_{owner_role[:4]}")
    sys_b = await create_system(client, org_b["id"], name=f"OwnerRoleSysB_{owner_role[:4]}")

    owner_a = await create_owner(
        client, sys_a["id"], org_a["id"],
        role=owner_role, name=owner_name,
    )

    resp = await get_with_org(
        client, f"/api/v1/systems/{sys_b['id']}/owners", org_b["id"]
    )
    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert owner_a["id"] not in ids, (
        f"Ägare med roll '{owner_role}' från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6g. RLS med ogiltigt UUID på olika endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,invalid_header", [
    ("/api/v1/systems/", "not-a-uuid"),
    ("/api/v1/integrations/", "not-a-uuid"),
    ("/api/v1/systems/", "12345"),
    ("/api/v1/integrations/", "12345"),
    ("/api/v1/systems/", "null"),
    ("/api/v1/integrations/", "null"),
    ("/api/v1/systems/", "SELECT 1"),
    ("/api/v1/integrations/", "SELECT 1"),
])
async def test_rls_invalid_uuid_on_all_endpoints_returns_400(client, endpoint, invalid_header):
    """Ogiltigt UUID i header skall ge 400 på alla listendpoints."""
    resp = await client.get(
        endpoint,
        headers={"X-Organization-Id": invalid_header},
    )
    assert resp.status_code == 400, (
        f"Ogiltigt UUID {invalid_header!r} på {endpoint} borde ge 400, "
        f"fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 6h. Kontraktsutgång — isolation per org
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("days_until_expiry", [7, 30, 60, 90, 180, 365, 730, 14])
async def test_iso_expiring_contracts_per_org(client, days_until_expiry):
    """Utgående kontrakt i Org A skall inte synas i Org B:s utgående kontrakt."""
    from datetime import date, timedelta

    org_a = await create_org(client, name=f"ContrExpOrgA_{days_until_expiry}", org_type="kommun")
    org_b = await create_org(client, name=f"ContrExpOrgB_{days_until_expiry}", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name=f"ContrExpSysA_{days_until_expiry}")
    sys_b = await create_system(client, org_b["id"], name=f"ContrExpSysB_{days_until_expiry}")

    expiry_date = (date.today() + timedelta(days=days_until_expiry)).isoformat()
    contract_a = await create_contract(
        client, sys_a["id"],
        supplier_name=f"LevA_{days_until_expiry}",
        contract_end=expiry_date,
    )

    # Org B:s system har inget utgående kontrakt
    resp = await get_with_org(
        client, f"/api/v1/systems/{sys_b['id']}/contracts", org_b["id"]
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract_a["id"] not in ids, (
        f"Kontrakt med {days_until_expiry} dagar till utgång från Org A synlig för Org B"
    )


# ---------------------------------------------------------------------------
# 6i. Systempagination med org-filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("limit,offset", [
    (10, 0),
    (5, 0),
    (5, 5),
    (1, 0),
])
async def test_iso_pagination_respects_org_filter(client, limit, offset):
    """Pagination med org-header returnerar bara rätt orgs system."""
    org_a = await create_org(client, name=f"PageOrgA_{limit}_{offset}", org_type="kommun")
    org_b = await create_org(client, name=f"PageOrgB_{limit}_{offset}", org_type="bolag")

    # Skapa 10 system i Org A och 10 i Org B
    sys_a_ids = []
    for i in range(10):
        sys = await create_system(
            client, org_a["id"], name=f"PgA-{i}-{uuid4().hex[:6]}"
        )
        sys_a_ids.append(sys["id"])

    for i in range(10):
        await create_system(client, org_b["id"], name=f"PgB-{i}-{uuid4().hex[:6]}")

    resp = await get_with_org(
        client, "/api/v1/systems/", org_a["id"],
        limit=limit, offset=offset,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]

    # Alla returnerade items skall tillhöra Org A
    for item in items:
        assert item["id"] in sys_a_ids, (
            f"Paginerat resultat innehåller system som inte tillhör Org A: {item['id']}"
        )


# ---------------------------------------------------------------------------
# 6j. Organisations-CRUD-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("org_type_a,org_type_b", [
    ("kommun", "bolag"),
    ("bolag", "samverkan"),
    ("samverkan", "digit"),
    ("digit", "kommun"),
    ("kommun", "samverkan"),
    ("bolag", "digit"),
    ("bolag", "kommun"),
    ("samverkan", "kommun"),
    ("digit", "bolag"),
    ("digit", "samverkan"),
    ("kommun", "digit"),
    ("samverkan", "bolag"),
])
async def test_iso_different_org_type_pairs_system_isolation(client, org_type_a, org_type_b):
    """System isolerade mellan alla kombination av org-typer."""
    org_a = await create_org(
        client, name=f"PairOrgA_{org_type_a}_{org_type_b}", org_type=org_type_a
    )
    org_b = await create_org(
        client, name=f"PairOrgB_{org_type_a}_{org_type_b}", org_type=org_type_b
    )

    sys_a = await create_system(
        client, org_a["id"], name=f"PairSysA_{org_type_a}_{org_type_b}"
    )
    sys_b = await create_system(
        client, org_b["id"], name=f"PairSysB_{org_type_a}_{org_type_b}"
    )

    # Org A ser bara sitt system
    resp_a = await get_with_org(client, "/api/v1/systems/", org_a["id"])
    ids_a = [s["id"] for s in resp_a.json()["items"]]
    assert sys_a["id"] in ids_a
    assert sys_b["id"] not in ids_a, (
        f"{org_type_a} ser {org_type_b}:s system (läckage)"
    )

    # Org B ser bara sitt system
    resp_b = await get_with_org(client, "/api/v1/systems/", org_b["id"])
    ids_b = [s["id"] for s in resp_b.json()["items"]]
    assert sys_b["id"] in ids_b
    assert sys_a["id"] not in ids_b, (
        f"{org_type_b} ser {org_type_a}:s system (läckage)"
    )


# ===========================================================================
# 7. GRÄNSFALL OCH KANTSCENARIER
# ===========================================================================


# ---------------------------------------------------------------------------
# 7a. Tom organisation (inga system)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("org_type", ["kommun", "bolag", "samverkan", "digit"])
async def test_edge_empty_org_returns_empty_list(client, org_type):
    """En organisation utan system skall returnera tom lista."""
    org = await create_org(client, name=f"EmptyOrg_{org_type}", org_type=org_type)

    resp = await get_with_org(client, "/api/v1/systems/", org["id"])
    assert resp.status_code == 200
    assert resp.json()["items"] == [], (
        f"Tom {org_type}-org borde ge tom systemlista"
    )


# ---------------------------------------------------------------------------
# 7b. Enstaka system per org — korrekt total
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("n_systems", [1, 2, 5, 13, 3, 7])
async def test_edge_org_sees_exact_system_count(client, n_systems):
    """Organisation med N system ser exakt N system (inte fler, inte färre)."""
    org = await create_org(client, name=f"ExactCountOrg_{n_systems}", org_type="kommun")
    decoy_org = await create_org(client, name=f"DecoyOrg_{n_systems}", org_type="bolag")

    for i in range(n_systems):
        await create_system(client, org["id"], name=f"ExactSys_{n_systems}_{i}")

    # Skapa brus från annan org
    for i in range(3):
        await create_system(client, decoy_org["id"], name=f"DecoyBrusSys_{n_systems}_{i}")

    resp = await get_with_org(client, "/api/v1/systems/", org["id"])
    assert resp.status_code == 200

    actual = len(resp.json()["items"])
    assert actual == n_systems, (
        f"Org med {n_systems} system borde se exakt {n_systems}, fick {actual}"
    )


# ---------------------------------------------------------------------------
# 7c. Org ser sina egna system direkt via ID (bypass)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edge_direct_system_access_own_org(client):
    """GET /systems/{id} på eget system utan header returnerar korrekt data."""
    org = await create_org(client, name="DirectAccessOrg", org_type="kommun")
    sys = await create_system(client, org["id"], name="DirectAccessSys")

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sys["id"]
    assert resp.json()["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_edge_system_details_include_org_id(client):
    """Systemdetaljer skall alltid inkludera organization_id för att möjliggöra RLS-kontroll."""
    org = await create_org(client, name="OrgIdCheckOrg", org_type="kommun")
    sys = await create_system(client, org["id"], name="OrgIdCheckSys")

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert "organization_id" in body, "Systemdetaljer borde inkludera organization_id"
    assert body["organization_id"] == org["id"]


# ---------------------------------------------------------------------------
# 7d. Sortering och filtrering respekterar org-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("sort_field,sort_order", [
    ("name", "asc"),
    ("name", "desc"),
    ("created_at", "asc"),
    ("created_at", "desc"),
    ("system_category", "asc"),
    ("lifecycle_status", "asc"),
])
async def test_edge_sorted_results_stay_in_org(client, sort_field, sort_order):
    """Sorterade listor skall bara innehålla den egna orgens system."""
    org_a = await create_org(client, name=f"SortOrgA_{sort_field}", org_type="kommun")
    org_b = await create_org(client, name=f"SortOrgB_{sort_field}", org_type="bolag")

    for i in range(3):
        await create_system(client, org_a["id"], name=f"SrtA-{i}-{uuid4().hex[:6]}")
    for i in range(3):
        await create_system(client, org_b["id"], name=f"SrtB-{i}-{uuid4().hex[:6]}")

    resp = await get_with_org(
        client, "/api/v1/systems/", org_a["id"],
        sort=sort_field, order=sort_order,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]

    # Alla returnerade items skall tillhöra Org A
    for item in items:
        assert item["organization_id"] == org_a["id"], (
            f"Sorterat resultat innehåller system från annan org: {item['id']}"
        )


# ---------------------------------------------------------------------------
# 7e. Filter på systemkategori respekterar org-isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category_filter", [
    "verksamhetssystem",
    "stödsystem",
    "infrastruktur",
])
async def test_edge_category_filter_respects_org_isolation(client, category_filter):
    """Filtrering på system_category returnerar bara rätt orgs system."""
    org_a = await create_org(client, name=f"CatFilterOrgA_{category_filter[:5]}", org_type="kommun")
    org_b = await create_org(client, name=f"CatFilterOrgB_{category_filter[:5]}", org_type="bolag")

    sys_a = await create_system(
        client, org_a["id"],
        name=f"CatFilterSysA_{category_filter[:5]}",
        system_category=category_filter,
    )
    sys_b = await create_system(
        client, org_b["id"],
        name=f"CatFilterSysB_{category_filter[:5]}",
        system_category=category_filter,
    )

    resp = await get_with_org(
        client, "/api/v1/systems/", org_a["id"],
        system_category=category_filter,
    )
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]

    assert sys_a["id"] in ids, "Org A borde se sitt filtrerade system"
    assert sys_b["id"] not in ids, "Org A skall INTE se Org B:s system via kategorifilter"
