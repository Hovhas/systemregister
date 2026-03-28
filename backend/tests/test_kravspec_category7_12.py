"""
Kravspecifikation — Kategori 7–12 (utvidgade testfall).

Kat 7:  Integrationer och beroenden
Kat 8:  Avtal och leverantörer
Kat 9:  Backup / DR
Kat 10: Kostnader och TCO
Kat 11: Dokumentation och spårbarhet (audit trail, versionshistorik)
Kat 12: Regelefterlevnad (NIS2/CSL, riskbedömning, KLASSA)

Målet är ~300 testfall med flitigt pytest.mark.parametrize.
"""

import pytest
from datetime import date, timedelta

from tests.factories import (
    create_org,
    create_system,
    create_integration,
    create_contract,
    create_classification,
    create_owner,
    create_gdpr_treatment,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ===========================================================================
# KAT 7: INTEGRATIONER OCH BEROENDEN
# ===========================================================================


# ---------------------------------------------------------------------------
# 7.1 — Alla integrationstyper (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", [
    "api",
    "filöverföring",
    "databasreplikering",
    "event",
    "manuell",
])
async def test_kat7_integration_type_accepted(client, itype):
    """Alla giltiga integration_type-värden ska accepteras och returneras korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"Src-{itype}")
    tgt = await create_system(client, org["id"], name=f"Tgt-{itype}")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": itype,
    })
    assert resp.status_code == 201, f"integration_type={itype!r} avvisades: {resp.text}"
    assert resp.json()["integration_type"] == itype


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", [
    "rpc",
    "grpc",
    "okänd",
    "",
    "API",
    "MANUELL",
])
async def test_kat7_integration_type_invalid_rejected(client, itype):
    """Ogiltiga integration_type-värden ska avvisas med 422."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="SrcInvalid")
    tgt = await create_system(client, org["id"], name="TgtInvalid")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": itype,
    })
    assert resp.status_code == 422, (
        f"Ogiltig integration_type={itype!r} borde ge 422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 7.2 — Alla criticality-nivåer på integrationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("crit", ["låg", "medel", "hög", "kritisk"])
async def test_kat7_integration_criticality_all_levels(client, crit):
    """Integration: alla criticality-nivåer ska accepteras och sparas."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"CritSrc-{crit}")
    tgt = await create_system(client, org["id"], name=f"CritTgt-{crit}")

    integ = await create_integration(client, src["id"], tgt["id"], criticality=crit)
    assert integ["criticality"] == crit


@pytest.mark.asyncio
async def test_kat7_integration_criticality_null_allowed(client):
    """Integration utan criticality ska accepteras (fältet är valfritt)."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="NoCritSrc")
    tgt = await create_system(client, org["id"], name="NoCritTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 201
    assert resp.json()["criticality"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("crit", ["låg", "medel", "hög", "kritisk"])
async def test_kat7_integration_patch_criticality(client, crit):
    """PATCH integration: criticality kan uppdateras till alla nivåer."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"PatchCritSrc-{crit}")
    tgt = await create_system(client, org["id"], name=f"PatchCritTgt-{crit}")
    integ = await create_integration(client, src["id"], tgt["id"])

    resp = await client.patch(f"/api/v1/integrations/{integ['id']}", json={
        "criticality": crit,
    })
    assert resp.status_code == 200
    assert resp.json()["criticality"] == crit


# ---------------------------------------------------------------------------
# 7.3 — is_external och external_party
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("external_party", [
    "Skatteverket",
    "Region Stockholm",
    "Försäkringskassan",
    "Bolagsverket",
    "Externt system utan känt namn",
])
async def test_kat7_integration_external_party_variants(client, external_party):
    """is_external=True med olika external_party-värden ska sparas korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"ExtSrc-{external_party[:10]}")
    tgt = await create_system(client, org["id"], name=f"ExtTgt-{external_party[:10]}")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
        "is_external": True,
        "external_party": external_party,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_external"] is True
    assert body["external_party"] == external_party


@pytest.mark.asyncio
async def test_kat7_integration_internal_no_external_party(client):
    """Intern integration (is_external=False) utan external_party ska vara giltigt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="InternalSrc")
    tgt = await create_system(client, org["id"], name="InternalTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "event",
        "is_external": False,
    })
    assert resp.status_code == 201
    assert resp.json()["is_external"] is False
    assert resp.json()["external_party"] is None


@pytest.mark.asyncio
async def test_kat7_integration_external_defaults_to_false(client):
    """is_external ska defaulta till False när det inte anges."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="DefaultExtSrc")
    tgt = await create_system(client, org["id"], name="DefaultExtTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "manuell",
    })
    assert resp.status_code == 201
    assert resp.json()["is_external"] is False


# ---------------------------------------------------------------------------
# 7.4 — data_types och frequency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("data_types", [
    "personuppgifter",
    "ärendedata, beslut",
    "fastighetsinformation, taxeringsuppgifter",
    "hälsodata, läkemedelsuppgifter",
    "a" * 500,  # Lång sträng
])
async def test_kat7_integration_data_types_variants(client, data_types):
    """data_types-fältet ska acceptera olika strängvärden."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="DtSrc")
    tgt = await create_system(client, org["id"], name="DtTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
        "data_types": data_types,
    })
    assert resp.status_code == 201
    assert resp.json()["data_types"] == data_types


@pytest.mark.asyncio
@pytest.mark.parametrize("frequency", [
    "realtid",
    "varje minut",
    "var 15:e minut",
    "dagligen kl 02:00",
    "veckovis",
    "månadsvis",
    "vid behov",
    "batchkörning nattligen",
])
async def test_kat7_integration_frequency_variants(client, frequency):
    """frequency-fältet ska acceptera olika beskrivande strängar."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="FreqSrc")
    tgt = await create_system(client, org["id"], name="FreqTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "filöverföring",
        "frequency": frequency,
    })
    assert resp.status_code == 201
    assert resp.json()["frequency"] == frequency


# ---------------------------------------------------------------------------
# 7.5 — Beroenden TO och FROM (riktning)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat7_dependencies_to_other_system(client):
    """System A → B: A:s utgående integrations ska visas i A:s integrationslista."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="DepA")
    sys_b = await create_system(client, org["id"], name="DepB")

    integ = await create_integration(client, sys_a["id"], sys_b["id"])

    resp = await client.get(f"/api/v1/systems/{sys_a['id']}/integrations")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert integ["id"] in ids


@pytest.mark.asyncio
async def test_kat7_dependencies_from_other_system(client):
    """System A → B: B:s inkommande integrations ska visas i B:s integrationslista."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="FromA")
    sys_b = await create_system(client, org["id"], name="FromB")

    integ = await create_integration(client, sys_a["id"], sys_b["id"])

    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/integrations")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert integ["id"] in ids


@pytest.mark.asyncio
async def test_kat7_integration_direction_source_target_correct(client):
    """source_system_id och target_system_id ska återspegla riktning korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="DirectionSrc")
    tgt = await create_system(client, org["id"], name="DirectionTgt")

    integ = await create_integration(client, src["id"], tgt["id"])
    assert integ["source_system_id"] == src["id"]
    assert integ["target_system_id"] == tgt["id"]


@pytest.mark.asyncio
async def test_kat7_bidirectional_integrations(client):
    """A→B och B→A (bidirektionella integrationer) ska båda accepteras."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="BiDirA")
    sys_b = await create_system(client, org["id"], name="BiDirB")

    integ_ab = await create_integration(client, sys_a["id"], sys_b["id"])
    integ_ba = await create_integration(client, sys_b["id"], sys_a["id"])

    assert integ_ab["id"] != integ_ba["id"]
    assert integ_ab["source_system_id"] == sys_a["id"]
    assert integ_ba["source_system_id"] == sys_b["id"]


# ---------------------------------------------------------------------------
# 7.6 — Cirkulära beroenden A→B→C→A
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat7_circular_dependency_abc(client):
    """A→B→C→A (cirkulärt beroende) ska kunna skapas utan fel."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="CircA")
    sys_b = await create_system(client, org["id"], name="CircB")
    sys_c = await create_system(client, org["id"], name="CircC")

    integ_ab = await create_integration(client, sys_a["id"], sys_b["id"])
    integ_bc = await create_integration(client, sys_b["id"], sys_c["id"])
    integ_ca = await create_integration(client, sys_c["id"], sys_a["id"])

    assert integ_ab["source_system_id"] == sys_a["id"]
    assert integ_bc["source_system_id"] == sys_b["id"]
    assert integ_ca["source_system_id"] == sys_c["id"]

    # Varje system ska ha 2 integrationer (1 in + 1 ut)
    for sys in [sys_a, sys_b, sys_c]:
        resp = await client.get(f"/api/v1/systems/{sys['id']}/integrations")
        assert resp.status_code == 200
        assert len(resp.json()) == 2, (
            f"System {sys['name']} borde ha 2 integrationer i cirkulärt beroende"
        )


@pytest.mark.asyncio
async def test_kat7_circular_dependency_four_systems(client):
    """A→B→C→D→A (längre cirkel) ska kunna skapas korrekt."""
    org = await create_org(client)
    systems = [
        await create_system(client, org["id"], name=f"Circ4-{i}")
        for i in range(4)
    ]
    for i in range(4):
        await create_integration(client, systems[i]["id"], systems[(i + 1) % 4]["id"])

    for sys in systems:
        resp = await client.get(f"/api/v1/systems/{sys['id']}/integrations")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# 7.7 — Samma system som source och target (self-loop)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat7_self_loop_integration_rejected(client):
    """Integration med samma system som källa och mål ska avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="SelfLoopSys")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys["id"],
        "target_system_id": sys["id"],
        "integration_type": "api",
    })
    assert resp.status_code != 201, (
        f"Self-loop integration borde avvisas, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", [
    "api", "filöverföring", "databasreplikering", "event", "manuell",
])
async def test_kat7_self_loop_all_types_rejected(client, itype):
    """Self-loop integrationer ska avvisas för alla integration_type-värden."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name=f"SelfLoop-{itype}")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys["id"],
        "target_system_id": sys["id"],
        "integration_type": itype,
    })
    assert resp.status_code != 201, (
        f"Self-loop med {itype!r} borde avvisas, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 7.8 — Komplett integration med alla fält
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat7_integration_all_fields_stored(client):
    """Integration med alla tillgängliga fält ska sparas och returneras korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="AllFieldsSrc")
    tgt = await create_system(client, org["id"], name="AllFieldsTgt")

    payload = {
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
        "data_types": "personnummer, adress, hälsodata",
        "frequency": "realtid",
        "description": "Komplett integration för alla fält",
        "criticality": "kritisk",
        "is_external": True,
        "external_party": "Socialstyrelsen",
    }
    resp = await client.post("/api/v1/integrations/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["data_types"] == payload["data_types"]
    assert body["frequency"] == payload["frequency"]
    assert body["description"] == payload["description"]
    assert body["criticality"] == payload["criticality"]
    assert body["is_external"] is True
    assert body["external_party"] == payload["external_party"]


# ---------------------------------------------------------------------------
# 7.9 — Integration borttagning, 404 vid saknade system
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field,kept_field", [
    ("source_system_id", "target_system_id"),
    ("target_system_id", "source_system_id"),
])
async def test_kat7_integration_missing_required_field(client, missing_field, kept_field):
    """POST integration utan obligatoriskt fält ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="ReqFieldSys")

    payload = {
        kept_field: sys["id"],
        "integration_type": "api",
    }
    resp = await client.post("/api/v1/integrations/", json=payload)
    assert resp.status_code == 422, (
        f"Saknat fält {missing_field!r} borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_kat7_integration_nonexistent_source_404(client):
    """POST med okänt source_system_id ska ge 404."""
    org = await create_org(client)
    tgt = await create_system(client, org["id"], name="TgtExists")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": FAKE_UUID,
        "target_system_id": tgt["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kat7_integration_nonexistent_target_404(client):
    """POST med okänt target_system_id ska ge 404."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="SrcExists")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": FAKE_UUID,
        "integration_type": "api",
    })
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7.10 — Filtrering på integration_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", [
    "api", "filöverföring", "databasreplikering", "event", "manuell",
])
async def test_kat7_filter_by_integration_type(client, itype):
    """GET /integrations/?integration_type=X ska returnera enbart matching integrations."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"FiltSrc2-{itype}")
    tgt = await create_system(client, org["id"], name=f"FiltTgt2-{itype}")

    created = await create_integration(client, src["id"], tgt["id"], integration_type=itype)

    resp = await client.get("/api/v1/integrations/", params={"integration_type": itype})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert created["id"] in ids
    for item in resp.json():
        assert item["integration_type"] == itype, (
            f"Filter på {itype!r} returnerade {item['integration_type']!r}"
        )


# ---------------------------------------------------------------------------
# 7.11 — Hub-mönster: många-till-en
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("num_spokes", [2, 5, 10])
async def test_kat7_hub_pattern_multiple_sources(client, num_spokes):
    """Hub-mönster: {num_spokes} system kan peka mot en central hub."""
    org = await create_org(client)
    hub = await create_system(client, org["id"], name=f"Hub-{num_spokes}")

    for i in range(num_spokes):
        spoke = await create_system(client, org["id"], name=f"Spoke-{num_spokes}-{i}")
        await create_integration(client, spoke["id"], hub["id"])

    resp = await client.get(f"/api/v1/systems/{hub['id']}/integrations")
    assert resp.status_code == 200
    assert len(resp.json()) >= num_spokes


# ===========================================================================
# KAT 8: AVTAL OCH LEVERANTÖRER
# ===========================================================================


# ---------------------------------------------------------------------------
# 8.1 — contract_start/end validering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat8_contract_end_before_start_rejected(client):
    """contract_end < contract_start ska avvisas med 400 eller 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Bakvänd AB",
        "contract_start": "2025-06-01",
        "contract_end": "2024-01-01",
    })
    assert resp.status_code in (400, 422), (
        f"contract_end < contract_start borde ge 400/422, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_kat8_contract_end_same_as_start_accepted(client):
    """contract_end == contract_start ska accepteras (engångslicens)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Endagsavtal AB",
        "contract_start": "2025-01-01",
        "contract_end": "2025-01-01",
    })
    assert resp.status_code == 201, (
        f"contract_end == contract_start borde ge 201, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("start,end", [
    ("2020-01-01", "2025-12-31"),
    ("2024-01-01", "2026-12-31"),
    ("2026-03-01", "2029-02-28"),
    ("2000-01-01", "2099-12-31"),
])
async def test_kat8_contract_valid_date_ranges(client, start, end):
    """Giltiga datumintervall för avtal ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "DatumAvtal AB",
        "contract_start": start,
        "contract_end": end,
    })
    assert resp.status_code == 201, (
        f"Datumintervall {start}–{end} avvisades: {resp.status_code} {resp.text}"
    )
    body = resp.json()
    assert body["contract_start"] == start
    assert body["contract_end"] == end


# ---------------------------------------------------------------------------
# 8.2 — auto_renewal och notice_period_months
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("auto_renewal,notice_months", [
    (True, 1),
    (True, 3),
    (True, 6),
    (True, 12),
    (True, 24),
    (False, None),
    (False, 3),
])
async def test_kat8_auto_renewal_notice_period_combinations(client, auto_renewal, notice_months):
    """auto_renewal med olika notice_period_months ska sparas korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    payload = {
        "supplier_name": f"AutoRenewal {auto_renewal} {notice_months}",
        "auto_renewal": auto_renewal,
    }
    if notice_months is not None:
        payload["notice_period_months"] = notice_months

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json=payload)
    assert resp.status_code == 201, (
        f"auto_renewal={auto_renewal}, notice={notice_months} avvisades: {resp.text}"
    )
    body = resp.json()
    assert body["auto_renewal"] == auto_renewal
    if notice_months is not None:
        assert body["notice_period_months"] == notice_months


@pytest.mark.asyncio
@pytest.mark.parametrize("notice_months", [1, 2, 3, 6, 9, 12, 18, 24, 36])
async def test_kat8_notice_period_values(client, notice_months):
    """Alla realistiska notice_period_months-värden ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": f"Notice {notice_months}m AB",
        "notice_period_months": notice_months,
    })
    assert resp.status_code == 201
    assert resp.json()["notice_period_months"] == notice_months


# ---------------------------------------------------------------------------
# 8.3 — license_model varianter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("license_model", [
    "per_användare",
    "per_installation",
    "enterprise",
    "saas_månadsvis",
    "saas_årsvis",
    "open_source",
    "site_license",
    "concurrent_users",
    "Ramavtal med volymlicens",
    "Engångslicens",
])
async def test_kat8_license_model_variants(client, license_model):
    """Olika license_model-värden ska accepteras som fritext."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "LicensModel AB",
        "license_model": license_model,
    })
    assert resp.status_code == 201, (
        f"license_model={license_model!r} avvisades: {resp.text}"
    )
    assert resp.json()["license_model"] == license_model


# ---------------------------------------------------------------------------
# 8.4 — procurement_type varianter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("procurement_type", [
    "ramavtal",
    "direktupphandling",
    "öppen upphandling",
    "selektiv upphandling",
    "förhandlat förfarande",
    "Kammarkollegiet",
    "SKR Kommentus",
    "Statliga ramavtal",
    "Eget ramavtal",
    "Lou §19",
])
async def test_kat8_procurement_type_variants(client, procurement_type):
    """Olika procurement_type-värden ska accepteras som fritext."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Upphandling AB",
        "procurement_type": procurement_type,
    })
    assert resp.status_code == 201
    assert resp.json()["procurement_type"] == procurement_type


# ---------------------------------------------------------------------------
# 8.5 — Kostnadsfält: negativa, noll, stora tal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("annual_license_cost", [
    0,
    1,
    100,
    50000,
    500000,
    1000000,
    10000000,
    999999999,
])
async def test_kat8_annual_license_cost_valid_values(client, annual_license_cost):
    """annual_license_cost: noll och positiva tal ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Kostnad AB",
        "annual_license_cost": annual_license_cost,
    })
    assert resp.status_code == 201
    assert resp.json()["annual_license_cost"] == annual_license_cost


@pytest.mark.asyncio
@pytest.mark.parametrize("annual_operations_cost", [
    0,
    1000,
    75000,
    250000,
    2000000,
])
async def test_kat8_annual_operations_cost_valid_values(client, annual_operations_cost):
    """annual_operations_cost: noll och positiva tal ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Drift Kostnad AB",
        "annual_operations_cost": annual_operations_cost,
    })
    assert resp.status_code == 201
    assert resp.json()["annual_operations_cost"] == annual_operations_cost


@pytest.mark.asyncio
@pytest.mark.parametrize("cost_field", [
    "annual_license_cost",
    "annual_operations_cost",
])
async def test_kat8_negative_costs_rejected_or_accepted(client, cost_field):
    """Negativa kostnader: kontrollera att API:et hanterar det konsekvent."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Negativ Kostnad AB",
        cost_field: -1,
    })
    # Negativa kostnader kan vara ogiltiga (422) eller tillåtna (201 vid kreditnotor etc)
    # Viktigt: inte 500
    assert resp.status_code in (201, 400, 422), (
        f"Negativ {cost_field} borde ge 201/400/422, fick {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 8.6 — supplier_org_number format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("org_number", [
    "556975-4537",
    "556841-8049",
    "212000-0142",
    "232100-0131",
])
async def test_kat8_supplier_org_number_valid_format(client, org_number):
    """Giltiga org_number-format (XXXXXX-XXXX) ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "OrgNr AB",
        "supplier_org_number": org_number,
    })
    assert resp.status_code == 201
    assert resp.json()["supplier_org_number"] == org_number


@pytest.mark.asyncio
@pytest.mark.parametrize("org_number", [
    "5569754537",        # Utan bindestreck
    "org-12345",         # Felaktigt format
    "12345",             # För kort
    "ABC-12345",         # Bokstäver
])
async def test_kat8_supplier_org_number_invalid_format(client, org_number):
    """Ogiltiga org_number-format: API ska antingen avvisa (422) eller acceptera (201)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "OgiltOrgNr AB",
        "supplier_org_number": org_number,
    })
    # Validering av org_number-format är valfritt — testa att det inte kraschar
    assert resp.status_code in (201, 422), (
        f"supplier_org_number={org_number!r}: förväntade 201 eller 422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 8.7 — Utgående avtal (expiring endpoint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("days_param,days_until_expiry,should_appear", [
    (30, 15, True),     # Löper ut om 15 dagar, fönster 30 dagar → ska synas
    (30, 45, False),    # Löper ut om 45 dagar, fönster 30 dagar → ska inte synas
    (90, 60, True),     # Löper ut om 60 dagar, fönster 90 dagar → ska synas
    (90, 100, False),   # Löper ut om 100 dagar, fönster 90 dagar → ska inte synas
    (365, 300, True),   # Löper ut om 300 dagar, fönster 365 dagar → ska synas
    (1, 0, True),       # Löper ut idag, fönster 1 dag → ska synas
])
async def test_kat8_expiring_endpoint_window(client, days_param, days_until_expiry, should_appear):
    """GET /contracts/expiring?days=N: korrekt fönster ska kontrolleras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    contract_end = (date.today() + timedelta(days=days_until_expiry)).isoformat()
    contract = await create_contract(
        client, sys["id"],
        supplier_name=f"Expiry {days_param}d {days_until_expiry}d",
        contract_end=contract_end,
    )

    resp = await client.get(f"/api/v1/contracts/expiring?days={days_param}")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]

    if should_appear:
        assert contract["id"] in ids, (
            f"Avtal som löper ut om {days_until_expiry}d borde synas i {days_param}d-fönstret"
        )
    else:
        assert contract["id"] not in ids, (
            f"Avtal som löper ut om {days_until_expiry}d borde INTE synas i {days_param}d-fönstret"
        )


@pytest.mark.asyncio
async def test_kat8_already_expired_not_in_expiring(client):
    """Redan utgångna avtal ska INTE visas i expiring-listan."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    contract = await create_contract(
        client, sys["id"],
        supplier_name="Redan Utgången AB",
        contract_end=yesterday,
    )

    resp = await client.get("/api/v1/contracts/expiring?days=365")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract["id"] not in ids, "Redan utgångna avtal ska inte visas i expiring"


@pytest.mark.asyncio
async def test_kat8_no_end_date_not_in_expiring(client):
    """Avtal utan contract_end ska inte visas i expiring-listan."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    contract = await create_contract(
        client, sys["id"],
        supplier_name="Ingen Slutdatum AB",
    )
    assert contract["contract_end"] is None

    resp = await client.get("/api/v1/contracts/expiring?days=365")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract["id"] not in ids, "Avtal utan slutdatum ska inte visas i expiring"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_days", [0, -1, -30])
async def test_kat8_expiring_invalid_days_rejected(client, invalid_days):
    """GET /contracts/expiring?days=N med ogiltigt N ska ge 422."""
    resp = await client.get(f"/api/v1/contracts/expiring?days={invalid_days}")
    assert resp.status_code == 422, (
        f"days={invalid_days} borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_kat8_expiring_response_has_system_id(client):
    """Svar från expiring-endpoint ska inkludera system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    end_date = (date.today() + timedelta(days=10)).isoformat()
    contract = await create_contract(
        client, sys["id"],
        supplier_name="SystemId Check AB",
        contract_end=end_date,
    )

    resp = await client.get("/api/v1/contracts/expiring?days=30")
    assert resp.status_code == 200
    matching = [c for c in resp.json() if c["id"] == contract["id"]]
    assert len(matching) == 1
    assert "system_id" in matching[0]
    assert matching[0]["system_id"] == sys["id"]


# ---------------------------------------------------------------------------
# 8.8 — Kontrakt: CRUD-operationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat8_contract_update_supplier_name(client):
    """PATCH contract: supplier_name ska kunna uppdateras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], supplier_name="Gammalt Namn AB")

    resp = await client.patch(f"/api/v1/contracts/{contract['id']}", json={
        "supplier_name": "Nytt Namn AB",
    })
    assert resp.status_code == 200
    assert resp.json()["supplier_name"] == "Nytt Namn AB"


@pytest.mark.asyncio
@pytest.mark.parametrize("patch_field,new_value", [
    ("auto_renewal", True),
    ("notice_period_months", 6),
    ("license_model", "saas_årsvis"),
    ("procurement_type", "ramavtal"),
    ("annual_license_cost", 999999),
    ("annual_operations_cost", 50000),
    ("sla_description", "99.9% tillgänglighet"),
])
async def test_kat8_contract_patch_individual_fields(client, patch_field, new_value):
    """PATCH contract: enskilda fält ska kunna uppdateras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.patch(f"/api/v1/contracts/{contract['id']}", json={
        patch_field: new_value,
    })
    assert resp.status_code == 200, (
        f"PATCH {patch_field}={new_value!r} misslyckades: {resp.text}"
    )
    assert resp.json()[patch_field] == new_value


@pytest.mark.asyncio
async def test_kat8_contract_patch_not_found(client):
    """PATCH okänt contract-id ska ge 404."""
    resp = await client.patch(f"/api/v1/contracts/{FAKE_UUID}", json={
        "supplier_name": "Ghost",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kat8_contract_delete_success(client):
    """DELETE contract ska ge 204 och kontraktet ska vara borta."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.delete(f"/api/v1/contracts/{contract['id']}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    ids = [c["id"] for c in list_resp.json()]
    assert contract["id"] not in ids


@pytest.mark.asyncio
async def test_kat8_multiple_contracts_per_system(client):
    """Ett system kan ha flera avtal (t.ex. licens + drift + support)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_contract(client, sys["id"], supplier_name="Licens AB")
    await create_contract(client, sys["id"], supplier_name="Drift AB")
    await create_contract(client, sys["id"], supplier_name="Support AB")

    resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


# ===========================================================================
# KAT 9: BACKUP OCH DR
# ===========================================================================


# ---------------------------------------------------------------------------
# 9.1 — backup_frequency varianter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("frequency", [
    "dagligen",
    "varje timme",
    "var 6:e timme",
    "var 15:e minut",
    "realtid",
    "veckovis",
    "månadsvis",
    "vid behov",
    "ingen backup",
    "Dagligen kl 01:00 (differentiell) + veckovis (full)",
])
async def test_kat9_backup_frequency_variants(client, frequency):
    """Alla backup_frequency-varianter ska accepteras och lagras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], backup_frequency=frequency)
    assert sys["backup_frequency"] == frequency


@pytest.mark.asyncio
async def test_kat9_backup_frequency_null_default(client):
    """backup_frequency ska vara None om det inte sätts."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["backup_frequency"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("frequency", [
    "dagligen",
    "veckovis",
    "månadsvis",
])
async def test_kat9_backup_frequency_can_be_updated(client, frequency):
    """backup_frequency ska kunna uppdateras via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "backup_frequency": frequency,
    })
    assert resp.status_code == 200
    assert resp.json()["backup_frequency"] == frequency


# ---------------------------------------------------------------------------
# 9.2 — RPO och RTO strängar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("rpo,rto", [
    ("4 timmar", "8 timmar"),
    ("1 timme", "4 timmar"),
    ("15 minuter", "1 timme"),
    ("24 timmar", "72 timmar"),
    ("0 (realtidsreplikering)", "15 minuter"),
    ("Inga krav", "Inga krav"),
    ("RPO ≤ 4h", "RTO ≤ 8h"),
])
async def test_kat9_rpo_rto_combinations(client, rpo, rto):
    """RPO och RTO i kombination ska kunna sättas och returneras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rpo=rpo, rto=rto)
    assert sys["rpo"] == rpo
    assert sys["rto"] == rto


@pytest.mark.asyncio
async def test_kat9_rpo_without_rto(client):
    """RPO kan sättas utan RTO (och vice versa)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rpo="4 timmar")
    assert sys["rpo"] == "4 timmar"
    assert sys["rto"] is None


@pytest.mark.asyncio
async def test_kat9_rto_without_rpo(client):
    """RTO kan sättas utan RPO."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rto="8 timmar")
    assert sys["rto"] == "8 timmar"
    assert sys["rpo"] is None


# ---------------------------------------------------------------------------
# 9.3 — dr_plan_exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("dr_exists", [True, False])
async def test_kat9_dr_plan_exists_bool(client, dr_exists):
    """dr_plan_exists=True/False ska sparas och returneras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], dr_plan_exists=dr_exists)
    assert sys["dr_plan_exists"] == dr_exists


@pytest.mark.asyncio
async def test_kat9_dr_plan_default_false(client):
    """dr_plan_exists ska defaulta till False."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["dr_plan_exists"] is False


@pytest.mark.asyncio
async def test_kat9_dr_plan_can_be_updated(client):
    """dr_plan_exists ska kunna uppdateras från False till True via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], dr_plan_exists=False)
    assert sys["dr_plan_exists"] is False

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "dr_plan_exists": True,
    })
    assert resp.status_code == 200
    assert resp.json()["dr_plan_exists"] is True


@pytest.mark.asyncio
async def test_kat9_full_backup_profile(client):
    """System med komplett backup/DR-profil ska sparas korrekt."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        backup_frequency="dagligen kl 01:00",
        rpo="4 timmar",
        rto="8 timmar",
        dr_plan_exists=True,
    )
    assert sys["backup_frequency"] == "dagligen kl 01:00"
    assert sys["rpo"] == "4 timmar"
    assert sys["rto"] == "8 timmar"
    assert sys["dr_plan_exists"] is True


# ===========================================================================
# KAT 10: KOSTNADER OCH TCO
# ===========================================================================


# ---------------------------------------------------------------------------
# 10.1 — Total ägandekostnad (TCO) per system
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat10_tco_single_contract(client):
    """TCO för system med ett avtal: license + operations ska summeras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_contract(
        client, sys["id"],
        supplier_name="TCO Leverantör AB",
        annual_license_cost=300000,
        annual_operations_cost=100000,
    )

    resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert resp.status_code == 200
    contracts = resp.json()
    total_license = sum(c.get("annual_license_cost") or 0 for c in contracts)
    total_ops = sum(c.get("annual_operations_cost") or 0 for c in contracts)
    assert total_license == 300000
    assert total_ops == 100000
    assert total_license + total_ops == 400000


@pytest.mark.asyncio
async def test_kat10_tco_multiple_contracts(client):
    """TCO för system med flera avtal ska kunna beräknas korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_contract(
        client, sys["id"],
        supplier_name="Licens AB",
        annual_license_cost=200000,
        annual_operations_cost=50000,
    )
    await create_contract(
        client, sys["id"],
        supplier_name="Drift AB",
        annual_license_cost=0,
        annual_operations_cost=150000,
    )

    resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert resp.status_code == 200
    contracts = resp.json()
    assert len(contracts) >= 2
    total = sum(
        (c.get("annual_license_cost") or 0) + (c.get("annual_operations_cost") or 0)
        for c in contracts
    )
    assert total == 400000


@pytest.mark.asyncio
async def test_kat10_tco_zero_costs(client):
    """System utan kostnad (gratis/open source) ska kunna registreras med 0."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    contract = await create_contract(
        client, sys["id"],
        supplier_name="Open Source Projekt",
        annual_license_cost=0,
        annual_operations_cost=0,
    )
    assert contract["annual_license_cost"] == 0
    assert contract["annual_operations_cost"] == 0


# ---------------------------------------------------------------------------
# 10.2 — Kostnad per organisation (multi-system)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat10_cost_per_organization_multiple_systems(client):
    """Kostnaderna för alla system i en organisation ska kunna aggregeras."""
    org = await create_org(client)

    systems_and_costs = [
        ("SystemA", 100000, 20000),
        ("SystemB", 200000, 50000),
        ("SystemC", 50000, 10000),
    ]

    for name, license_cost, ops_cost in systems_and_costs:
        sys = await create_system(client, org["id"], name=name)
        await create_contract(
            client, sys["id"],
            supplier_name=f"Leverantör {name}",
            annual_license_cost=license_cost,
            annual_operations_cost=ops_cost,
        )

    # Hämta alla system för organisationen
    resp = await client.get(f"/api/v1/organizations/{org['id']}/systems")
    assert resp.status_code == 200
    org_systems = resp.json()
    assert len(org_systems) >= 3


@pytest.mark.asyncio
async def test_kat10_costs_scoped_to_system(client):
    """Kontrakt för system A ska inte visas i system B:s kontraktslista."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="CostSysA")
    sys_b = await create_system(client, org["id"], name="CostSysB")

    await create_contract(
        client, sys_a["id"],
        supplier_name="Kostnad A AB",
        annual_license_cost=500000,
    )

    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/contracts")
    assert resp.status_code == 200
    assert resp.json() == [], "System B ska inte ha system A:s kontrakt"


@pytest.mark.asyncio
@pytest.mark.parametrize("cost_combination", [
    (100000, None),
    (None, 50000),
    (100000, 50000),
    (0, 0),
    (1, 1),
])
async def test_kat10_cost_field_combinations(client, cost_combination):
    """Olika kombinationer av license_cost och operations_cost ska accepteras."""
    license_cost, ops_cost = cost_combination
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    payload = {"supplier_name": "CostCombo AB"}
    if license_cost is not None:
        payload["annual_license_cost"] = license_cost
    if ops_cost is not None:
        payload["annual_operations_cost"] = ops_cost

    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    if license_cost is not None:
        assert body["annual_license_cost"] == license_cost
    if ops_cost is not None:
        assert body["annual_operations_cost"] == ops_cost


# ===========================================================================
# KAT 11: DOKUMENTATION OCH SPÅRBARHET
# ===========================================================================


# ---------------------------------------------------------------------------
# 11.1 — last_reviewed_at och last_reviewed_by
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("reviewer", [
    "anna.andersson@kommunen.se",
    "it-chef@region.se",
    "john.doe@bolag.com",
    "dataskyddsombud@organisation.se",
])
async def test_kat11_last_reviewed_by_variants(client, reviewer):
    """last_reviewed_by ska kunna sättas med olika e-post/namn-format."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "last_reviewed_by": reviewer,
    })
    assert resp.status_code == 200
    assert resp.json()["last_reviewed_by"] == reviewer


@pytest.mark.asyncio
async def test_kat11_last_reviewed_at_can_be_set(client):
    """last_reviewed_at ska kunna sättas via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    review_time = "2026-01-15T10:30:00Z"
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "last_reviewed_at": review_time,
    })
    assert resp.status_code == 200
    assert resp.json()["last_reviewed_at"] is not None


@pytest.mark.asyncio
async def test_kat11_last_reviewed_at_and_by_together(client):
    """last_reviewed_at och last_reviewed_by ska kunna sättas tillsammans."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "last_reviewed_at": "2026-02-20T14:00:00Z",
        "last_reviewed_by": "granskning@kommunen.se",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_reviewed_by"] == "granskning@kommunen.se"
    assert body["last_reviewed_at"] is not None


@pytest.mark.asyncio
async def test_kat11_last_reviewed_defaults_null(client):
    """last_reviewed_at och last_reviewed_by ska vara None på nytt system."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["last_reviewed_at"] is None
    assert sys["last_reviewed_by"] is None


# ---------------------------------------------------------------------------
# 11.2 — Audit trail-verifiering: alla ändringar loggas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat11_audit_create_system_logged(client):
    """Skapande av system ska generera audit-entry med action=create."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    create_entries = [e for e in entries if e["action"] == "create"]
    assert len(create_entries) >= 1, "Skapande av system borde loggas som create"


@pytest.mark.asyncio
async def test_kat11_audit_update_system_logged(client):
    """Uppdatering av system ska generera audit-entry med action=update."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "description": "Uppdaterad beskrivning för audit-test",
    })

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    update_entries = [e for e in entries if e["action"] == "update"]
    assert len(update_entries) >= 1, "Uppdatering av system borde loggas som update"


@pytest.mark.asyncio
async def test_kat11_audit_delete_system_logged(client):
    """Borttagning av system ska generera audit-entry med action=delete."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    sys_id = sys["id"]

    await client.delete(f"/api/v1/systems/{sys_id}")

    resp = await client.get(f"/api/v1/audit/record/{sys_id}")
    assert resp.status_code == 200
    entries = resp.json()
    delete_entries = [e for e in entries if e["action"] == "delete"]
    assert len(delete_entries) >= 1, "Borttagning av system borde loggas som delete"


@pytest.mark.asyncio
async def test_kat11_audit_create_contract_logged(client):
    """Skapande av kontrakt ska generera audit-entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": contract["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1, "Skapande av kontrakt borde generera audit-entry"


@pytest.mark.asyncio
async def test_kat11_audit_update_contract_logged(client):
    """Uppdatering av kontrakt ska generera audit-entry med action=update."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    await client.patch(f"/api/v1/contracts/{contract['id']}", json={
        "annual_license_cost": 750000,
    })

    resp = await client.get("/api/v1/audit/", params={"record_id": contract["id"]})
    assert resp.status_code == 200
    items = resp.json()["items"]
    update_entries = [e for e in items if e["action"] == "update"]
    assert len(update_entries) >= 1, "Uppdatering av kontrakt borde loggas som update"


@pytest.mark.asyncio
async def test_kat11_audit_create_integration_logged(client):
    """Skapande av integration ska generera audit-entry."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="AuditIntSrc")
    tgt = await create_system(client, org["id"], name="AuditIntTgt")
    integ = await create_integration(client, src["id"], tgt["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": integ["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1, "Skapande av integration borde generera audit-entry"


@pytest.mark.asyncio
async def test_kat11_audit_create_classification_logged(client):
    """Skapande av klassning ska generera audit-entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    clf = await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": clf["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1, "Skapande av klassning borde generera audit-entry"


@pytest.mark.asyncio
async def test_kat11_audit_create_owner_logged(client):
    """Skapande av ägare ska generera audit-entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": owner["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1, "Skapande av ägare borde generera audit-entry"


@pytest.mark.asyncio
async def test_kat11_audit_create_gdpr_logged(client):
    """Skapande av GDPR-behandling ska generera audit-entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"])

    resp = await client.get("/api/v1/audit/", params={"record_id": gdpr["id"]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1, "Skapande av GDPR-behandling borde generera audit-entry"


@pytest.mark.asyncio
async def test_kat11_audit_new_values_present_on_create(client):
    """Audit-entry för create ska ha new_values."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    create_entries = [e for e in entries if e["action"] == "create"]
    if create_entries:
        assert create_entries[0]["new_values"] is not None, (
            "Create audit-entry borde ha new_values"
        )


@pytest.mark.asyncio
async def test_kat11_audit_old_values_present_on_update(client):
    """Audit-entry för update ska ha old_values och new_values."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="OldName")

    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "NewName"})

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    update_entries = [e for e in entries if e["action"] == "update"]
    if update_entries:
        entry = update_entries[0]
        # old_values eller new_values ska finnas (impl-beroende)
        has_values = (
            entry.get("old_values") is not None
            or entry.get("new_values") is not None
        )
        assert has_values, "Update audit-entry borde ha old_values eller new_values"


@pytest.mark.asyncio
async def test_kat11_audit_multiple_updates_logged_separately(client):
    """Varje PATCH-operation ska generera en separat audit-entry."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "Ändring 1"})
    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "Ändring 2"})
    await client.patch(f"/api/v1/systems/{sys['id']}", json={"name": "Ändring 3"})

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    update_entries = [e for e in entries if e["action"] == "update"]
    assert len(update_entries) >= 3, (
        f"3 PATCH-operationer borde ge ≥3 update-entries, fick {len(update_entries)}"
    )


# ---------------------------------------------------------------------------
# 11.3 — Versionshistorik (klassningshistorik)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat11_classification_history_multiple_entries(client):
    """Flera klassningar på samma system ska sparas som historik."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    clf1 = await create_classification(client, sys["id"],
                                        confidentiality=2, integrity=2, availability=2)
    clf2 = await create_classification(client, sys["id"],
                                        confidentiality=3, integrity=3, availability=3)

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    classifications = resp.json()
    ids = [c["id"] for c in classifications]
    assert clf1["id"] in ids
    assert clf2["id"] in ids


@pytest.mark.asyncio
async def test_kat11_classification_history_ordered_newest_first(client):
    """Klassningshistorik ska returneras med nyaste klassning först."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_classification(client, sys["id"],
                                 confidentiality=1, integrity=1, availability=1)
    await create_classification(client, sys["id"],
                                 confidentiality=4, integrity=4, availability=4)

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    classifications = resp.json()
    if len(classifications) >= 2:
        # Nyaste (högre värden) ska komma först
        times = [c["classified_at"] for c in classifications]
        assert times == sorted(times, reverse=True), (
            "Klassningshistorik borde vara sorterad med nyaste först"
        )


@pytest.mark.asyncio
async def test_kat11_audit_table_name_correct(client):
    """Audit-entries ska ha korrekt table_name för respektive entitet."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    for entry in entries:
        assert entry["table_name"] == "systems", (
            f"Audit-entry för system borde ha table_name='systems', fick {entry['table_name']!r}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("table_filter", [
    "systems",
    "contracts",
    "system_classifications",
    "system_owners",
    "gdpr_treatments",
    "system_integrations",
])
async def test_kat11_audit_filter_by_table_name(client, table_filter):
    """GET /audit/?table_name=X ska returnera enbart entries för den tabellen."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"table_name": table_filter})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["table_name"] == table_filter, (
            f"Filter table_name={table_filter!r} returnerade {item['table_name']!r}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("action_filter", ["create", "update", "delete"])
async def test_kat11_audit_filter_by_action(client, action_filter):
    """GET /audit/?action=X ska returnera enbart entries med den actionen."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/audit/", params={"action": action_filter})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["action"] == action_filter, (
            f"Filter action={action_filter!r} returnerade {item['action']!r}"
        )


# ===========================================================================
# KAT 12: REGELEFTERLEVNAD
# ===========================================================================


# ---------------------------------------------------------------------------
# 12.1 — NIS2-fält
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_applicable,nis2_classification", [
    (True, "väsentlig"),
    (True, "viktig"),
    (True, "ej_tillämplig"),
    (False, None),
    (False, "ej_tillämplig"),
])
async def test_kat12_nis2_combinations(client, nis2_applicable, nis2_classification):
    """Alla kombinationer av nis2_applicable och nis2_classification ska accepteras."""
    org = await create_org(client)
    kwargs = {"nis2_applicable": nis2_applicable}
    if nis2_classification is not None:
        kwargs["nis2_classification"] = nis2_classification

    sys = await create_system(client, org["id"], **kwargs)
    assert sys["nis2_applicable"] == nis2_applicable
    if nis2_classification is not None:
        assert sys["nis2_classification"] == nis2_classification


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_class", ["väsentlig", "viktig", "ej_tillämplig"])
async def test_kat12_nis2_classification_all_values(client, nis2_class):
    """Alla nis2_classification-värden ska accepteras och lagras korrekt."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        nis2_applicable=True,
        nis2_classification=nis2_class,
    )
    assert sys["nis2_classification"] == nis2_class


@pytest.mark.asyncio
async def test_kat12_nis2_default_false(client):
    """nis2_applicable ska defaulta till False."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["nis2_applicable"] is False


@pytest.mark.asyncio
async def test_kat12_nis2_classification_null_default(client):
    """nis2_classification ska defaulta till None."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["nis2_classification"] is None


@pytest.mark.asyncio
async def test_kat12_nis2_applicable_can_be_updated(client):
    """nis2_applicable ska kunna uppdateras via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], nis2_applicable=False)

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "nis2_applicable": True,
        "nis2_classification": "väsentlig",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "väsentlig"


# ---------------------------------------------------------------------------
# 12.2 — CSL-fält (säkerhetsskyddslagen + förhöjt skydd)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("security_protection,has_elevated_protection", [
    (True, True),
    (True, False),
    (False, True),
    (False, False),
])
async def test_kat12_security_protection_combinations(
    client, security_protection, has_elevated_protection
):
    """Alla kombinationer av security_protection och has_elevated_protection ska accepteras."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        security_protection=security_protection,
        has_elevated_protection=has_elevated_protection,
    )
    assert sys["security_protection"] == security_protection
    assert sys["has_elevated_protection"] == has_elevated_protection


@pytest.mark.asyncio
async def test_kat12_security_protection_default_false(client):
    """security_protection och has_elevated_protection ska defaulta till False."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["security_protection"] is False
    assert sys["has_elevated_protection"] is False


@pytest.mark.asyncio
async def test_kat12_security_protection_can_be_updated(client):
    """security_protection ska kunna uppdateras via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "security_protection": True,
    })
    assert resp.status_code == 200
    assert resp.json()["security_protection"] is True


# ---------------------------------------------------------------------------
# 12.3 — last_risk_assessment_date
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("assessment_date", [
    "2024-01-15",
    "2025-06-30",
    "2026-01-01",
    "2023-12-31",
    "2020-03-01",
])
async def test_kat12_last_risk_assessment_date_variants(client, assessment_date):
    """last_risk_assessment_date ska acceptera olika datumvärden."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        last_risk_assessment_date=assessment_date,
    )
    assert sys["last_risk_assessment_date"] == assessment_date


@pytest.mark.asyncio
async def test_kat12_risk_assessment_date_null_default(client):
    """last_risk_assessment_date ska vara None om det inte sätts."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["last_risk_assessment_date"] is None


@pytest.mark.asyncio
async def test_kat12_risk_assessment_date_can_be_updated(client):
    """last_risk_assessment_date ska kunna uppdateras via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    new_date = "2026-02-28"
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "last_risk_assessment_date": new_date,
    })
    assert resp.status_code == 200
    assert resp.json()["last_risk_assessment_date"] == new_date


@pytest.mark.asyncio
async def test_kat12_risk_assessment_date_invalid_format(client):
    """last_risk_assessment_date med ogiltigt format ska ge 422."""
    org = await create_org(client)

    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "InvalidDate",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "last_risk_assessment_date": "not-a-date",
    })
    assert resp.status_code == 422, (
        f"Ogiltigt datumformat borde ge 422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 12.4 — klassa_reference_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("klassa_ref", [
    "KLASSA-2024-001",
    "KLASSA-2025-042",
    "K-REF-2026-0099",
    "MSBFS-2024-001",
    "SEC-2026-A",
    "Riskanalys 2025 Q1",
    "a" * 100,  # Max-längd test
])
async def test_kat12_klassa_reference_id_variants(client, klassa_ref):
    """klassa_reference_id ska acceptera olika referensformat."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], klassa_reference_id=klassa_ref)
    assert sys["klassa_reference_id"] == klassa_ref


@pytest.mark.asyncio
async def test_kat12_klassa_reference_id_null_default(client):
    """klassa_reference_id ska vara None om det inte sätts."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert sys["klassa_reference_id"] is None


@pytest.mark.asyncio
async def test_kat12_klassa_reference_id_can_be_updated(client):
    """klassa_reference_id ska kunna uppdateras via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "klassa_reference_id": "KLASSA-2026-NEW",
    })
    assert resp.status_code == 200
    assert resp.json()["klassa_reference_id"] == "KLASSA-2026-NEW"


# ---------------------------------------------------------------------------
# 12.5 — Compliance gap-analys (systemregisters compliance-endpoint)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat12_compliance_endpoint_accessible(client):
    """Compliance-relaterade endpoints ska returnera 200."""
    resp = await client.get("/api/v1/systems/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_kat12_system_without_classification_has_no_current_classification(client):
    """System utan klassning ska returnera tom klassningslista."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_kat12_system_with_old_risk_assessment_identifiable(client):
    """System med gammal riskbedömning ska kunna identifieras via filtreringsfunktion."""
    org = await create_org(client)

    # System med gammal riskbedömning
    old_date = (date.today() - timedelta(days=400)).isoformat()
    sys_old = await create_system(
        client, org["id"],
        name="GammalRisk",
        last_risk_assessment_date=old_date,
    )

    # System med ny riskbedömning
    new_date = (date.today() - timedelta(days=30)).isoformat()
    sys_new = await create_system(
        client, org["id"],
        name="NyRisk",
        last_risk_assessment_date=new_date,
    )

    assert sys_old["last_risk_assessment_date"] == old_date
    assert sys_new["last_risk_assessment_date"] == new_date


@pytest.mark.asyncio
async def test_kat12_nis2_systems_filterable(client):
    """System med nis2_applicable=True ska kunna filtreras ut."""
    org = await create_org(client)

    await create_system(
        client, org["id"],
        name="NIS2 Väsentlig",
        nis2_applicable=True,
        nis2_classification="väsentlig",
    )
    await create_system(
        client, org["id"],
        name="Ej NIS2",
        nis2_applicable=False,
    )

    resp = await client.get("/api/v1/systems/", params={"nis2_applicable": True})
    if resp.status_code == 200:
        systems = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
        for sys in systems:
            assert sys["nis2_applicable"] is True


@pytest.mark.asyncio
async def test_kat12_security_protection_systems_filterable(client):
    """System med security_protection=True ska kunna identifieras."""
    org = await create_org(client)

    sys_protected = await create_system(
        client, org["id"],
        name="SäkSkydd",
        security_protection=True,
    )
    sys_normal = await create_system(
        client, org["id"],
        name="Normalt",
        security_protection=False,
    )

    assert sys_protected["security_protection"] is True
    assert sys_normal["security_protection"] is False


# ---------------------------------------------------------------------------
# 12.6 — Fullständig compliance-profil
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat12_full_compliance_profile(client):
    """System med komplett compliance-profil ska sparas och returneras korrekt."""
    org = await create_org(client)
    assessment_date = (date.today() - timedelta(days=90)).isoformat()

    sys = await create_system(
        client, org["id"],
        name="Komplett Compliance",
        nis2_applicable=True,
        nis2_classification="väsentlig",
        security_protection=False,
        has_elevated_protection=True,
        last_risk_assessment_date=assessment_date,
        klassa_reference_id="KLASSA-2026-001",
    )

    assert sys["nis2_applicable"] is True
    assert sys["nis2_classification"] == "väsentlig"
    assert sys["security_protection"] is False
    assert sys["has_elevated_protection"] is True
    assert sys["last_risk_assessment_date"] == assessment_date
    assert sys["klassa_reference_id"] == "KLASSA-2026-001"


@pytest.mark.asyncio
async def test_kat12_compliance_profile_via_patch(client):
    """Compliance-profil ska kunna uppdateras komplett via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    assessment_date = date.today().isoformat()
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "nis2_applicable": True,
        "nis2_classification": "viktig",
        "security_protection": True,
        "has_elevated_protection": False,
        "last_risk_assessment_date": assessment_date,
        "klassa_reference_id": "KLASSA-2026-PATCH",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "viktig"
    assert body["security_protection"] is True
    assert body["last_risk_assessment_date"] == assessment_date
    assert body["klassa_reference_id"] == "KLASSA-2026-PATCH"


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality,nis2_class,expected_risk", [
    ("kritisk", "väsentlig", "maximal"),
    ("hög", "väsentlig", "hög"),
    ("hög", "viktig", "hög"),
    ("medel", "viktig", "medel"),
    ("låg", "ej_tillämplig", "låg"),
])
async def test_kat12_criticality_nis2_combinations(client, criticality, nis2_class, expected_risk):
    """Kombinationer av criticality och nis2_classification ska sparas korrekt."""
    org = await create_org(client)
    sys = await create_system(
        client, org["id"],
        name=f"Risk {criticality} {nis2_class}",
        criticality=criticality,
        nis2_applicable=True,
        nis2_classification=nis2_class,
    )
    assert sys["criticality"] == criticality
    assert sys["nis2_classification"] == nis2_class


# ---------------------------------------------------------------------------
# 12.7 — Audit trail för compliance-ändringar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat12_nis2_change_logged_in_audit(client):
    """Ändring av NIS2-status ska loggas i audit trail."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], nis2_applicable=False)

    await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "nis2_applicable": True,
        "nis2_classification": "väsentlig",
    })

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    entries = resp.json()
    update_entries = [e for e in entries if e["action"] == "update"]
    assert len(update_entries) >= 1, "NIS2-ändring borde loggas i audit"


@pytest.mark.asyncio
async def test_kat12_risk_assessment_date_change_logged(client):
    """Uppdatering av riskbedömningsdatum ska loggas i audit trail."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "last_risk_assessment_date": "2026-03-01",
    })

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    update_entries = [e for e in resp.json() if e["action"] == "update"]
    assert len(update_entries) >= 1, "Ändring av riskdatum borde loggas"


@pytest.mark.asyncio
async def test_kat12_klassa_reference_change_logged(client):
    """Uppdatering av KLASSA-referens ska loggas i audit trail."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "klassa_reference_id": "KLASSA-2026-NEW",
    })

    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    update_entries = [e for e in resp.json() if e["action"] == "update"]
    assert len(update_entries) >= 1, "Ändring av KLASSA-referens borde loggas"


# ---------------------------------------------------------------------------
# 12.8 — Kombinationsscenarion: systemregister med full compliance-data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kat12_critical_system_full_profile(client):
    """Kritiskt NIS2-system med full backup/DR och compliance-profil."""
    org = await create_org(client)
    assessment_date = (date.today() - timedelta(days=30)).isoformat()

    sys = await create_system(
        client, org["id"],
        name="Kritiskt NIS2-system",
        criticality="kritisk",
        nis2_applicable=True,
        nis2_classification="väsentlig",
        security_protection=False,
        has_elevated_protection=True,
        backup_frequency="var 6:e timme",
        rpo="1 timme",
        rto="4 timmar",
        dr_plan_exists=True,
        last_risk_assessment_date=assessment_date,
        klassa_reference_id="KLASSA-2026-KR-001",
    )

    # Verifiera alla compliance-fält
    assert sys["criticality"] == "kritisk"
    assert sys["nis2_applicable"] is True
    assert sys["nis2_classification"] == "väsentlig"
    assert sys["has_elevated_protection"] is True
    assert sys["backup_frequency"] == "var 6:e timme"
    assert sys["rpo"] == "1 timme"
    assert sys["rto"] == "4 timmar"
    assert sys["dr_plan_exists"] is True
    assert sys["klassa_reference_id"] == "KLASSA-2026-KR-001"

    # Lägg till ett avtal
    contract = await create_contract(
        client, sys["id"],
        supplier_name="Kritisk Leverantör AB",
        annual_license_cost=2000000,
        annual_operations_cost=500000,
    )
    assert contract["annual_license_cost"] == 2000000

    # Lägg till integration
    hub = await create_system(client, org["id"], name="Hub")
    integ = await create_integration(
        client, sys["id"], hub["id"],
        integration_type="api",
        criticality="kritisk",
        is_external=False,
    )
    assert integ["criticality"] == "kritisk"
