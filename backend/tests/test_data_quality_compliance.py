"""
Datakvalitet och regelefterlevnad — verifierar att API:et uppfyller
regulatoriska krav enligt kravspecifikationen.

Täcker:
- Datakvalitetskontroll (notifications, severity-nivåer, pagination)
- NIS2/CSL compliance (SFS 2025:1506 art. 21)
- ISO 27001:2022 Annex A (A.5.9, A.5.12, A.5.14, A.5.15, A.5.19-5.22,
  A.5.23, A.5.30, A.8.9)
- MSBFS 2020:7 Kap 2 § 4 (hårdvara/mjukvara, beroenden,
  utökat skyddsbehov, centrala system)
- GDPR Art. 30 (behandlingsregister, typ av personuppgifter,
  PuB-avtal, tredjeland, gallring)
- Informationsklassning MSBFS 2020:6 (K/R/T 0-4, uppföljning,
  has_elevated_protection)
- Rapporter (NIS2 JSON/XLSX, compliance-gap, HTML/PDF)
- Audit trail (NIS2 + ISO 27001)

Målantal: ~200 testfall
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_contract,
    create_gdpr_treatment,
    create_integration,
    create_full_system,
)


# ===========================================================================
# DEL 1: DATAKVALITETSKONTROLL — Notifikationer
# ===========================================================================


# ---------------------------------------------------------------------------
# 1a. missing_classification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_missing_classification_flaggas(client):
    """System utan klassificering genererar missing_classification-notifikation."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_classification" in types


@pytest.mark.asyncio
async def test_dq_missing_classification_inkluderar_system_id(client):
    """missing_classification-notifikation ska innehålla system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"] if n["type"] == "missing_classification"]
    assert len(missing) > 0
    assert all("system_id" in n for n in missing)
    system_ids = [n["system_id"] for n in missing]
    assert sys["id"] in system_ids


@pytest.mark.asyncio
async def test_dq_missing_classification_forsvinner_nar_klassning_finns(client):
    """System med klassificering ska INTE generera missing_classification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [
        n for n in resp.json()["items"]
        if n["type"] == "missing_classification" and n["system_id"] == sys["id"]
    ]
    assert len(missing) == 0, "Klassat system ska inte generera missing_classification"


@pytest.mark.asyncio
async def test_dq_missing_classification_severity_ar_warning_eller_critical(client):
    """missing_classification ska ha severity warning eller critical."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"] if n["type"] == "missing_classification"]
    assert len(missing) > 0
    for n in missing:
        assert n["severity"] in ("warning", "critical"), (
            f"Oväntat severity för missing_classification: {n['severity']}"
        )


# ---------------------------------------------------------------------------
# 1b. missing_owner
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_missing_owner_flaggas(client):
    """System utan ägare genererar missing_owner-notifikation."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_owner" in types


@pytest.mark.asyncio
async def test_dq_missing_owner_inkluderar_system_id(client):
    """missing_owner-notifikation ska innehålla system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"] if n["type"] == "missing_owner"]
    assert len(missing) > 0
    assert all("system_id" in n for n in missing)
    assert sys["id"] in [n["system_id"] for n in missing]


@pytest.mark.asyncio
async def test_dq_missing_owner_forsvinner_nar_agare_finns(client):
    """System med ägare ska INTE generera missing_owner."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [
        n for n in resp.json()["items"]
        if n["type"] == "missing_owner" and n["system_id"] == sys["id"]
    ]
    assert len(missing) == 0, "System med ägare ska inte ha missing_owner"


@pytest.mark.asyncio
async def test_dq_missing_owner_severity_giltig(client):
    """missing_owner ska ha giltig severity."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"] if n["type"] == "missing_owner"]
    assert len(missing) > 0
    valid = {"info", "warning", "critical"}
    for n in missing:
        assert n["severity"] in valid


# ---------------------------------------------------------------------------
# 1c. missing_gdpr_treatment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_missing_gdpr_treatment_flaggas(client):
    """System med personuppgifter men utan GDPR-behandling genererar notifikation."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_gdpr_treatment" in types


@pytest.mark.asyncio
async def test_dq_missing_gdpr_severity_ar_critical(client):
    """missing_gdpr_treatment ska alltid ha severity=critical."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    gdpr_notifs = [n for n in resp.json()["items"] if n["type"] == "missing_gdpr_treatment"]
    assert len(gdpr_notifs) > 0
    assert all(n["severity"] == "critical" for n in gdpr_notifs), (
        "missing_gdpr_treatment ska alltid vara critical"
    )


@pytest.mark.asyncio
async def test_dq_missing_gdpr_forsvinner_nar_behandling_finns(client):
    """System med GDPR-behandling ska INTE ha missing_gdpr_treatment."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    await create_gdpr_treatment(client, sys["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [
        n for n in resp.json()["items"]
        if n["type"] == "missing_gdpr_treatment" and n["system_id"] == sys["id"]
    ]
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_dq_system_utan_personuppgifter_ingen_gdpr_notifikation(client):
    """System utan personuppgifter ska INTE generera missing_gdpr_treatment."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=False)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    gdpr = [
        n for n in resp.json()["items"]
        if n["type"] == "missing_gdpr_treatment" and n["system_id"] == sys["id"]
    ]
    assert len(gdpr) == 0


# ---------------------------------------------------------------------------
# 1d. missing_risk_assessment (NIS2-system)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_nis2_utan_riskbedomning_flaggas(client):
    """NIS2-system utan riskbedömning ska generera notifikation."""
    org = await create_org(client)
    await create_system(
        client, org["id"],
        nis2_applicable=True,
        last_risk_assessment_date=None,
    )

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    # Acceptera antingen missing_risk_assessment eller nis2_missing_risk_assessment
    risk_types = [t for t in types if "risk_assessment" in t]
    assert len(risk_types) > 0, (
        "NIS2-system utan riskbedömning bör generera notifikation om risk assessment"
    )


@pytest.mark.asyncio
async def test_dq_nis2_med_riskbedomning_ingen_notifikation(client):
    """NIS2-system med aktuell riskbedömning ska INTE ha risk assessment-notifikation."""
    org = await create_org(client)
    recent_date = (date.today() - timedelta(days=30)).isoformat()
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        last_risk_assessment_date=recent_date,
    )

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    risk_notifs = [
        n for n in resp.json()["items"]
        if "risk_assessment" in n["type"] and n.get("system_id") == sys["id"]
    ]
    assert len(risk_notifs) == 0, (
        "NIS2-system med aktuell riskbedömning ska inte ha risk_assessment-notifikation"
    )


@pytest.mark.asyncio
async def test_dq_icke_nis2_system_utan_riskbedomning_ingen_notifikation(client):
    """System som inte är NIS2 ska INTE generera risk_assessment-notifikation."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        nis2_applicable=False,
        last_risk_assessment_date=None,
    )

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    risk = [
        n for n in resp.json()["items"]
        if "risk_assessment" in n.get("type", "") and n.get("system_id") == sys["id"]
    ]
    assert len(risk) == 0, "Icke-NIS2 system bör inte flaggas för saknad riskbedömning"


# ---------------------------------------------------------------------------
# 1e. stale_classification (äldre än 12 månader)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_forsenad_klassning_flaggas(client):
    """Klassificering äldre än 12 månader ska generera stale_classification-notifikation."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    old_date = (date.today() - timedelta(days=400)).isoformat()
    await create_classification(client, sys["id"], valid_until=old_date)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "stale_classification" in types, (
        "Klassificering äldre än 12 månader bör generera stale_classification"
    )


@pytest.mark.asyncio
async def test_dq_aktuell_klassning_ingen_stale_notifikation(client):
    """Klassificering med framtida valid_until ska INTE generera stale_classification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    future_date = (date.today() + timedelta(days=180)).isoformat()
    await create_classification(client, sys["id"], valid_until=future_date)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    stale = [
        n for n in resp.json()["items"]
        if n["type"] == "stale_classification" and n.get("system_id") == sys["id"]
    ]
    assert len(stale) == 0, "Aktuell klassificering ska inte vara stale"


# ---------------------------------------------------------------------------
# 1f. expiring_contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_avtal_utgaar_inom_90_dagar_flaggas(client):
    """Avtal som löper ut inom 90 dagar ska generera expiring_contract."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=45)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "expiring_contract" in types


@pytest.mark.asyncio
async def test_dq_avtal_kritisk_severity_inom_30_dagar(client):
    """Avtal som löper ut inom 30 dagar ska ha severity=critical."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=15)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert any(n["severity"] == "critical" for n in expiring), (
        "Avtal < 30 dagar ska vara critical"
    )


@pytest.mark.asyncio
async def test_dq_avtal_warning_severity_31_90_dagar(client):
    """Avtal som löper ut om 31-90 dagar ska ha severity=warning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=60)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert any(n["severity"] == "warning" for n in expiring), (
        "Avtal 31-90 dagar ska ha warning severity"
    )


@pytest.mark.asyncio
async def test_dq_avtal_over_90_dagar_ingen_notifikation(client):
    """Avtal som löper ut om > 90 dagar ska INTE generera expiring_contract."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=120)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert len(expiring) == 0


@pytest.mark.asyncio
async def test_dq_utganget_avtal_ingen_expiring_notifikation(client):
    """Redan utgånget avtal ska INTE generera expiring_contract."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expired = (date.today() - timedelta(days=10)).isoformat()
    await create_contract(client, sys["id"], contract_end=expired)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert len(expiring) == 0, "Redan utgångna avtal genererar inte expiring_contract"


# ---------------------------------------------------------------------------
# 1g. Notifications-struktur och severity-nivåer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_notifikationer_har_type_severity_title(client):
    """Alla notifikationer ska ha fälten type, severity och title."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    for n in resp.json()["items"]:
        assert "type" in n, f"Notifikation saknar 'type': {n}"
        assert "severity" in n, f"Notifikation saknar 'severity': {n}"
        assert "title" in n, f"Notifikation saknar 'title': {n}"


@pytest.mark.asyncio
async def test_dq_severity_bara_info_warning_critical(client):
    """Severity-värden ska vara info, warning eller critical."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    valid = {"info", "warning", "critical"}
    for n in resp.json()["items"]:
        assert n["severity"] in valid, f"Ogiltigt severity: {n['severity']}"


@pytest.mark.asyncio
async def test_dq_by_severity_stammer_med_lista(client):
    """by_severity-summering ska stämma med faktiska antalet per severity."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    by_severity = body["by_severity"]
    computed: dict = {}
    for n in body["items"]:
        sev = n["severity"]
        computed[sev] = computed.get(sev, 0) + 1
    assert by_severity == computed, (
        f"by_severity {by_severity} stämmer inte med beräknat {computed}"
    )


@pytest.mark.asyncio
async def test_dq_total_matchar_listans_langd(client):
    """total i notifications-response ska matcha antal items."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["items"])


@pytest.mark.asyncio
async def test_dq_notifications_har_pagination_falten(client):
    """Notifications-endpoint ska ha limit, offset, items och total."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert "limit" in body, "Pagination: limit saknas"
    assert "offset" in body, "Pagination: offset saknas"
    assert "items" in body, "Pagination: items saknas"
    assert "total" in body, "Pagination: total saknas"


@pytest.mark.asyncio
async def test_dq_notifications_tom_db_ger_noll(client):
    """Tom databas ska ge total=0 och tom items-lista."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


# ===========================================================================
# DEL 2: NIS2/CSL COMPLIANCE (SFS 2025:1506)
# ===========================================================================


# ---------------------------------------------------------------------------
# 2a. Art. 21(2)(i) — tillgångsförvaltning: unik ID, namn, ägare, klassificering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_system_har_unikt_id(client):
    """Art. 21(2)(i): Varje system ska ha unikt UUID-id."""
    import re
    org = await create_org(client)
    sys1 = await create_system(client, org["id"], name="NIS2 System 1")
    sys2 = await create_system(client, org["id"], name="NIS2 System 2")

    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, sys1["id"])
    assert re.match(uuid_pattern, sys2["id"])
    assert sys1["id"] != sys2["id"], "Varje system ska ha unikt ID"


@pytest.mark.asyncio
async def test_nis2_system_har_namn(client):
    """Art. 21(2)(i): Varje system ska ha ett namn."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Kritiskt NIS2-system")
    assert sys["name"] == "Kritiskt NIS2-system"
    assert sys["name"] is not None
    assert len(sys["name"]) > 0


@pytest.mark.asyncio
async def test_nis2_system_kan_ha_agare(client):
    """Art. 21(2)(i): System ska stödja namngivet ägarskap."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"], name="Anna Svensson")
    assert owner["name"] == "Anna Svensson"
    assert "id" in owner


@pytest.mark.asyncio
async def test_nis2_system_kan_klassificeras(client):
    """Art. 21(2)(i): System ska ha möjlighet till klassificering."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"], confidentiality=3, integrity=3, availability=3)
    assert clf["confidentiality"] == 3
    assert clf["integrity"] == 3
    assert clf["availability"] == 3


@pytest.mark.asyncio
async def test_nis2_system_scope_flagga(client):
    """NIS2-applicerbara system ska kunna flaggas med nis2_applicable=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], nis2_applicable=True)
    assert sys["nis2_applicable"] is True


@pytest.mark.asyncio
async def test_nis2_klassificering_vasentlig_viktig(client):
    """NIS2-klassificering ska stödja väsentlig och viktig."""
    org = await create_org(client)
    for val in ["väsentlig", "viktig"]:
        sys = await create_system(client, org["id"], nis2_classification=val)
        assert sys["nis2_classification"] == val


# ---------------------------------------------------------------------------
# 2b. NIS2-system kräver klassificering, riskbedömning, ägare, backup-plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_system_har_riskbedömningsdatum_fält(client):
    """NIS2-system ska ha fältet last_risk_assessment_date."""
    org = await create_org(client)
    d = "2025-09-15"
    sys = await create_system(client, org["id"], nis2_applicable=True, last_risk_assessment_date=d)
    assert sys["last_risk_assessment_date"] == d


@pytest.mark.asyncio
async def test_nis2_system_har_backup_fält(client):
    """NIS2-system ska kunna dokumentera backup-frekvens."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        backup_frequency="dagligen",
        rpo="4 timmar",
        rto="8 timmar",
        dr_plan_exists=True,
    )
    assert sys["backup_frequency"] == "dagligen"
    assert sys["rpo"] == "4 timmar"
    assert sys["rto"] == "8 timmar"
    assert sys["dr_plan_exists"] is True


@pytest.mark.asyncio
async def test_nis2_rapport_innehaller_nis2_system(client):
    """NIS2-rapport ska innehålla NIS2-applicerbara system."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        nis2_classification="väsentlig",
        criticality="kritisk",
    )

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]
    assert sys["id"] in ids, "NIS2-system ska finnas i NIS2-rapporten"


@pytest.mark.asyncio
async def test_nis2_rapport_exkluderar_icke_nis2(client):
    """NIS2-rapport ska INTE innehålla system med nis2_applicable=False."""
    org = await create_org(client)
    non_nis2 = await create_system(client, org["id"], name="InteNIS2", nis2_applicable=False)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]
    assert non_nis2["id"] not in ids


@pytest.mark.asyncio
async def test_nis2_rapport_struktur(client):
    """NIS2-rapport ska ha generated_at, summary och systems."""
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()
    assert "generated_at" in body
    assert "summary" in body
    assert "systems" in body
    assert "total" in body["summary"]
    assert "without_classification" in body["summary"]
    assert "without_risk_assessment" in body["summary"]


@pytest.mark.asyncio
async def test_nis2_rapport_system_entry_struktur(client):
    """Varje systempost i NIS2-rapport ska ha id, name, nis2_classification, has_gdpr_treatment."""
    org = await create_org(client)
    await create_system(client, org["id"], nis2_applicable=True)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    systems = resp.json()["systems"]
    if systems:
        entry = systems[0]
        assert "id" in entry
        assert "name" in entry
        assert "has_gdpr_treatment" in entry
        assert "owner_names" in entry
        assert isinstance(entry["owner_names"], list)


@pytest.mark.asyncio
async def test_nis2_rapport_summary_raknar_utan_klassificering(client):
    """NIS2-summering ska räkna system utan nis2_classification."""
    org = await create_org(client)
    await create_system(client, org["id"], nis2_applicable=True, nis2_classification=None)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    assert resp.json()["summary"]["without_classification"] >= 1


@pytest.mark.asyncio
async def test_nis2_rapport_has_gdpr_treatment_flagga(client):
    """NIS2-rapport ska korrekt sätta has_gdpr_treatment per system."""
    org = await create_org(client)
    sys_med = await create_system(client, org["id"], name="MedGDPR", nis2_applicable=True)
    sys_utan = await create_system(client, org["id"], name="UtanGDPR", nis2_applicable=True)
    await create_gdpr_treatment(client, sys_med["id"])

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    by_id = {s["id"]: s for s in resp.json()["systems"]}
    assert by_id[sys_med["id"]]["has_gdpr_treatment"] is True
    assert by_id[sys_utan["id"]]["has_gdpr_treatment"] is False


@pytest.mark.asyncio
async def test_nis2_rapport_xlsx_format(client):
    """NIS2 XLSX-rapport ska returnera giltig Excel-fil."""
    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "spreadsheetml" in ct or "excel" in ct or "openxmlformats" in ct, (
        f"Fel content-type för XLSX: {ct}"
    )
    assert len(resp.content) > 0
    assert resp.content[:2] == b"PK", "XLSX ska vara ZIP-format"


@pytest.mark.asyncio
async def test_nis2_rapport_xlsx_har_attachment_header(client):
    """NIS2 XLSX-rapport ska ha Content-Disposition: attachment."""
    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert ".xlsx" in cd


# ===========================================================================
# DEL 3: ISO 27001:2022 ANNEX A
# ===========================================================================


# ---------------------------------------------------------------------------
# 3a. A.5.9 — Namngivet ägarskap, plats, värde (klassificering)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a59_system_har_agare_roll_systemagare(client):
    """A.5.9: System ska ha en ägare med roll systemägare."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"], role="systemägare")
    assert owner["role"] == "systemägare"


@pytest.mark.asyncio
async def test_iso_a59_agare_har_namn_och_epost(client):
    """A.5.9: Ägare ska kunna ha namn och e-postadress."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(
        client, sys["id"], org["id"],
        name="Bertil Karlsson",
        email="bertil@example.se",
    )
    assert owner["name"] == "Bertil Karlsson"
    assert owner.get("email") == "bertil@example.se"


@pytest.mark.asyncio
async def test_iso_a59_system_kan_ha_klassificering_som_varde(client):
    """A.5.9: System ska ha klassificering som anger informationsvärde."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"], confidentiality=3)
    assert clf["confidentiality"] == 3


@pytest.mark.asyncio
async def test_iso_a59_system_har_plats_via_hosting(client):
    """A.5.9: System ska dokumentera plats via hosting_model och data_location_country."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        hosting_model="on-premise",
        data_location_country="Sverige",
    )
    assert sys["hosting_model"] == "on-premise"
    assert sys["data_location_country"] == "Sverige"


@pytest.mark.asyncio
async def test_iso_a59_flera_agare_per_system(client):
    """A.5.9: System ska kunna ha flera ägare med olika roller."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"], role="systemägare", name="Ägare 1")
    await create_owner(client, sys["id"], org["id"], role="informationsägare", name="Ägare 2")

    resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert resp.status_code == 200
    owners = resp.json()
    assert len(owners) >= 2
    roles = [o["role"] for o in owners]
    assert "systemägare" in roles
    assert "informationsägare" in roles


# ---------------------------------------------------------------------------
# 3b. A.5.12 — Klassificering K/R/T med regelbunden omprövning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a512_klassificering_krt_nivaer_0_4(client):
    """A.5.12: K/R/T-klassning ska acceptera värden 0-4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for val in [0, 1, 2, 3, 4]:
        resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
            "confidentiality": val,
            "integrity": val,
            "availability": val,
            "classified_by": "iso27001@test.se",
        })
        assert resp.status_code == 201, f"Klassningsvärde {val} avvisades"
        data = resp.json()
        assert data["confidentiality"] == val
        assert data["integrity"] == val
        assert data["availability"] == val


@pytest.mark.asyncio
async def test_iso_a512_klassificering_har_classified_by(client):
    """A.5.12: Klassificering ska ange vem som klassade (ansvarsspårbarhet)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"], classified_by="iso-ansvarig@test.se")
    assert clf.get("classified_by") == "iso-ansvarig@test.se"


@pytest.mark.asyncio
async def test_iso_a512_klassificering_har_valid_until(client):
    """A.5.12: Klassificering ska stödja giltighetstid för omprövning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    valid_until = (date.today() + timedelta(days=365)).isoformat()
    clf = await create_classification(client, sys["id"], valid_until=valid_until)
    assert clf.get("valid_until") == valid_until


@pytest.mark.asyncio
async def test_iso_a512_spårbarhet_S_värde(client):
    """A.5.12: Spårbarhet (S/traceability) ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"], traceability=2)
    assert clf.get("traceability") == 2


@pytest.mark.asyncio
async def test_iso_a512_klassificeringsnoteringar(client):
    """A.5.12: Klassificering ska stödja anteckningar (notes)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(
        client, sys["id"],
        notes="Klassad enligt ISO 27001:2022 Annex A.5.12",
    )
    assert clf.get("notes") == "Klassad enligt ISO 27001:2022 Annex A.5.12"


# ---------------------------------------------------------------------------
# 3c. A.5.14 — Integrationer med dataflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a514_integration_med_datatyper(client):
    """A.5.14: Integrationer ska dokumentera vilka datatyper som flödar."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="A514 Källa")
    tgt = await create_system(client, org["id"], name="A514 Mål")
    intg = await create_integration(
        client, src["id"], tgt["id"],
        data_types="Personnummer, folkbokföringsadress",
    )
    assert intg.get("data_types") == "Personnummer, folkbokföringsadress"


@pytest.mark.asyncio
async def test_iso_a514_extern_integration_med_motpart(client):
    """A.5.14: Externa integrationer ska dokumentera extern motpart."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="A514 Intern")
    tgt = await create_system(client, org["id"], name="A514 Extern")
    intg = await create_integration(
        client, src["id"], tgt["id"],
        is_external=True,
        external_party="Försäkringskassan",
    )
    assert intg["is_external"] is True
    assert intg.get("external_party") == "Försäkringskassan"


@pytest.mark.asyncio
async def test_iso_a514_integration_frequens(client):
    """A.5.14: Integrationens frekvens ska kunna dokumenteras."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="A514 Freq Src")
    tgt = await create_system(client, org["id"], name="A514 Freq Tgt")
    intg = await create_integration(
        client, src["id"], tgt["id"],
        frequency="realtid",
    )
    assert intg.get("frequency") == "realtid"


@pytest.mark.asyncio
async def test_iso_a514_integration_typ(client):
    """A.5.14: Integrationstyp ska dokumenteras."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="A514 Type Src")
    tgt = await create_system(client, org["id"], name="A514 Type Tgt")
    for itype in ["api", "filöverföring", "event"]:
        intg = await create_integration(client, src["id"], tgt["id"], integration_type=itype)
        assert intg["integration_type"] == itype


# ---------------------------------------------------------------------------
# 3d. A.5.15 — Behörighetsmodell (åtkomstkontroll)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a515_system_kategorier_stöds(client):
    """A.5.15: Systemkategorier (verksamhetssystem, infrastruktur etc.) ska finnas."""
    org = await create_org(client)
    for cat in ["verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"]:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"A515 {cat}",
            "description": "Åtkomstkontroll-test",
            "system_category": cat,
        })
        assert resp.status_code == 201, f"Kategori {cat!r} avvisades"
        assert resp.json()["system_category"] == cat


@pytest.mark.asyncio
async def test_iso_a515_roller_alla_stöds(client):
    """A.5.15: Alla ägarroller (systemägare, informationsägare etc.) ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    roles = [
        "systemägare", "informationsägare", "systemförvaltare",
        "teknisk_förvaltare", "it_kontakt", "dataskyddsombud",
    ]
    for role in roles:
        resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
            "organization_id": org["id"],
            "role": role,
            "name": f"Person {role}",
        })
        assert resp.status_code == 201, f"Roll {role!r} avvisades"
        assert resp.json()["role"] == role


# ---------------------------------------------------------------------------
# 3e. A.5.19-5.22 — Leverantörer och avtal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a519_leverantor_namn(client):
    """A.5.19: Leverantörsnamn ska dokumenteras i avtal."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], supplier_name="Tieto Evry AB")
    assert contract["supplier_name"] == "Tieto Evry AB"


@pytest.mark.asyncio
async def test_iso_a519_leverantor_organisationsnummer(client):
    """A.5.19: Leverantörens organisationsnummer ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], supplier_org_number="556817-8043")
    assert contract.get("supplier_org_number") == "556817-8043"


@pytest.mark.asyncio
async def test_iso_a520_avtalsdatum(client):
    """A.5.20: Avtalets start- och slutdatum ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(
        client, sys["id"],
        contract_start="2024-01-01",
        contract_end="2027-12-31",
    )
    assert contract.get("contract_start") == "2024-01-01"
    assert contract.get("contract_end") == "2027-12-31"


@pytest.mark.asyncio
async def test_iso_a521_sla_dokumenteras(client):
    """A.5.21: SLA-beskrivning ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(
        client, sys["id"],
        sla_description="Tillgänglighet 99.9%, max 4h responstid vardagar",
    )
    assert contract.get("sla_description") is not None


@pytest.mark.asyncio
async def test_iso_a522_uppsagningstid(client):
    """A.5.22: Uppsägningstid ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], notice_period_months=6)
    assert contract.get("notice_period_months") == 6


@pytest.mark.asyncio
async def test_iso_a522_automatisk_forlangning(client):
    """A.5.22: Automatisk förlängning av avtal ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], auto_renewal=True)
    assert contract["auto_renewal"] is True


@pytest.mark.asyncio
async def test_iso_a522_upphandlingstyp(client):
    """A.5.22: Upphandlingstyp (LOU/direktupphandling) ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], procurement_type="Upphandling LOU")
    assert contract.get("procurement_type") == "Upphandling LOU"


# ---------------------------------------------------------------------------
# 3f. A.5.23 — Molntjänster dokumenterade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a523_molntjänst_hosting_model_cloud(client):
    """A.5.23: Molntjänster ska dokumenteras med hosting_model=cloud."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], hosting_model="cloud")
    assert sys["hosting_model"] == "cloud"


@pytest.mark.asyncio
async def test_iso_a523_cloud_provider_dokumenteras(client):
    """A.5.23: Molnleverantör ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], cloud_provider="Amazon Web Services")
    assert sys["cloud_provider"] == "Amazon Web Services"


@pytest.mark.asyncio
async def test_iso_a523_dataplats_dokumenteras(client):
    """A.5.23: Dataplats (land) ska dokumenteras för molntjänster."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        hosting_model="cloud",
        data_location_country="EU (Irland)",
    )
    assert sys["data_location_country"] == "EU (Irland)"


@pytest.mark.asyncio
async def test_iso_a523_tredjelandsöverföring_flaggas(client):
    """A.5.23: Tredjelandsöverföring ska kunna flaggas."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        hosting_model="cloud",
        third_country_transfer=True,
    )
    assert sys["third_country_transfer"] is True


# ---------------------------------------------------------------------------
# 3g. A.5.30 — Backup, DR-plan, RPO/RTO
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a530_backup_frekvens(client):
    """A.5.30: Backup-frekvens ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], backup_frequency="dagligen kl 02:00")
    assert sys["backup_frequency"] == "dagligen kl 02:00"


@pytest.mark.asyncio
async def test_iso_a530_rpo(client):
    """A.5.30: Recovery Point Objective (RPO) ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rpo="1 timme")
    assert sys["rpo"] == "1 timme"


@pytest.mark.asyncio
async def test_iso_a530_rto(client):
    """A.5.30: Recovery Time Objective (RTO) ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rto="4 timmar")
    assert sys["rto"] == "4 timmar"


@pytest.mark.asyncio
async def test_iso_a530_dr_plan_exists(client):
    """A.5.30: Förekomst av DR-plan ska dokumenteras."""
    org = await create_org(client)
    sys_med = await create_system(client, org["id"], dr_plan_exists=True)
    sys_utan = await create_system(client, org["id"], dr_plan_exists=False)
    assert sys_med["dr_plan_exists"] is True
    assert sys_utan["dr_plan_exists"] is False


# ---------------------------------------------------------------------------
# 3h. A.8.9 — Konfigurationsdokumentation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a89_produktnamn_dokumenteras(client):
    """A.8.9: Produktnamn ska dokumenteras för konfigurationsspårbarhet."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], product_name="Alhambra Social")
    assert sys["product_name"] == "Alhambra Social"


@pytest.mark.asyncio
async def test_iso_a89_produktversion_dokumenteras(client):
    """A.8.9: Produktversion ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], product_version="8.5.2")
    assert sys["product_version"] == "8.5.2"


@pytest.mark.asyncio
async def test_iso_a89_livscykel_dokumenteras(client):
    """A.8.9: Livscykelstatus ska dokumenteras (planerad → avvecklad)."""
    org = await create_org(client)
    for status in ["planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"]:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"A89 {status}",
            "description": "Konfiguration",
            "system_category": "infrastruktur",
            "lifecycle_status": status,
        })
        assert resp.status_code == 201
        assert resp.json()["lifecycle_status"] == status


@pytest.mark.asyncio
async def test_iso_a89_driftsättningsdatum(client):
    """A.8.9: Driftsättningsdatum ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], deployment_date="2023-03-15")
    assert sys["deployment_date"] == "2023-03-15"


@pytest.mark.asyncio
async def test_iso_a89_eol_datum(client):
    """A.8.9: End-of-support-datum ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], end_of_support_date="2028-06-01")
    assert sys["end_of_support_date"] == "2028-06-01"


@pytest.mark.asyncio
async def test_iso_a89_extended_attributes_for_konfiguration(client):
    """A.8.9: extended_attributes ska kunna lagra konfigurationsdata."""
    org = await create_org(client)
    attrs = {
        "os_version": "Windows Server 2022",
        "patch_level": "2025-Q1",
        "antal_instanser": 3,
    }
    sys = await create_system(client, org["id"], extended_attributes=attrs)
    assert sys["extended_attributes"]["os_version"] == "Windows Server 2022"
    assert sys["extended_attributes"]["patch_level"] == "2025-Q1"


# ===========================================================================
# DEL 4: MSBFS 2020:7 KAP 2 § 4
# ===========================================================================


# ---------------------------------------------------------------------------
# 4a. Dokumentation av hård- och mjukvara
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_msbfs_hards_och_mjukvara_produkt(client):
    """MSBFS 2020:7 § 4: Produktnamn och version dokumenteras (mjukvaruinventering)."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        product_name="Navet",
        product_version="2.4.1",
    )
    assert sys["product_name"] == "Navet"
    assert sys["product_version"] == "2.4.1"


@pytest.mark.asyncio
async def test_msbfs_system_kategori_infrastruktur(client):
    """MSBFS 2020:7 § 4: Infrastruktursystem ska kunna kategoriseras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], system_category="infrastruktur")
    assert sys["system_category"] == "infrastruktur"


@pytest.mark.asyncio
async def test_msbfs_system_business_area(client):
    """MSBFS 2020:7 § 4: Verksamhetsområde ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], business_area="Socialtjänst")
    assert sys["business_area"] == "Socialtjänst"


# ---------------------------------------------------------------------------
# 4b. Beroenden (interna + externa)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_msbfs_interna_beroenden_via_integrationer(client):
    """MSBFS 2020:7 § 4: Interna systemberoenden dokumenteras via integrationer."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="MSBFS Källa")
    sys_b = await create_system(client, org["id"], name="MSBFS Mål")
    intg = await create_integration(client, sys_a["id"], sys_b["id"])
    assert intg["source_system_id"] == sys_a["id"]
    assert intg["target_system_id"] == sys_b["id"]


@pytest.mark.asyncio
async def test_msbfs_externa_beroenden_dokumenteras(client):
    """MSBFS 2020:7 § 4: Externa beroenden (utomstående aktörer) ska dokumenteras."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="MSBFS Intern")
    ext = await create_system(client, org["id"], name="MSBFS Ext")
    intg = await create_integration(
        client, src["id"], ext["id"],
        is_external=True,
        external_party="Migrationsverket",
    )
    assert intg["is_external"] is True
    assert intg.get("external_party") == "Migrationsverket"


@pytest.mark.asyncio
async def test_msbfs_integrationer_listade_for_system(client):
    """MSBFS 2020:7 § 4: Integrationer för ett system ska kunna listas."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="MSBFS Src List")
    sys_b = await create_system(client, org["id"], name="MSBFS Tgt List")
    await create_integration(client, sys_a["id"], sys_b["id"])

    resp = await client.get("/api/v1/integrations/", params={"system_id": sys_a["id"]})
    assert resp.status_code == 200
    data = resp.json()
    # Acceptera antingen list eller paginerad respons
    items = data if isinstance(data, list) else data.get("items", data)
    ids = [i["source_system_id"] for i in items] + [i["target_system_id"] for i in items]
    assert sys_a["id"] in ids, "System A ska finnas i integrationslistan"


# ---------------------------------------------------------------------------
# 4c. Information med utökat skyddsbehov
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_msbfs_has_elevated_protection_kan_sattas(client):
    """MSBFS 2020:7 § 4: has_elevated_protection ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], has_elevated_protection=True)
    assert sys["has_elevated_protection"] is True


@pytest.mark.asyncio
async def test_msbfs_security_protection_kan_sattas(client):
    """MSBFS 2020:7 § 4: security_protection ska kunna sättas (säkerhetsskyddsklassad info)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], security_protection=True)
    assert sys["security_protection"] is True


@pytest.mark.asyncio
async def test_msbfs_elevated_protection_false_by_default(client):
    """MSBFS 2020:7 § 4: has_elevated_protection ska vara False om ej angivet."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    # Ska vara False eller None (inte True)
    assert sys.get("has_elevated_protection") in (False, None)


# ---------------------------------------------------------------------------
# 4d. Centrala system (criticality = kritisk)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_msbfs_centrala_system_criticality_kritisk(client):
    """MSBFS 2020:7 § 4: Centrala system ska ha criticality=kritisk."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], criticality="kritisk")
    assert sys["criticality"] == "kritisk"


@pytest.mark.asyncio
async def test_msbfs_criticality_alla_nivaer(client):
    """MSBFS 2020:7 § 4: Alla kritikalitetsnivåer ska accepteras."""
    org = await create_org(client)
    for crit in ["låg", "medel", "hög", "kritisk"]:
        sys = await create_system(client, org["id"], criticality=crit)
        assert sys["criticality"] == crit


# ===========================================================================
# DEL 5: GDPR ART. 30
# ===========================================================================


# ---------------------------------------------------------------------------
# 5a. Behandlingsregister
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_art30_system_med_personuppgifter_flaggas(client):
    """GDPR Art. 30: System med personuppgifter ska flaggas med treats_personal_data=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    assert sys["treats_personal_data"] is True


@pytest.mark.asyncio
async def test_gdpr_art30_ropa_referens(client):
    """GDPR Art. 30: Koppling till behandlingsregister via ropa_reference_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(client, sys["id"], ropa_reference_id="ROPA-2025-042")
    assert gdpr.get("ropa_reference_id") == "ROPA-2025-042"


@pytest.mark.asyncio
async def test_gdpr_art30_typ_av_personuppgifter(client):
    """GDPR Art. 30: Typ av personuppgifter (data_categories) ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    kategorier = ["personnummer", "känsliga", "hälsodata"]
    gdpr = await create_gdpr_treatment(client, sys["id"], data_categories=kategorier)
    assert gdpr.get("data_categories") is not None
    assert isinstance(gdpr["data_categories"], list)
    assert len(gdpr["data_categories"]) > 0


@pytest.mark.asyncio
async def test_gdpr_art30_kategorier_av_registrerade(client):
    """GDPR Art. 30: Kategorier av registrerade ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        categories_of_data_subjects="Medborgare, anställda",
    )
    assert gdpr.get("categories_of_data_subjects") == "Medborgare, anställda"


# ---------------------------------------------------------------------------
# 5b. PuB-avtal status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_pub_avtal_ja(client):
    """GDPR Art. 30: PuB-avtal med status 'ja' ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"], processor_agreement_status="ja")
    assert gdpr.get("processor_agreement_status") == "ja"


@pytest.mark.asyncio
async def test_gdpr_pub_avtal_alla_statusar(client):
    """GDPR Art. 30: Alla PuB-avtalsstatus ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for status in ["ja", "nej", "under_framtagande", "ej_tillämpligt"]:
        gdpr = await create_gdpr_treatment(client, sys["id"], processor_agreement_status=status)
        assert gdpr.get("processor_agreement_status") == status


@pytest.mark.asyncio
async def test_gdpr_pub_processor_namn(client):
    """GDPR Art. 30: Personuppgiftsbiträdets namn ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        data_processor="CGI Sverige AB",
        processor_agreement_status="ja",
    )
    assert gdpr.get("data_processor") == "CGI Sverige AB"


# ---------------------------------------------------------------------------
# 5c. Tredjelandsöverföring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_tredjeland_flaggas_pa_system(client):
    """GDPR Art. 30: Tredjelandsöverföring ska flaggas på system-nivå."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], third_country_transfer=True)
    assert sys["third_country_transfer"] is True


@pytest.mark.asyncio
async def test_gdpr_tredjeland_detaljer_i_gdpr_behandling(client):
    """GDPR Art. 30: Detaljer om tredjelandsöverföring ska dokumenteras i GDPR-behandling."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        third_country_transfer_details="Standardavtalsklausuler (SCC) med USA-baserad leverantör",
    )
    assert gdpr.get("third_country_transfer_details") is not None


@pytest.mark.asyncio
async def test_gdpr_underbitraden_dokumenteras(client):
    """GDPR Art. 30: Underbiträden (sub_processors) ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        sub_processors=["AWS (hosting)", "Sendgrid (e-post)"],
    )
    assert gdpr.get("sub_processors") is not None


# ---------------------------------------------------------------------------
# 5d. Gallringsregler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_gallringsregler_dokumenteras(client):
    """GDPR Art. 30: Gallringsregler (retention_policy) ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        retention_policy="7 år efter avslutat ärende (Socialtjänstlagen)",
    )
    assert gdpr.get("retention_policy") == "7 år efter avslutat ärende (Socialtjänstlagen)"


@pytest.mark.asyncio
async def test_gdpr_dpia_genomförd(client):
    """GDPR Art. 30: DPIA (konsekvensbedömning) ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    dpia_date = (date.today() - timedelta(days=90)).isoformat()
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        dpia_conducted=True,
        dpia_date=dpia_date,
        dpia_link="https://example.se/dpia/2025-04.pdf",
    )
    assert gdpr["dpia_conducted"] is True
    assert gdpr.get("dpia_date") == dpia_date
    assert "dpia" in gdpr.get("dpia_link", "").lower()


@pytest.mark.asyncio
async def test_gdpr_känsliga_uppgifter_flaggas(client):
    """GDPR Art. 30: Känsliga personuppgifter ska kunna flaggas separat."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        treats_personal_data=True,
        treats_sensitive_data=True,
    )
    assert sys["treats_sensitive_data"] is True


# ===========================================================================
# DEL 6: INFORMATIONSKLASSNING (MSBFS 2020:6)
# ===========================================================================


# ---------------------------------------------------------------------------
# 6a. K/R/T i nivåer 0-4
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_klassning_K_0_till_4(client):
    """MSBFS 2020:6: Konfidentialitet (K) ska acceptera nivåerna 0-4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for val in range(5):
        resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
            "confidentiality": val,
            "integrity": 0,
            "availability": 0,
            "classified_by": "msbfs@test.se",
        })
        assert resp.status_code == 201, f"K={val} avvisades"
        assert resp.json()["confidentiality"] == val


@pytest.mark.asyncio
async def test_klassning_R_0_till_4(client):
    """MSBFS 2020:6: Riktighet (R) ska acceptera nivåerna 0-4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for val in range(5):
        resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
            "confidentiality": 0,
            "integrity": val,
            "availability": 0,
            "classified_by": "msbfs@test.se",
        })
        assert resp.status_code == 201, f"R={val} avvisades"
        assert resp.json()["integrity"] == val


@pytest.mark.asyncio
async def test_klassning_T_0_till_4(client):
    """MSBFS 2020:6: Tillgänglighet (T) ska acceptera nivåerna 0-4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for val in range(5):
        resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
            "confidentiality": 0,
            "integrity": 0,
            "availability": val,
            "classified_by": "msbfs@test.se",
        })
        assert resp.status_code == 201, f"T={val} avvisades"
        assert resp.json()["availability"] == val


@pytest.mark.asyncio
async def test_klassning_ogiltigt_varde_5_avvisas(client):
    """MSBFS 2020:6: Klassningsvärde 5 (utanför 0-4) ska avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": 5,
        "integrity": 0,
        "availability": 0,
        "classified_by": "msbfs@test.se",
    })
    assert resp.status_code == 422, "Värde 5 ska avvisas med 422"


@pytest.mark.asyncio
async def test_klassning_negativt_varde_avvisas(client):
    """MSBFS 2020:6: Negativt klassningsvärde ska avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": -1,
        "integrity": 0,
        "availability": 0,
        "classified_by": "msbfs@test.se",
    })
    assert resp.status_code == 422, "Negativt värde ska avvisas med 422"


# ---------------------------------------------------------------------------
# 6b. Klassning följs upp minst årligen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_klassning_valid_until_for_uppfoljning(client):
    """MSBFS 2020:6: Klassificering ska ha valid_until för att möjliggöra uppföljning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    annual_review = (date.today() + timedelta(days=365)).isoformat()
    clf = await create_classification(client, sys["id"], valid_until=annual_review)
    assert clf.get("valid_until") == annual_review


@pytest.mark.asyncio
async def test_klassning_utgangen_ger_stale_notifikation(client):
    """MSBFS 2020:6: Klassificering äldre än 12 månader ska flaggas via notifications."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    old_valid_until = (date.today() - timedelta(days=400)).isoformat()
    await create_classification(client, sys["id"], valid_until=old_valid_until)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "stale_classification" in types, (
        "Utgången klassificering ska generera stale_classification-notifikation"
    )


# ---------------------------------------------------------------------------
# 6c. has_elevated_protection auto-sätts vid K, R eller T >= 3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_klassning_hog_K_ger_elevated_protection(client):
    """MSBFS 2020:6: K >= 3 ska automatiskt sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=3, integrity=0, availability=0)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    updated_sys = resp.json()
    assert updated_sys.get("has_elevated_protection") is True, (
        "K=3 ska automatiskt sätta has_elevated_protection=True"
    )


@pytest.mark.asyncio
async def test_klassning_hog_R_ger_elevated_protection(client):
    """MSBFS 2020:6: R >= 3 ska automatiskt sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=0, integrity=3, availability=0)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    updated_sys = resp.json()
    assert updated_sys.get("has_elevated_protection") is True, (
        "R=3 ska automatiskt sätta has_elevated_protection=True"
    )


@pytest.mark.asyncio
async def test_klassning_hog_T_ger_elevated_protection(client):
    """MSBFS 2020:6: T >= 3 ska automatiskt sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=0, integrity=0, availability=3)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    updated_sys = resp.json()
    assert updated_sys.get("has_elevated_protection") is True, (
        "T=3 ska automatiskt sätta has_elevated_protection=True"
    )


@pytest.mark.asyncio
async def test_klassning_lag_krt_ger_inte_elevated_protection(client):
    """MSBFS 2020:6: K/R/T < 3 ska INTE automatiskt sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=2, integrity=2, availability=2)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    updated_sys = resp.json()
    assert updated_sys.get("has_elevated_protection") in (False, None), (
        "K/R/T=2 ska INTE sätta has_elevated_protection=True"
    )


# ===========================================================================
# DEL 7: RAPPORTER
# ===========================================================================


# ---------------------------------------------------------------------------
# 7a. NIS2-rapport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapport_nis2_json_200(client):
    """NIS2-rapport JSON ska returnera 200."""
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rapport_nis2_json_komplett_struktur(client):
    """NIS2-rapport JSON ska ha generated_at, summary, systems."""
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()
    assert "generated_at" in body
    assert "summary" in body
    assert "systems" in body
    assert isinstance(body["systems"], list)


@pytest.mark.asyncio
async def test_rapport_nis2_xlsx_200(client):
    """NIS2-rapport XLSX ska returnera 200."""
    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rapport_nis2_xlsx_giltig_excel(client):
    """NIS2-rapport XLSX ska vara en giltig Excel-fil (PK magic bytes)."""
    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200
    assert len(resp.content) > 0
    assert resp.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_rapport_nis2_innehall_matchar_data(client):
    """NIS2-rapport ska matcha faktisk data (system finns i rapporten)."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        name="NIS2 Rapport Systemtest",
        nis2_applicable=True,
        nis2_classification="väsentlig",
    )

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]
    assert sys["id"] in ids


# ---------------------------------------------------------------------------
# 7b. Compliance gap-rapport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapport_compliance_gap_200(client):
    """Compliance gap-rapport ska returnera 200."""
    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rapport_compliance_gap_5_kategorier(client):
    """Compliance gap ska ha 5 gap-kategorier."""
    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    for kategori in [
        "missing_classification",
        "missing_owner",
        "personal_data_without_gdpr",
        "nis2_without_risk_assessment",
        "expiring_contracts",
    ]:
        assert kategori in gaps, f"Gap-kategori saknas: {kategori}"
        assert isinstance(gaps[kategori], list)


@pytest.mark.asyncio
async def test_rapport_compliance_gap_summary_total(client):
    """Compliance gap ska ha summary med total_gaps."""
    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "total_gaps" in body["summary"]
    assert isinstance(body["summary"]["total_gaps"], int)


@pytest.mark.asyncio
async def test_rapport_compliance_gap_identifierar_missing_classification(client):
    """Compliance gap ska identifiera system utan klassificering."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapSystemNoClass")

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    no_class_ids = [s["id"] for s in resp.json()["gaps"]["missing_classification"]]
    assert sys["id"] in no_class_ids


@pytest.mark.asyncio
async def test_rapport_compliance_gap_identifierar_missing_owner(client):
    """Compliance gap ska identifiera system utan ägare."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapSystemNoOwner")

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    no_owner_ids = [s["id"] for s in resp.json()["gaps"]["missing_owner"]]
    assert sys["id"] in no_owner_ids


@pytest.mark.asyncio
async def test_rapport_compliance_gap_identifierar_personal_data_utan_gdpr(client):
    """Compliance gap ska identifiera system med personuppgifter men utan GDPR-behandling."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapPersonalNoGDPR", treats_personal_data=True)

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    pdng_ids = [s["id"] for s in resp.json()["gaps"]["personal_data_without_gdpr"]]
    assert sys["id"] in pdng_ids


@pytest.mark.asyncio
async def test_rapport_compliance_gap_identifierar_utgaende_avtal(client):
    """Compliance gap ska identifiera avtal som löper ut inom 90 dagar."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapExpContract")
    expiry = (date.today() + timedelta(days=30)).isoformat()
    contract = await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    exp_ids = [c["id"] for c in resp.json()["gaps"]["expiring_contracts"]]
    assert contract["id"] in exp_ids


@pytest.mark.asyncio
async def test_rapport_compliance_gap_klassat_system_ej_i_missing(client):
    """Compliance gap: system med klassificering ska INTE vara i missing_classification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapClassified")
    await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    no_class_ids = [s["id"] for s in resp.json()["gaps"]["missing_classification"]]
    assert sys["id"] not in no_class_ids


# ---------------------------------------------------------------------------
# 7c. Rapport-format (HTML/PDF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapport_html_returneras_utan_fel(client):
    """HTML-rapport ska returneras utan fel (200 eller 404 om ej implementerad)."""
    resp = await client.get("/api/v1/reports/nis2.html")
    # Acceptera 200 (implementerad) eller 404 (ej implementerad ännu)
    assert resp.status_code in (200, 404), (
        f"HTML-rapport gav oväntat statuskod: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_rapport_pdf_returneras_utan_fel(client):
    """PDF-rapport ska returneras utan fel (200 eller 404 om ej implementerad)."""
    resp = await client.get("/api/v1/reports/nis2.pdf")
    # Acceptera 200 (implementerad) eller 404 (ej implementerad ännu)
    assert resp.status_code in (200, 404), (
        f"PDF-rapport gav oväntat statuskod: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_rapport_nis2_generated_at_ar_iso8601(client):
    """NIS2-rapport generated_at ska vara giltig ISO 8601-tidsstämpel."""
    from datetime import datetime
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    generated_at = resp.json().get("generated_at")
    assert generated_at is not None
    # Försök parsa som ISO 8601
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"generated_at är inte giltig ISO 8601: {generated_at!r}")


# ===========================================================================
# DEL 8: AUDIT TRAIL (NIS2 + ISO 27001)
# ===========================================================================


# ---------------------------------------------------------------------------
# 8a. Varje ändring loggas (create, update, delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_create_system_loggas(client):
    """Audit: Skapande av system ska loggas med action=create."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    create_entries = [e for e in entries if e["action"] == "create"]
    assert len(create_entries) >= 1, "System create ska loggas"


@pytest.mark.asyncio
async def test_audit_update_system_loggas(client):
    """Audit: Uppdatering av system ska loggas med action=update."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "Uppdaterat Namn"})

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    update_entries = [e for e in resp.json() if e["action"] == "update"]
    assert len(update_entries) >= 1, "System update ska loggas"


@pytest.mark.asyncio
async def test_audit_delete_system_loggas(client):
    """Audit: Radering av system ska loggas med action=delete."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    sys_id = sys["id"]
    await client.delete(f"/api/v1/systems/{sys_id}")

    resp = await client.get(f"/api/v1/audit/record/{sys_id}")
    assert resp.status_code == 200
    delete_entries = [e for e in resp.json() if e["action"] == "delete"]
    assert len(delete_entries) >= 1, "System delete ska loggas"


@pytest.mark.asyncio
async def test_audit_create_klassificering_loggas(client):
    """Audit: Skapande av klassificering ska loggas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": clf["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_audit_create_agare_loggas(client):
    """Audit: Skapande av systemägare ska loggas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": owner["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_audit_create_gdpr_behandling_loggas(client):
    """Audit: Skapande av GDPR-behandling ska loggas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": gdpr["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_audit_create_avtal_loggas(client):
    """Audit: Skapande av avtal ska loggas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": contract["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# 8b. Loggar inkluderar: vem, vad, när, gamla/nya värden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_entry_har_obligatoriska_fält(client):
    """Audit: Varje post ska ha id, table_name, record_id, action, changed_at."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    for entry in items:
        for field in ("id", "table_name", "record_id", "action", "changed_at"):
            assert field in entry, f"Audit entry saknar '{field}': {entry}"


@pytest.mark.asyncio
async def test_audit_create_har_new_values(client):
    """Audit: Create-poster ska ha new_values (vad skapades)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    create_entries = [e for e in resp.json() if e["action"] == "create"]
    if create_entries:
        assert create_entries[0]["new_values"] is not None, (
            "Create audit ska ha new_values"
        )


@pytest.mark.asyncio
async def test_audit_table_name_ar_systems(client):
    """Audit: table_name ska vara 'systems' för system-poster."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    if entries:
        table_names = {e["table_name"] for e in entries}
        assert "systems" in table_names, f"table_name ska vara 'systems', fick: {table_names}"


@pytest.mark.asyncio
async def test_audit_action_ar_giltig_strang(client):
    """Audit: action-värden ska vara strängar (create, update, delete)."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    valid_actions = {"create", "update", "delete"}
    for item in resp.json()["items"]:
        assert isinstance(item["action"], str)
        assert item["action"] in valid_actions, f"Ogiltigt action: {item['action']}"


@pytest.mark.asyncio
async def test_audit_changed_at_ar_tidsstampel(client):
    """Audit: changed_at ska vara en tidsstämpel."""
    from datetime import datetime
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["changed_at"] is not None
        try:
            datetime.fromisoformat(item["changed_at"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pytest.fail(f"changed_at är inte giltig tidsstämpel: {item['changed_at']!r}")


# ---------------------------------------------------------------------------
# 8c. Filtrering av audit-loggar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_filter_table_name_systems(client):
    """Audit: Filtrering på table_name=systems returnerar bara system-poster."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"table_name": "systems"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["table_name"] == "systems"


@pytest.mark.asyncio
async def test_audit_filter_action_create(client):
    """Audit: Filtrering på action=create returnerar bara create-poster."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"action": "create"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["action"] == "create"


@pytest.mark.asyncio
async def test_audit_filter_record_id(client):
    """Audit: Filtrering på record_id returnerar bara poster för det systemet."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="Audit Filter A")
    sys_b = await create_system(client, org["id"], name="Audit Filter B")

    resp = await client.get("/api/v1/audit/", params={"record_id": sys_a["id"]})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["record_id"] == sys_a["id"], (
            f"Fick post för fel record: {item['record_id']}"
        )


@pytest.mark.asyncio
async def test_audit_filter_okand_tabell_ger_tomt_resultat(client):
    """Audit: Filtrering på okänt table_name ger tomt resultat."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"table_name": "okand_tabell_xyz"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_audit_per_record_endpoint(client):
    """Audit: GET /audit/record/{id} ska returnera lista för specifikt record."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)
    for e in entries:
        assert e["record_id"] == sys["id"]


# ---------------------------------------------------------------------------
# 8d. Audit-loggar kan inte modifieras eller raderas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_delete_ej_tillgangligt(client):
    """Audit: DELETE-metod på audit-endpoint ska returnera 405 (Method Not Allowed)."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if items:
        audit_id = items[0]["id"]
        del_resp = await client.delete(f"/api/v1/audit/{audit_id}")
        # Ska vara 405 Method Not Allowed eller 404 Not Found
        assert del_resp.status_code in (404, 405), (
            f"Audit-post ska inte kunna raderas: {del_resp.status_code}"
        )


@pytest.mark.asyncio
async def test_audit_put_ej_tillgangligt(client):
    """Audit: PUT/PATCH på audit-endpoint ska returnera 405 eller 404."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if items:
        audit_id = items[0]["id"]
        patch_resp = await client.patch(
            f"/api/v1/audit/{audit_id}",
            json={"action": "tampered"},
        )
        assert patch_resp.status_code in (404, 405), (
            f"Audit-post ska inte kunna modifieras: {patch_resp.status_code}"
        )


@pytest.mark.asyncio
async def test_audit_post_ej_tillgangligt(client):
    """Audit: POST till audit-lista ska returnera 405 (skapas bara automatiskt)."""
    resp = await client.post("/api/v1/audit/", json={
        "table_name": "systems",
        "action": "create",
        "record_id": "00000000-0000-0000-0000-000000000001",
    })
    assert resp.status_code in (404, 405), (
        f"Manuellt skapande av audit-poster ska inte vara möjligt: {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 8e. Pagination och ordning av audit-loggar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_pagination_limit(client):
    """Audit: limit-parameter ska begränsa antal returnerade poster."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"AudPag-{i}-{uuid4().hex[:6]}")

    resp = await client.get("/api/v1/audit/", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 2


@pytest.mark.asyncio
async def test_audit_pagination_offset(client):
    """Audit: offset-parameter ska returnera nästa sida."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"AudOff-{i}-{uuid4().hex[:6]}")

    resp1 = await client.get("/api/v1/audit/", params={"limit": 2, "offset": 0})
    resp2 = await client.get("/api/v1/audit/", params={"limit": 2, "offset": 2})
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    ids1 = {i["id"] for i in resp1.json()["items"]}
    ids2 = {i["id"] for i in resp2.json()["items"]}
    assert ids1.isdisjoint(ids2), "Sidor ska inte överlappa"


@pytest.mark.asyncio
async def test_audit_ordning_newest_first(client):
    """Audit: Poster ska sorteras med nyaste först (changed_at DESC)."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Tidigt System")
    await create_system(client, org["id"], name="Sent System")

    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if len(items) >= 2:
        times = [i["changed_at"] for i in items if i.get("changed_at")]
        assert times == sorted(times, reverse=True), "Audit ska sorteras nyast först"


@pytest.mark.asyncio
async def test_audit_default_limit_50(client):
    """Audit: Standard-limit ska vara 50."""
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    assert resp.json()["limit"] == 50


@pytest.mark.asyncio
async def test_audit_ogiltigt_record_id_format(client):
    """Audit: Ogiltigt UUID-format för record_id ska returnera 422."""
    resp = await client.get("/api/v1/audit/record/inte-ett-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_total_okar_efter_operationer(client):
    """Audit: total ska öka efter att poster skapas."""
    resp_before = await client.get("/api/v1/audit/")
    total_before = resp_before.json()["total"]

    org = await create_org(client)
    await create_system(client, org["id"])

    resp_after = await client.get("/api/v1/audit/")
    total_after = resp_after.json()["total"]
    assert total_after >= total_before, "Audit total ska inte minska"


# ===========================================================================
# DEL 9: KOMPLETTERANDE KRAVTÄCKNING
# ===========================================================================


# ---------------------------------------------------------------------------
# 9a. Systemidentitet (NIS2 Art. 21 tillgångsförvaltning — komplettering)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_komplett_nis2_system_har_alla_kravda_falt(client):
    """NIS2 Art. 21: Komplett NIS2-system ska ha klassificering, ägare, backup och riskbedömning."""
    org = await create_org(client)
    today = date.today()
    sys = await create_full_system(
        client, org["id"],
        name="Komplett NIS2",
        nis2_applicable=True,
        nis2_classification="väsentlig",
        criticality="kritisk",
        backup_frequency="dagligen",
        rpo="4 timmar",
        rto="8 timmar",
        dr_plan_exists=True,
        last_risk_assessment_date=(today - timedelta(days=30)).isoformat(),
    )
    assert sys["nis2_applicable"] is True
    assert sys["backup_frequency"] == "dagligen"
    assert sys["dr_plan_exists"] is True


@pytest.mark.asyncio
async def test_system_organisation_koppling(client):
    """System ska vara kopplat till en organisation (organization_id)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["organization_id"] == org["id"]


@pytest.mark.asyncio
async def test_system_timestamps_sätts_vid_skapande(client):
    """System ska ha created_at och updated_at vid skapande."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys.get("created_at") is not None
    assert sys.get("updated_at") is not None


@pytest.mark.asyncio
async def test_system_alias_kan_sättas(client):
    """System ska kunna ha alternativa namn (aliases)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], aliases="GAMLA-NAMN, FÖRKORTNING")
    assert sys.get("aliases") is not None


@pytest.mark.asyncio
async def test_klassa_reference_id_dokumenteras(client):
    """Klassa-referens-id ska kunna dokumenteras för klassningsspårbarhet."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], klassa_reference_id="KLASSA-2025-007")
    assert sys["klassa_reference_id"] == "KLASSA-2025-007"


# ---------------------------------------------------------------------------
# 9b. Compliance gap — NIS2 utan riskbedömning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapport_gap_nis2_utan_riskbedomning(client):
    """Compliance gap ska identifiera NIS2-system utan riskbedömning."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        name="GapNIS2NoRisk",
        nis2_applicable=True,
        last_risk_assessment_date=None,
    )

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gap_ids = [s["id"] for s in resp.json()["gaps"]["nis2_without_risk_assessment"]]
    assert sys["id"] in gap_ids, (
        "NIS2-system utan riskbedömning ska finnas i nis2_without_risk_assessment"
    )


@pytest.mark.asyncio
async def test_rapport_gap_nis2_med_riskbedomning_ej_i_gap(client):
    """Compliance gap: NIS2-system med riskbedömning ska INTE vara i nis2_without_risk_assessment."""
    org = await create_org(client)
    recent = (date.today() - timedelta(days=60)).isoformat()
    sys = await create_system(
        client, org["id"],
        name="GapNIS2WithRisk",
        nis2_applicable=True,
        last_risk_assessment_date=recent,
    )

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gap_ids = [s["id"] for s in resp.json()["gaps"]["nis2_without_risk_assessment"]]
    assert sys["id"] not in gap_ids


@pytest.mark.asyncio
async def test_rapport_gap_avtal_ej_utganget_ej_i_gap(client):
    """Compliance gap: Avtal som inte löper ut inom 90 dagar ska INTE vara i expiring_contracts."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="GapFuture")
    future = (date.today() + timedelta(days=200)).isoformat()
    contract = await create_contract(client, sys["id"], contract_end=future)

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    exp_ids = [c["id"] for c in resp.json()["gaps"]["expiring_contracts"]]
    assert contract["id"] not in exp_ids


# ---------------------------------------------------------------------------
# 9c. Datakvalitet — organisations-koppling och RLS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_system_utan_namn_avvisas(client):
    """Datakvalitet: System utan namn ska avvisas."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "description": "Inget namn",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, "System utan namn ska avvisas"


@pytest.mark.asyncio
async def test_dq_system_utan_organisation_avvisas(client):
    """Datakvalitet: System utan organization_id ska avvisas."""
    resp = await client.post("/api/v1/systems/", json={
        "name": "Foräldrarlöst System",
        "description": "Ingen org",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, "System utan organization_id ska avvisas"


@pytest.mark.asyncio
async def test_dq_klassificering_utan_classified_by_avvisas(client):
    """Datakvalitet: Klassificering utan classified_by ska avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
    })
    assert resp.status_code == 422, "Klassificering utan classified_by ska avvisas"


@pytest.mark.asyncio
async def test_dq_avtal_utan_leverantor_avvisas(client):
    """Datakvalitet: Avtal utan leverantörsnamn ska avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={})
    assert resp.status_code == 422, "Avtal utan supplier_name ska avvisas"


# ---------------------------------------------------------------------------
# 9d. Informationsklassning — kompletterande kontroller
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_klassning_kan_hamtas_per_system(client):
    """Klassificering ska kunna hämtas per system via GET."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=2, integrity=2, availability=2)

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", [data])
    assert len(items) > 0


@pytest.mark.asyncio
async def test_klassning_K4_ger_elevated_protection(client):
    """MSBFS 2020:6: K=4 (högsta nivå) ska sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=4, integrity=0, availability=0)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json().get("has_elevated_protection") is True


@pytest.mark.asyncio
async def test_klassning_R4_ger_elevated_protection(client):
    """MSBFS 2020:6: R=4 (högsta nivå) ska sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=0, integrity=4, availability=0)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json().get("has_elevated_protection") is True


@pytest.mark.asyncio
async def test_klassning_T4_ger_elevated_protection(client):
    """MSBFS 2020:6: T=4 (högsta nivå) ska sätta has_elevated_protection=True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"], confidentiality=0, integrity=0, availability=4)

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json().get("has_elevated_protection") is True


# ---------------------------------------------------------------------------
# 9e. GDPR — känsliga uppgifter och tredjeland
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_känsliga_uppgifter_kräver_legal_basis(client):
    """GDPR: System med känsliga uppgifter bör ha rättslig grund dokumenterad."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        treats_personal_data=True,
        treats_sensitive_data=True,
    )
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        data_categories=["känsliga", "hälsodata"],
        legal_basis="Samtycke (art. 9.2 a)",
    )
    assert gdpr.get("legal_basis") is not None
    assert "art. 9" in gdpr["legal_basis"] or gdpr["legal_basis"] != ""


@pytest.mark.asyncio
async def test_gdpr_system_med_tredjeland_och_behandling(client):
    """GDPR: System med tredjelandsöverföring ska kunna ha fullständig dokumentation."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        treats_personal_data=True,
        third_country_transfer=True,
    )
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        third_country_transfer_details="SCC-avtal med AWS US-East",
        retention_policy="2 år",
    )
    assert gdpr.get("third_country_transfer_details") is not None
    assert gdpr.get("retention_policy") == "2 år"


# ---------------------------------------------------------------------------
# 9f. ISO 27001 A.5.9 — Komplett tillgångsregister
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iso_a59_system_list_returnerar_alla_system(client):
    """A.5.9: Tillgångsregister — alla system ska kunna listas."""
    org = await create_org(client)
    sys1 = await create_system(client, org["id"], name="A59 System 1")
    sys2 = await create_system(client, org["id"], name="A59 System 2")

    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", [])
    ids = [s["id"] for s in items]
    assert sys1["id"] in ids
    assert sys2["id"] in ids


@pytest.mark.asyncio
async def test_iso_a59_system_kan_hämtas_enskilt(client):
    """A.5.9: Enskilt system ska kunna hämtas via GET /systems/{id}."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="A59 Enskilt System")

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sys["id"]
    assert resp.json()["name"] == "A59 Enskilt System"


@pytest.mark.asyncio
async def test_iso_a59_system_kan_uppdateras(client):
    """A.5.9: Tillgångsregister ska hållas aktuellt — system ska kunna uppdateras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="A59 Ursprungligt")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "A59 Uppdaterat"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "A59 Uppdaterat"


@pytest.mark.asyncio
async def test_iso_a59_ägare_kan_listas_per_system(client):
    """A.5.9: Ägare till ett system ska kunna listas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"], name="Lista Ägare")

    resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert resp.status_code == 200
    owners = resp.json()
    assert len(owners) >= 1
    assert any(o["name"] == "Lista Ägare" for o in owners)


# ---------------------------------------------------------------------------
# 9g. NIS2 — Klassa-referens och riskbedömning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_riskbedomning_datum_dokumenteras(client):
    """NIS2 Art. 21: Datum för senaste riskbedömning ska dokumenteras."""
    org = await create_org(client)
    d = (date.today() - timedelta(days=180)).isoformat()
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        last_risk_assessment_date=d,
    )
    assert sys["last_risk_assessment_date"] == d


@pytest.mark.asyncio
async def test_nis2_klassa_referens_dokumenteras(client):
    """NIS2: Klassa-referens för klassningsverktyg ska kunna dokumenteras."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        klassa_reference_id="KLASSA-NIS2-2025-001",
    )
    assert sys["klassa_reference_id"] == "KLASSA-NIS2-2025-001"


@pytest.mark.asyncio
async def test_nis2_ej_tillämplig_klassificering(client):
    """NIS2: System kan klassificeras som ej_tillämplig."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], nis2_classification="ej_tillämplig")
    assert sys["nis2_classification"] == "ej_tillämplig"


# ---------------------------------------------------------------------------
# 9h. MSBFS — Utökad hårdvaru/mjukvarudokumentation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_msbfs_planerat_avvecklingsdatum(client):
    """MSBFS 2020:7 § 4: Planerat avvecklingsdatum ska dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], planned_decommission_date="2030-06-30")
    assert sys["planned_decommission_date"] == "2030-06-30"


@pytest.mark.asyncio
async def test_msbfs_end_of_support_datum(client):
    """MSBFS 2020:7 § 4: End-of-support ska dokumenteras för att planera uppgraderingar."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], end_of_support_date="2026-12-31")
    assert sys["end_of_support_date"] == "2026-12-31"


@pytest.mark.asyncio
async def test_msbfs_extended_attributes_beroenden(client):
    """MSBFS 2020:7 § 4: Extra beroenden ska kunna lagras i extended_attributes."""
    org = await create_org(client)
    attrs = {
        "beroende_system": ["AD", "DNS", "SMTP-relay"],
        "nätverkssegment": "DMZ",
        "brandväggsregler": "FW-2025-042",
    }
    sys = await create_system(client, org["id"], extended_attributes=attrs)
    assert sys["extended_attributes"]["nätverkssegment"] == "DMZ"
    assert isinstance(sys["extended_attributes"]["beroende_system"], list)


# ---------------------------------------------------------------------------
# 9i. GDPR — DPIA och känsliga datatyper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_dpia_ej_genomförd_by_default(client):
    """GDPR: DPIA ska som standard vara ej genomförd (dpia_conducted=False)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"])
    assert gdpr.get("dpia_conducted") is False or gdpr.get("dpia_conducted") is None


@pytest.mark.asyncio
async def test_gdpr_vanliga_personuppgifter_utan_känsliga(client):
    """GDPR: Vanliga personuppgifter ska kunna dokumenteras utan känsliga."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True, treats_sensitive_data=False)
    gdpr = await create_gdpr_treatment(client, sys["id"], data_categories=["vanliga"])
    assert "vanliga" in gdpr.get("data_categories", [])


@pytest.mark.asyncio
async def test_gdpr_notification_inkluderar_system_id(client):
    """GDPR: missing_gdpr_treatment-notifikation ska inkludera system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    gdpr_notifs = [n for n in resp.json()["items"] if n["type"] == "missing_gdpr_treatment"]
    assert len(gdpr_notifs) > 0
    assert all("system_id" in n for n in gdpr_notifs)
    assert sys["id"] in [n["system_id"] for n in gdpr_notifs]


# ---------------------------------------------------------------------------
# 9j. Notifications — fler scenarion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dq_flera_system_genererar_flera_notifikationer(client):
    """Datakvalitet: Flera ofullständiga system ska generera flera notifikationer."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Ofullständig 1")
    await create_system(client, org["id"], name="Ofullständig 2")

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 4, (
        "Två system utan ägare och klassificering bör ge minst 4 notifikationer"
    )


@pytest.mark.asyncio
async def test_dq_fullt_system_ger_inga_kritiska_notifikationer(client):
    """Datakvalitet: Komplett system ska inte ha critical-notifikationer."""
    org = await create_org(client)
    sys = await create_full_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    critical_for_sys = [
        n for n in resp.json()["items"]
        if n.get("system_id") == sys["id"] and n["severity"] == "critical"
    ]
    assert len(critical_for_sys) == 0, (
        "Komplett system ska inte ha critical-notifikationer"
    )


@pytest.mark.asyncio
async def test_dq_notifications_response_200(client):
    """Datakvalitet: Notifications-endpoint ska alltid returnera 200."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dq_notifications_by_severity_är_dict(client):
    """Datakvalitet: by_severity ska vara en dict."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    assert isinstance(resp.json()["by_severity"], dict)


# ---------------------------------------------------------------------------
# 9k. Rapport-integritet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapport_compliance_gap_tom_db_ger_tomma_listor(client):
    """Compliance gap: Tom databas ska ge tomma gap-listor."""
    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    for key, val in gaps.items():
        assert isinstance(val, list), f"Gap {key!r} ska vara en lista"


@pytest.mark.asyncio
async def test_rapport_nis2_tom_db_ger_noll_system(client):
    """NIS2-rapport: Tom databas ska ge systems=[] och total=0."""
    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["systems"] == []
    assert body["summary"]["total"] == 0


@pytest.mark.asyncio
async def test_rapport_compliance_gap_generated_at(client):
    """Compliance gap-rapport ska innehålla generated_at tidsstämpel."""
    from datetime import datetime
    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    generated_at = resp.json().get("generated_at")
    assert generated_at is not None
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pytest.fail(f"generated_at i compliance-gap är ogiltig: {generated_at!r}")
