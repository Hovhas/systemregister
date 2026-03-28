"""
End-to-end arbetsflödestester — hela systemet.

Testar sammanhängande flöden där flera API-anrop tillsammans utgör ett
affärsmässigt scenario. Varje testfall verifierar att systemet uppträder
korrekt som helhet, inte bara att enskilda endpoints fungerar.

Kategorier:
- Livscykelflöden (statusövergångar, hela livscykeln)
- Registreringsflöden (inventering, batchimport)
- GDPR-flöden (PU-behandling, DPIA, tredjelandsöverföring)
- NIS2-complianceflöden (identifiering, klassificering, rapport)
- Kontraktsflöden (förfall, förnyelse)
- Integrationsflöden (beroendekartläggning)
- Import/export roundtrip
- Rapportflöden
- Felhanteringsflöden
"""

import csv
import io
import json
import pytest
from datetime import date, timedelta

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_integration,
    create_gdpr_treatment,
    create_contract,
    create_full_system,
)


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------


def make_json_file(rows: list[dict]) -> tuple[bytes, str, str]:
    content = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    return content, "systems.json", "application/json"


def make_csv_file(rows: list[dict]) -> tuple[bytes, str, str]:
    if not rows:
        return b"", "systems.csv", "text/csv"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8"), "systems.csv", "text/csv"


async def post_import(client, org_id: str, content: bytes, filename: str, content_type: str):
    return await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org_id},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


# ---------------------------------------------------------------------------
# Livscykelflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifecycle_full_flow_planerad_to_avvecklad(client):
    """Komplett livscykel: Planerad -> Under införande -> I drift -> Under avveckling -> Avvecklad."""
    org = await create_org(client, name="Livscykel Org")

    sys = await create_system(client, org["id"],
                               name="Livscykelsystem",
                               lifecycle_status="planerad")
    assert sys["lifecycle_status"] == "planerad"

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "under_inforande"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "under_inforande"

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "i_drift"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "i_drift"

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "under_avveckling"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "under_avveckling"

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "avvecklad"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "avvecklad"


@pytest.mark.asyncio
async def test_lifecycle_status_transition_planerad_to_i_drift(client):
    """Direktövergång Planerad -> I drift ska vara möjlig."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="planerad")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "i_drift"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "i_drift"


@pytest.mark.asyncio
async def test_lifecycle_status_transition_under_inforande_to_i_drift(client):
    """Under införande -> I drift ska vara möjlig."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="under_inforande")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "i_drift"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "i_drift"


@pytest.mark.asyncio
async def test_lifecycle_status_transition_i_drift_to_under_avveckling(client):
    """I drift -> Under avveckling ska vara möjlig."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="i_drift")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "under_avveckling"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "under_avveckling"


@pytest.mark.asyncio
async def test_lifecycle_status_transition_avveckling_to_avvecklad(client):
    """Under avveckling -> Avvecklad ska vara möjlig."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="under_avveckling")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": "avvecklad"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "avvecklad"


@pytest.mark.asyncio
async def test_lifecycle_avvecklad_system_still_readable(client):
    """Avvecklat system ska fortfarande vara läsbart i API."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="avvecklad")

    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == "avvecklad"


@pytest.mark.asyncio
async def test_lifecycle_filter_avveckladda_system(client):
    """Filtrering på avvecklad ger bara avvecklade system."""
    org = await create_org(client)
    drift = await create_system(client, org["id"], name="I Drift", lifecycle_status="i_drift")
    avvecklad = await create_system(client, org["id"], name="Avvecklad", lifecycle_status="avvecklad")

    resp = await client.get("/api/v1/systems/", params={"lifecycle_status": "avvecklad", "organization_id": org["id"]})
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert avvecklad["id"] in ids
    assert drift["id"] not in ids


@pytest.mark.asyncio
async def test_lifecycle_full_system_with_all_entities(client):
    """System med alla relaterade entiteter genom hela livscykeln."""
    org = await create_org(client, name="Full Livscykel Org")

    sys = await create_system(client, org["id"],
                               name="Komplett System",
                               lifecycle_status="planerad",
                               treats_personal_data=True,
                               nis2_applicable=True,
                               nis2_classification="väsentlig")

    await create_classification(client, sys["id"], confidentiality=3, integrity=3, availability=3)
    await create_owner(client, sys["id"], org["id"], role="systemägare", name="Systemägare Person")
    await create_owner(client, sys["id"], org["id"], role="informationsägare", name="Informationsägare Person")
    await create_gdpr_treatment(client, sys["id"],
                                 data_categories=["vanliga", "känsliga"],
                                 legal_basis="Rättslig förpliktelse (art. 6.1 c)")
    await create_contract(client, sys["id"],
                          supplier_name="Leverantör AB",
                          contract_end=str(date.today() + timedelta(days=365)))

    for status in ["under_inforande", "i_drift", "under_avveckling", "avvecklad"]:
        resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": status})
        assert resp.status_code == 200, f"Statusövergång till {status} misslyckades"

    final = await client.get(f"/api/v1/systems/{sys['id']}")
    assert final.json()["lifecycle_status"] == "avvecklad"

    cls_resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert len(cls_resp.json()) >= 1

    owner_resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert len(owner_resp.json()) >= 2


@pytest.mark.asyncio
async def test_lifecycle_deployment_date_set_when_going_to_drift(client):
    """deployment_date kan sättas i samband med statusövergång till i_drift."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="planerad")
    deployment = date.today().isoformat()

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "lifecycle_status": "i_drift",
        "deployment_date": deployment,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["lifecycle_status"] == "i_drift"
    assert body["deployment_date"] == deployment


@pytest.mark.asyncio
async def test_lifecycle_planned_decommission_date_on_avveckling(client):
    """planned_decommission_date kan sättas vid statusövergång till under_avveckling."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status="i_drift")
    decommission = (date.today() + timedelta(days=180)).isoformat()

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "lifecycle_status": "under_avveckling",
        "planned_decommission_date": decommission,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["lifecycle_status"] == "under_avveckling"
    assert body["planned_decommission_date"] == decommission


# ---------------------------------------------------------------------------
# Registreringsflöden (Fas 1: grundinventering)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registration_flow_org_system_classify_owner(client):
    """Registreringsflöde: Org -> System -> Klassificera (K/R/T) -> Tilldela ägare."""
    org = await create_org(client, name="Inventerings Kommun", org_number="212000-0001")
    assert org["name"] == "Inventerings Kommun"

    sys = await create_system(client, org["id"],
                               name="Procapita",
                               description="Verksamhetssystem för omsorg",
                               system_category="verksamhetssystem",
                               criticality="hög")
    assert sys["organization_id"] == org["id"]

    cls = await create_classification(client, sys["id"],
                                       confidentiality=3,
                                       integrity=3,
                                       availability=3,
                                       traceability=2,
                                       classified_by="it@kommun.se")
    assert cls["confidentiality"] == 3
    assert cls["integrity"] == 3
    assert cls["availability"] == 3

    owner = await create_owner(client, sys["id"], org["id"],
                                role="systemägare",
                                name="Anna Andersson",
                                email="anna@kommun.se")
    assert owner["role"] == "systemägare"

    verify = await client.get(f"/api/v1/systems/{sys['id']}")
    assert verify.status_code == 200
    body = verify.json()
    assert body["criticality"] == "hög"


@pytest.mark.asyncio
async def test_registration_flow_verify_compliance_after_full_registration(client):
    """Efter fullständig registrering ska system uppfylla grundläggande krav."""
    org = await create_org(client)
    sys = await create_full_system(client, org["id"],
                                    name="Komplett Registrerat System",
                                    treats_personal_data=True,
                                    nis2_applicable=True)

    cls_resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert len(cls_resp.json()) >= 1, "Klassning saknas"

    owner_resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert len(owner_resp.json()) >= 1, "Ägare saknas"

    gdpr_resp = await client.get(f"/api/v1/systems/{sys['id']}/gdpr")
    assert len(gdpr_resp.json()) >= 1, "GDPR-behandling saknas"

    contract_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert len(contract_resp.json()) >= 1, "Kontrakt saknas"


@pytest.mark.asyncio
async def test_registration_batch_50_systems(client):
    """Batchregistrering: importera 50 system via JSON-import."""
    org = await create_org(client, name="Batch Import Org")
    rows = [
        {
            "name": f"Batchsystem {i:02d}",
            "description": f"System nummer {i}",
            "system_category": "verksamhetssystem",
            "criticality": "medel",
        }
        for i in range(50)
    ]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Import misslyckades: {resp.text}"
    body = resp.json()
    assert body["imported"] == 50, f"Förväntade 50 importerade, fick {body['imported']}"
    assert body["errors"] == []

    list_resp = await client.get("/api/v1/systems/",
                                  params={"organization_id": org["id"], "limit": 100})
    assert list_resp.json()["total"] >= 50


@pytest.mark.asyncio
async def test_registration_import_verify_export_compare_json(client):
    """Import -> Verifiera -> Exportera -> Jämför JSON roundtrip."""
    org = await create_org(client, name="Roundtrip Org")
    rows = [
        {"name": "Roundtrip System A", "description": "Beskrivning A", "system_category": "infrastruktur"},
        {"name": "Roundtrip System B", "description": "Beskrivning B", "system_category": "stödsystem"},
    ]
    content, filename, content_type = make_json_file(rows)
    import_resp = await post_import(client, org["id"], content, filename, content_type)
    assert import_resp.json()["imported"] == 2

    list_resp = await client.get("/api/v1/systems/", params={"organization_id": org["id"]})
    imported_names = {s["name"] for s in list_resp.json()["items"]}
    assert "Roundtrip System A" in imported_names
    assert "Roundtrip System B" in imported_names

    export_resp = await client.get("/api/v1/export/systems.json")
    assert export_resp.status_code == 200
    exported = export_resp.json()
    exported_names = {s["name"] for s in exported}
    assert "Roundtrip System A" in exported_names
    assert "Roundtrip System B" in exported_names


@pytest.mark.asyncio
async def test_registration_import_verify_export_compare_csv(client):
    """Import CSV -> Verifiera -> Exportera CSV -> Verifiera roundtrip."""
    org = await create_org(client, name="CSV Roundtrip Org")
    rows = [
        {"name": "CSV Roundtrip X", "description": "Test X", "system_category": "plattform"},
        {"name": "CSV Roundtrip Y", "description": "Test Y", "system_category": "iot"},
    ]
    content, filename, content_type = make_csv_file(rows)
    import_resp = await post_import(client, org["id"], content, filename, content_type)
    assert import_resp.status_code == 200
    assert import_resp.json()["imported"] == 2

    export_resp = await client.get("/api/v1/export/systems.csv")
    assert export_resp.status_code == 200

    text = export_resp.text
    assert "CSV Roundtrip X" in text or "CSV Roundtrip Y" in text


@pytest.mark.asyncio
async def test_registration_multiple_orgs_independent_inventories(client):
    """Flera org kan genomföra inventering oberoende av varandra."""
    org_a = await create_org(client, name="Org Alpha")
    org_b = await create_org(client, name="Org Beta")

    for i in range(3):
        await create_system(client, org_a["id"], name=f"Alpha System {i}")
        await create_system(client, org_b["id"], name=f"Beta System {i}")

    resp_a = await client.get("/api/v1/systems/", params={"organization_id": org_a["id"]})
    resp_b = await client.get("/api/v1/systems/", params={"organization_id": org_b["id"]})

    ids_a = {s["id"] for s in resp_a.json()["items"]}
    ids_b = {s["id"] for s in resp_b.json()["items"]}
    assert not ids_a & ids_b, "Inga system ska delas mellan org"


# ---------------------------------------------------------------------------
# GDPR-flöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_flow_flag_personal_data_create_treatment(client):
    """GDPR-flöde: skapa system -> flagga PU -> skapa GDPR-behandling."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name="Omsorgssystem",
                               treats_personal_data=True)
    assert sys["treats_personal_data"] is True

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga", "känsliga"],
                                        legal_basis="Rättslig förpliktelse (art. 6.1 c)",
                                        categories_of_data_subjects="Brukare, anhöriga",
                                        retention_policy="5 år efter avslutat ärende")
    assert gdpr["data_categories"] is not None
    assert gdpr["legal_basis"] == "Rättslig förpliktelse (art. 6.1 c)"


@pytest.mark.asyncio
async def test_gdpr_flow_ropa_reference(client):
    """GDPR-flöde: koppla GDPR-behandling till ROPA-referens."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        ropa_reference_id="ROPA-2025-042",
                                        data_categories=["vanliga"])
    assert gdpr["ropa_reference_id"] == "ROPA-2025-042"

    gdpr_resp = await client.get(f"/api/v1/systems/{sys['id']}/gdpr")
    assert gdpr_resp.status_code == 200
    treatments = gdpr_resp.json()
    assert any(t["ropa_reference_id"] == "ROPA-2025-042" for t in treatments)


@pytest.mark.asyncio
async def test_gdpr_flow_pub_agreement(client):
    """GDPR-flöde: dokumentera PuB-avtal med leverantör."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        data_processor="CGI Sverige AB",
                                        processor_agreement_status="ja")
    assert gdpr["data_processor"] == "CGI Sverige AB"
    assert gdpr["processor_agreement_status"] == "ja"


@pytest.mark.asyncio
async def test_gdpr_flow_pub_agreement_under_framtagande(client):
    """GDPR-flöde: PuB-avtal under framtagande dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        data_processor="Leverantör AB",
                                        processor_agreement_status="under_framtagande")
    assert gdpr["processor_agreement_status"] == "under_framtagande"


@pytest.mark.asyncio
async def test_gdpr_flow_third_country_transfer(client):
    """GDPR-flöde: tredjelandsöverföring flaggas och skyddsmekanism dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               treats_personal_data=True,
                               third_country_transfer=True,
                               data_location_country="USA")
    assert sys["third_country_transfer"] is True
    assert sys["data_location_country"] == "USA"

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        third_country_transfer_details="SCCs enligt art. 46.2 c GDPR")
    assert gdpr["third_country_transfer_details"] == "SCCs enligt art. 46.2 c GDPR"


@pytest.mark.asyncio
async def test_gdpr_flow_third_country_standard_clauses(client):
    """Tredjelandsöverföring: dokumentera standardavtalsklausuler."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               treats_personal_data=True,
                               third_country_transfer=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        third_country_transfer_details="EU-kommissionens SCC 2021")
    assert "SCC" in gdpr.get("third_country_transfer_details", "")


@pytest.mark.asyncio
async def test_gdpr_flow_dpia_full(client):
    """DPIA-flöde: genomför och dokumentera konsekvensbedömning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               treats_personal_data=True,
                               treats_sensitive_data=True)

    dpia_date = (date.today() - timedelta(days=30)).isoformat()
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["känsliga", "personnummer"],
                                        dpia_conducted=True,
                                        dpia_date=dpia_date,
                                        dpia_link="https://intern.exempel.se/dpia-2025-001.pdf",
                                        legal_basis="Allmänt intresse (art. 6.1 e)")
    assert gdpr["dpia_conducted"] is True
    assert gdpr["dpia_date"] == dpia_date
    assert "dpia-2025-001" in gdpr.get("dpia_link", "")


@pytest.mark.asyncio
async def test_gdpr_flow_dpia_not_conducted_documented(client):
    """DPIA-flöde: dokumentera att DPIA ännu inte genomförts."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        dpia_conducted=False)
    assert gdpr["dpia_conducted"] is False


@pytest.mark.asyncio
async def test_gdpr_flow_multiple_legal_bases(client):
    """GDPR: olika rättsliga grunder kan dokumenteras."""
    org = await create_org(client)
    legal_bases = [
        "Rättslig förpliktelse (art. 6.1 c)",
        "Allmänt intresse (art. 6.1 e)",
        "Samtycke (art. 6.1 a)",
        "Avtal (art. 6.1 b)",
    ]
    for basis in legal_bases:
        sys = await create_system(client, org["id"], treats_personal_data=True)
        gdpr = await create_gdpr_treatment(client, sys["id"],
                                            data_categories=["vanliga"],
                                            legal_basis=basis)
        assert gdpr["legal_basis"] == basis


@pytest.mark.asyncio
async def test_gdpr_flow_sub_processors(client):
    """GDPR-flöde: dokumentera underbiträden."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        data_processor="Primär Leverantör AB",
                                        sub_processors=["Underbiträde 1", "Underbiträde 2"])
    assert gdpr.get("sub_processors") is not None


@pytest.mark.asyncio
async def test_gdpr_flow_system_without_personal_data_no_treatment_needed(client):
    """System utan personuppgifter behöver inte GDPR-behandling."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name="Infrastruktursystem",
                               treats_personal_data=False,
                               system_category="infrastruktur")
    assert sys["treats_personal_data"] is False

    gdpr_resp = await client.get(f"/api/v1/systems/{sys['id']}/gdpr")
    assert gdpr_resp.status_code == 200
    assert gdpr_resp.json() == []


@pytest.mark.asyncio
async def test_gdpr_flow_patch_system_to_flag_personal_data(client):
    """Befintligt system kan flaggas för personuppgifter via PATCH."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=False)

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"treats_personal_data": True})
    assert resp.status_code == 200
    assert resp.json()["treats_personal_data"] is True


# ---------------------------------------------------------------------------
# NIS2-complianceflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_flow_identify_and_classify(client):
    """NIS2-flöde: identifiera NIS2-system -> klassificera -> riskbedöm."""
    org = await create_org(client)

    sys = await create_system(client, org["id"],
                               name="Kritisk Infrastruktur",
                               system_category="infrastruktur",
                               criticality="kritisk")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "nis2_applicable": True,
        "nis2_classification": "väsentlig",
        "last_risk_assessment_date": "2025-06-01",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "väsentlig"
    assert body["last_risk_assessment_date"] == "2025-06-01"


@pytest.mark.asyncio
async def test_nis2_flow_classify_all_levels(client):
    """NIS2: alla klassificeringsnivåer kan sättas."""
    org = await create_org(client)
    for classification in ["väsentlig", "viktig", "ej_tillämplig"]:
        sys = await create_system(client, org["id"],
                                   nis2_applicable=True,
                                   nis2_classification=classification)
        assert sys["nis2_classification"] == classification


@pytest.mark.asyncio
async def test_nis2_flow_generate_report(client):
    """NIS2-complianceflöde: generera NIS2-rapport med korrekt data."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name="NIS2 Rapportsystem",
                               nis2_applicable=True,
                               nis2_classification="väsentlig",
                               criticality="kritisk",
                               last_risk_assessment_date="2025-01-15")
    await create_classification(client, sys["id"], confidentiality=3, integrity=3, availability=3)
    await create_owner(client, sys["id"], org["id"], name="NIS2 Ägare")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    assert "summary" in body
    assert "systems" in body
    assert "generated_at" in body

    sys_ids = [s["id"] for s in body["systems"]]
    assert sys["id"] in sys_ids, "NIS2-system ska ingå i rapporten"

    entry = next(s for s in body["systems"] if s["id"] == sys["id"])
    assert entry["nis2_classification"] == "väsentlig"
    assert entry["criticality"] == "kritisk"


@pytest.mark.asyncio
async def test_nis2_flow_report_excludes_non_nis2(client):
    """NIS2-rapport: system utan NIS2 ska inte ingå."""
    org = await create_org(client)
    non_nis2 = await create_system(client, org["id"],
                                    name="Ej NIS2 System",
                                    nis2_applicable=False)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["systems"]]
    assert non_nis2["id"] not in ids


@pytest.mark.asyncio
async def test_nis2_flow_compliance_gap_report(client):
    """NIS2: compliance gap-rapport identifierar system som saknar krav."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         name="Gap System",
                         nis2_applicable=True,
                         nis2_classification="väsentlig",
                         criticality="kritisk")

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    body = resp.json()
    assert "gaps" in body or "systems" in body or isinstance(body, list) or "summary" in body


@pytest.mark.asyncio
async def test_nis2_flow_report_system_without_risk_assessment(client):
    """NIS2-rapport: system utan riskbedömning markeras som gap."""
    org = await create_org(client)
    sys_no_risk = await create_system(client, org["id"],
                                       name="Ej Riskbedömd",
                                       nis2_applicable=True,
                                       nis2_classification="viktig")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    summary = body["summary"]
    assert "without_risk_assessment" in summary
    assert isinstance(summary["without_risk_assessment"], int)

    entry = next((s for s in body["systems"] if s["id"] == sys_no_risk["id"]), None)
    if entry:
        assert entry.get("last_risk_assessment_date") is None


@pytest.mark.asyncio
async def test_nis2_flow_report_system_without_classification(client):
    """NIS2-rapport: system utan klassning markeras i summary."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         name="Ej Klassad",
                         nis2_applicable=True)

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert "without_classification" in summary


@pytest.mark.asyncio
async def test_nis2_flow_report_excel_format(client):
    """NIS2-rapport Excel-format returnerar binärfil."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         name="Excel NIS2 System",
                         nis2_applicable=True,
                         nis2_classification="väsentlig")

    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type


@pytest.mark.asyncio
async def test_nis2_flow_multiple_systems_all_levels(client):
    """NIS2-flöde med system på alla klassificeringsnivåer."""
    org = await create_org(client)
    expected_ids = []
    for cls in ["väsentlig", "viktig"]:
        sys = await create_system(client, org["id"],
                                   name=f"NIS2 {cls}",
                                   nis2_applicable=True,
                                   nis2_classification=cls)
        expected_ids.append(sys["id"])

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    report_ids = [s["id"] for s in resp.json()["systems"]]
    for eid in expected_ids:
        assert eid in report_ids


# ---------------------------------------------------------------------------
# Kontraktsflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contract_flow_new_agreement_to_expiry(client):
    """Kontraktsflöde: nytt avtal -> förfallodatum -> notifiering via expiring."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Kontraktsystem")

    today = date.today()
    contract = await create_contract(client, sys["id"],
                                      supplier_name="Leverantör AB",
                                      contract_start=str(today - timedelta(days=365)),
                                      contract_end=str(today + timedelta(days=60)),
                                      notice_period_months=3)
    assert contract["supplier_name"] == "Leverantör AB"

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract["id"] in ids


@pytest.mark.asyncio
async def test_contract_flow_not_expiring_not_in_list(client):
    """Kontrakt som inte löper ut inom 90 dagar ska inte vara i expiring-listan."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    today = date.today()
    contract = await create_contract(client, sys["id"],
                                      contract_end=str(today + timedelta(days=200)))

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract["id"] not in ids


@pytest.mark.asyncio
async def test_contract_flow_expiring_within_90_days(client):
    """Avtal som löper ut inom 90 dagar ska returneras från /contracts/expiring."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    today = date.today()

    expiring = await create_contract(client, sys["id"],
                                      contract_end=str(today + timedelta(days=30)))
    not_expiring = await create_contract(client, sys["id"],
                                          contract_end=str(today + timedelta(days=200)))

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert expiring["id"] in ids
    assert not_expiring["id"] not in ids


@pytest.mark.asyncio
async def test_contract_flow_renew_contract(client):
    """Kontraktsförnyelse: uppdatera slutdatum och auto_renewal."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    today = date.today()

    contract = await create_contract(client, sys["id"],
                                      contract_end=str(today + timedelta(days=30)))

    new_end = str(today + timedelta(days=365))
    resp = await client.patch(f"/api/v1/contracts/{contract['id']}", json={
        "contract_end": new_end,
        "auto_renewal": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["contract_end"] == new_end
    assert body["auto_renewal"] is True

    expiring_resp = await client.get("/api/v1/contracts/expiring")
    ids = [c["id"] for c in expiring_resp.json()]
    assert contract["id"] not in ids, "Förnyat kontrakt ska inte vara i expiring"


@pytest.mark.asyncio
async def test_contract_flow_terminate_contract(client):
    """Kontraktsavslut: radera kontrakt och verifiera att det är borta."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    del_resp = await client.delete(f"/api/v1/contracts/{contract['id']}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    ids = [c["id"] for c in list_resp.json()]
    assert contract["id"] not in ids


@pytest.mark.asyncio
async def test_contract_flow_multiple_contracts_per_system(client):
    """System kan ha flera aktiva kontrakt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    today = date.today()

    c1 = await create_contract(client, sys["id"],
                                 supplier_name="Leverantör 1",
                                 contract_end=str(today + timedelta(days=365)))
    c2 = await create_contract(client, sys["id"],
                                 supplier_name="Leverantör 2",
                                 contract_end=str(today + timedelta(days=180)))

    list_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert c1["id"] in ids
    assert c2["id"] in ids


@pytest.mark.asyncio
async def test_contract_flow_auto_renewal_notice_period(client):
    """Kontrakt med auto_renewal och uppsägningstid dokumenteras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    today = date.today()

    contract = await create_contract(client, sys["id"],
                                      auto_renewal=True,
                                      notice_period_months=6,
                                      contract_end=str(today + timedelta(days=365)))
    assert contract["auto_renewal"] is True
    assert contract["notice_period_months"] == 6


@pytest.mark.asyncio
async def test_contract_flow_expiring_default_90_days_window(client):
    """Standard expiring-fönster är 90 dagar."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    today = date.today()

    just_inside = await create_contract(client, sys["id"],
                                         contract_end=str(today + timedelta(days=89)))
    just_outside = await create_contract(client, sys["id"],
                                          contract_end=str(today + timedelta(days=91)))

    resp = await client.get("/api/v1/contracts/expiring")
    ids = [c["id"] for c in resp.json()]
    assert just_inside["id"] in ids
    assert just_outside["id"] not in ids


# ---------------------------------------------------------------------------
# Integrationsflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_flow_map_dependencies_10_systems(client):
    """Kartlägga beroenden mellan 10+ system."""
    org = await create_org(client)
    systems = []
    for i in range(10):
        sys = await create_system(client, org["id"], name=f"Integrationssystem {i}")
        systems.append(sys)

    integrations = []
    for i in range(9):
        intg = await create_integration(client,
                                         systems[i]["id"],
                                         systems[i + 1]["id"],
                                         integration_type="api",
                                         description=f"Koppling {i} -> {i+1}")
        integrations.append(intg)

    for intg in integrations:
        assert intg["source_system_id"] is not None
        assert intg["target_system_id"] is not None

    resp = await client.get("/api/v1/integrations/",
                             params={"source_system_id": systems[0]["id"]})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_integration_flow_identify_critical_dependencies(client):
    """Identifiera kritiska beroenden baserat på criticality."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Kärnssystem", criticality="kritisk")
    dep1 = await create_system(client, org["id"], name="Beroende 1")
    dep2 = await create_system(client, org["id"], name="Beroende 2")

    intg1 = await create_integration(client, src["id"], dep1["id"],
                                      criticality="hög",
                                      description="Kritisk beroende")
    intg2 = await create_integration(client, src["id"], dep2["id"],
                                      criticality="låg")

    assert intg1["criticality"] == "hög"
    assert intg2["criticality"] == "låg"


@pytest.mark.asyncio
async def test_integration_flow_external_dependency(client):
    """Externa beroenden dokumenteras med external_party."""
    org = await create_org(client)
    internal = await create_system(client, org["id"], name="Internt System")
    external = await create_system(client, org["id"], name="Externt System")

    intg = await create_integration(client, internal["id"], external["id"],
                                     is_external=True,
                                     external_party="Skatteverket",
                                     description="API-integration mot Skatteverket")
    assert intg["is_external"] is True
    assert intg["external_party"] == "Skatteverket"


@pytest.mark.asyncio
async def test_integration_flow_all_types(client):
    """Alla integrationstyper kan dokumenteras."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Källsystem")
    for itype in ["api", "filöverföring", "databasreplikering", "event", "manuell"]:
        tgt = await create_system(client, org["id"], name=f"Mål {itype}")
        intg = await create_integration(client, src["id"], tgt["id"],
                                         integration_type=itype)
        assert intg["integration_type"] == itype


@pytest.mark.asyncio
async def test_integration_flow_bidirectional(client):
    """Dubbelriktad integration kan dokumenteras som två separata."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="System A")
    sys_b = await create_system(client, org["id"], name="System B")

    a_to_b = await create_integration(client, sys_a["id"], sys_b["id"],
                                       description="A skickar till B")
    b_to_a = await create_integration(client, sys_b["id"], sys_a["id"],
                                       description="B skickar till A")

    assert a_to_b["source_system_id"] == sys_a["id"]
    assert b_to_a["source_system_id"] == sys_b["id"]


@pytest.mark.asyncio
async def test_integration_flow_list_by_source(client):
    """Lista integrationer per källsystem."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Masterkälla")
    targets = [await create_system(client, org["id"], name=f"Mål {i}") for i in range(3)]

    created_ids = []
    for tgt in targets:
        intg = await create_integration(client, src["id"], tgt["id"])
        created_ids.append(intg["id"])

    resp = await client.get("/api/v1/integrations/",
                             params={"source_system_id": src["id"]})
    assert resp.status_code == 200
    result_ids = [i["id"] for i in resp.json()]
    for cid in created_ids:
        assert cid in result_ids


@pytest.mark.asyncio
async def test_integration_flow_delete_integration(client):
    """Radera integration och verifiera borttagning."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Del Src")
    tgt = await create_system(client, org["id"], name="Del Tgt")
    intg = await create_integration(client, src["id"], tgt["id"])

    del_resp = await client.delete(f"/api/v1/integrations/{intg['id']}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/v1/integrations/",
                                  params={"source_system_id": src["id"]})
    assert list_resp.status_code == 200
    ids = [i["id"] for i in list_resp.json()]
    assert intg["id"] not in ids


@pytest.mark.asyncio
async def test_integration_flow_data_types_documented(client):
    """Datatyper i integration dokumenteras korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Data Src")
    tgt = await create_system(client, org["id"], name="Data Tgt")

    intg = await create_integration(client, src["id"], tgt["id"],
                                     data_types="Personnummer, adressuppgifter",
                                     description="Överföring av personuppgifter")
    assert intg.get("data_types") == "Personnummer, adressuppgifter"


# ---------------------------------------------------------------------------
# Import/export roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_roundtrip_json_import_export(client):
    """JSON export -> import -> export ger konsekventa resultat."""
    org = await create_org(client, name="JSON Roundtrip Org")
    rows = [
        {
            "name": f"Roundtrip {i}",
            "description": f"System {i}",
            "system_category": "verksamhetssystem",
            "criticality": "medel",
        }
        for i in range(5)
    ]
    content, filename, content_type = make_json_file(rows)
    import_resp = await post_import(client, org["id"], content, filename, content_type)
    assert import_resp.status_code == 200
    assert import_resp.json()["imported"] == 5

    export_resp = await client.get("/api/v1/export/systems.json")
    assert export_resp.status_code == 200
    exported = export_resp.json()
    exported_names = {s["name"] for s in exported}
    for i in range(5):
        assert f"Roundtrip {i}" in exported_names


@pytest.mark.asyncio
async def test_roundtrip_csv_import_export(client):
    """CSV import -> export roundtrip."""
    org = await create_org(client, name="CSV Roundtrip Org 2")
    rows = [
        {"name": f"CSV RT {i}", "description": "Test", "system_category": "infrastruktur"}
        for i in range(3)
    ]
    content, filename, content_type = make_csv_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 3

    export_resp = await client.get("/api/v1/export/systems.csv")
    assert export_resp.status_code == 200
    text = export_resp.text
    for i in range(3):
        assert f"CSV RT {i}" in text


@pytest.mark.asyncio
async def test_roundtrip_excel_import_export(client):
    """Excel import -> export roundtrip."""
    try:
        from openpyxl import Workbook
    except ImportError:
        pytest.skip("openpyxl not installed")

    org = await create_org(client, name="Excel Roundtrip Org")
    wb = Workbook()
    ws = wb.active
    headers = ["name", "description", "system_category"]
    ws.append(headers)
    for i in range(3):
        ws.append([f"Excel RT {i}", f"Beskrivning {i}", "plattform"])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    content = buffer.read()
    filename = "systems.xlsx"
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 3

    export_resp = await client.get("/api/v1/export/systems.xlsx")
    assert export_resp.status_code == 200
    content_type_hdr = export_resp.headers.get("content-type", "")
    assert "spreadsheet" in content_type_hdr or "excel" in content_type_hdr or "octet-stream" in content_type_hdr


@pytest.mark.asyncio
async def test_roundtrip_json_fields_preserved(client):
    """Importerade fält bevaras korrekt i export."""
    org = await create_org(client, name="Fields Preserved Org")
    rows = [{
        "name": "Fältbevaringssystem",
        "description": "Test av fältbevarning",
        "system_category": "verksamhetssystem",
        "criticality": "hög",
        "lifecycle_status": "planerad",
    }]
    content, filename, content_type = make_json_file(rows)
    import_resp = await post_import(client, org["id"], content, filename, content_type)
    assert import_resp.status_code == 200

    list_resp = await client.get("/api/v1/systems/",
                                  params={"organization_id": org["id"]})
    systems = list_resp.json()["items"]
    target = next((s for s in systems if s["name"] == "Fältbevaringssystem"), None)
    assert target is not None
    assert target["criticality"] == "hög"
    assert target["lifecycle_status"] == "planerad"


# ---------------------------------------------------------------------------
# Rapportflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_nis2_json_structure(client):
    """NIS2-rapport JSON har rätt struktur."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         nis2_applicable=True,
                         nis2_classification="väsentlig",
                         criticality="kritisk")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    assert "generated_at" in body
    assert "summary" in body
    assert "systems" in body
    assert "total" in body["summary"]
    assert "without_classification" in body["summary"]
    assert "without_risk_assessment" in body["summary"]
    assert isinstance(body["systems"], list)


@pytest.mark.asyncio
async def test_report_nis2_json_system_entry_structure(client):
    """NIS2-rapport: systempost har alla förväntade fält."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name="Rapport System",
                               nis2_applicable=True,
                               nis2_classification="viktig",
                               criticality="hög")
    await create_owner(client, sys["id"], org["id"], name="Rapport Ägare")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    entry = next((s for s in resp.json()["systems"] if s["id"] == sys["id"]), None)
    assert entry is not None
    assert "name" in entry
    assert "nis2_classification" in entry
    assert "criticality" in entry
    assert "has_gdpr_treatment" in entry
    assert "owner_names" in entry
    assert isinstance(entry["owner_names"], list)


@pytest.mark.asyncio
async def test_report_nis2_excel_downloadable(client):
    """NIS2-rapport Excel kan laddas ned."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         nis2_applicable=True,
                         nis2_classification="väsentlig")

    resp = await client.get("/api/v1/reports/nis2.xlsx")
    assert resp.status_code == 200
    assert len(resp.content) > 0


@pytest.mark.asyncio
async def test_report_compliance_gap_returns_response(client):
    """Compliance gap-rapport returnerar svar."""
    org = await create_org(client)
    await create_system(client, org["id"],
                         nis2_applicable=True,
                         nis2_classification="väsentlig",
                         criticality="kritisk")

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None


@pytest.mark.asyncio
async def test_report_nis2_summary_counts_correct(client):
    """NIS2-rapport: summary.total matchar antal NIS2-system i rapport."""
    org = await create_org(client)
    created_ids = []
    for i in range(3):
        sys = await create_system(client, org["id"],
                                   name=f"NIS2 Count System {i}",
                                   nis2_applicable=True,
                                   nis2_classification="viktig")
        created_ids.append(sys["id"])

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    body = resp.json()

    report_ids = [s["id"] for s in body["systems"]]
    for cid in created_ids:
        assert cid in report_ids

    assert body["summary"]["total"] >= 3


@pytest.mark.asyncio
async def test_report_nis2_owner_names_populated(client):
    """NIS2-rapport: owner_names fylls i för system med ägare."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               nis2_applicable=True,
                               nis2_classification="väsentlig")
    await create_owner(client, sys["id"], org["id"],
                        role="systemägare",
                        name="Test Ägare NIS2")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    entry = next((s for s in resp.json()["systems"] if s["id"] == sys["id"]), None)
    assert entry is not None
    assert "Test Ägare NIS2" in entry.get("owner_names", [])


@pytest.mark.asyncio
async def test_report_nis2_gdpr_flag_correct(client):
    """NIS2-rapport: has_gdpr_treatment sätts korrekt."""
    org = await create_org(client)

    sys_with_gdpr = await create_system(client, org["id"],
                                         name="Med GDPR",
                                         nis2_applicable=True,
                                         nis2_classification="väsentlig",
                                         treats_personal_data=True)
    await create_gdpr_treatment(client, sys_with_gdpr["id"],
                                 data_categories=["vanliga"])

    sys_no_gdpr = await create_system(client, org["id"],
                                       name="Utan GDPR",
                                       nis2_applicable=True,
                                       nis2_classification="viktig")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    systems = resp.json()["systems"]

    with_gdpr_entry = next((s for s in systems if s["id"] == sys_with_gdpr["id"]), None)
    no_gdpr_entry = next((s for s in systems if s["id"] == sys_no_gdpr["id"]), None)

    if with_gdpr_entry:
        assert with_gdpr_entry["has_gdpr_treatment"] is True
    if no_gdpr_entry:
        assert no_gdpr_entry["has_gdpr_treatment"] is False


# ---------------------------------------------------------------------------
# Felhanteringsflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_create_system_missing_name(client):
    """Skapa system utan namn ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "description": "Ingen namnfält",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_create_system_missing_organization_id(client):
    """Skapa system utan organization_id ger 422."""
    resp = await client.post("/api/v1/systems/", json={
        "name": "System utan org",
        "description": "Ingen org",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_create_system_invalid_category(client):
    """Skapa system med ogiltig kategori ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Ogiltigt System",
        "description": "Test",
        "system_category": "ogiltig_kategori",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_create_system_invalid_lifecycle_status(client):
    """Skapa system med ogiltig lifecycle_status ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Ogiltigt Status System",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "lifecycle_status": "ej_existerande_status",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_create_system_nonexistent_organization(client):
    """Skapa system med icke-existerande org ger 422 eller 404."""
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": "00000000-0000-0000-0000-000000000000",
        "name": "System utan org",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (404, 422, 400)


@pytest.mark.asyncio
async def test_error_delete_organization_with_systems(client):
    """Radera organisation med befintliga system ska nekas."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Skyddat System")

    del_resp = await client.delete(f"/api/v1/organizations/{org['id']}")
    assert del_resp.status_code in (409, 422, 400, 422), (
        f"Org med system borde inte kunna raderas, fick {del_resp.status_code}"
    )


@pytest.mark.asyncio
async def test_error_duplicate_import_skipped(client):
    """Import av redan existerande system (duplikat) hoppas över med felmeddelande."""
    org = await create_org(client)
    rows = [{"name": "Duplikat System", "description": "Test", "system_category": "verksamhetssystem"}]
    content, filename, content_type = make_json_file(rows)

    resp1 = await post_import(client, org["id"], content, filename, content_type)
    assert resp1.status_code == 200
    assert resp1.json()["imported"] == 1

    resp2 = await post_import(client, org["id"], content, filename, content_type)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["imported"] == 0
    assert len(body2["errors"]) == 1


@pytest.mark.asyncio
async def test_error_invalid_classification_value(client):
    """Klassningsvärde utanför 0-4 ger 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": 5,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_get_nonexistent_system(client):
    """Hämta icke-existerande system ger 404."""
    resp = await client.get("/api/v1/systems/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_error_get_nonexistent_organization(client):
    """Hämta icke-existerande organisation ger 404."""
    resp = await client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_error_patch_nonexistent_system(client):
    """PATCH på icke-existerande system ger 404."""
    resp = await client.patch(
        "/api/v1/systems/00000000-0000-0000-0000-000000000000",
        json={"name": "Uppdaterat Namn"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_error_create_organization_missing_name(client):
    """Skapa organisation utan namn ger 422."""
    resp = await client.post("/api/v1/organizations/", json={"org_type": "kommun"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_create_organization_invalid_type(client):
    """Skapa organisation med ogiltig org_type ger 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Felaktig Org",
        "org_type": "ogiltig_typ",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_import_empty_file(client):
    """Import av tom fil ger 200 med 0 importerade."""
    org = await create_org(client)
    content, filename, content_type = make_json_file([])
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 0


@pytest.mark.asyncio
async def test_error_integration_self_reference(client):
    """Integration där källa och mål är samma system ska ge fel."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Self Ref System")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys["id"],
        "target_system_id": sys["id"],
        "integration_type": "api",
    })
    assert resp.status_code in (400, 422), (
        f"Självkoppling borde ge fel, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_error_delete_nonexistent_system(client):
    """Radera icke-existerande system ger 404."""
    resp = await client.delete("/api/v1/systems/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_error_delete_nonexistent_organization(client):
    """Radera icke-existerande organisation ger 404."""
    resp = await client.delete("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sammansatta E2E-flöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_inventory_workflow(client):
    """Komplett inventering: org -> system -> klassificera -> ägare -> GDPR -> kontrakt -> rapport."""
    org = await create_org(client, name="Inventerings Kommun Full")

    systems_created = []
    for i, (name, cat, crit, nis2) in enumerate([
        ("Procapita", "verksamhetssystem", "hög", True),
        ("Visma Lön", "verksamhetssystem", "medel", False),
        ("AD/LDAP", "infrastruktur", "kritisk", True),
        ("Backup System", "infrastruktur", "hög", False),
        ("Webbportal", "stödsystem", "medel", True),
    ]):
        sys = await create_system(client, org["id"],
                                   name=name,
                                   system_category=cat,
                                   criticality=crit,
                                   nis2_applicable=nis2,
                                   nis2_classification="väsentlig" if nis2 else None,
                                   treats_personal_data=(i % 2 == 0))
        await create_classification(client, sys["id"], confidentiality=2+i%3, integrity=2, availability=3)
        await create_owner(client, sys["id"], org["id"], name=f"Ägare {name}")
        if i % 2 == 0:
            await create_gdpr_treatment(client, sys["id"], data_categories=["vanliga"])
        await create_contract(client, sys["id"],
                               supplier_name=f"Leverantör {i}",
                               contract_end=str(date.today() + timedelta(days=365)))
        systems_created.append(sys)

    list_resp = await client.get("/api/v1/systems/",
                                  params={"organization_id": org["id"]})
    assert list_resp.json()["total"] >= 5

    nis2_resp = await client.get("/api/v1/reports/nis2")
    assert nis2_resp.status_code == 200
    nis2_ids = [s["id"] for s in nis2_resp.json()["systems"]]
    for sys in systems_created:
        if sys["nis2_applicable"]:
            assert sys["id"] in nis2_ids


@pytest.mark.asyncio
async def test_e2e_gdpr_audit_trail(client):
    """GDPR-flöde med audit trail: alla ändringar loggas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name="Auditerat GDPR System",
                               treats_personal_data=True)

    await create_gdpr_treatment(client, sys["id"],
                                 data_categories=["vanliga"],
                                 legal_basis="Rättslig förpliktelse (art. 6.1 c)")

    await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "treats_sensitive_data": True,
        "third_country_transfer": False,
    })

    audit_resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert audit_resp.status_code == 200
    audit_entries = audit_resp.json()
    assert isinstance(audit_entries, list)
    assert len(audit_entries) >= 1


@pytest.mark.asyncio
async def test_e2e_nis2_compliance_full_workflow(client):
    """Komplett NIS2-complianceflöde från identifiering till rapport."""
    org = await create_org(client)

    systems = []
    for name, cls in [("Driftsystem 1", "väsentlig"), ("Driftsystem 2", "viktig")]:
        sys = await create_system(client, org["id"],
                                   name=name,
                                   criticality="kritisk",
                                   system_category="infrastruktur")

        resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
            "nis2_applicable": True,
            "nis2_classification": cls,
            "last_risk_assessment_date": "2025-03-01",
        })
        assert resp.json()["nis2_applicable"] is True

        await create_classification(client, sys["id"], confidentiality=3, integrity=3, availability=4)
        await create_owner(client, sys["id"], org["id"], name=f"NIS2 Ägare {name}")
        systems.append(sys)

    report = await client.get("/api/v1/reports/nis2")
    assert report.status_code == 200
    body = report.json()
    report_ids = [s["id"] for s in body["systems"]]
    for sys in systems:
        assert sys["id"] in report_ids


@pytest.mark.asyncio
async def test_e2e_contract_lifecycle_with_renewal(client):
    """Komplett kontraktslivscykel: nytt avtal -> nära förfall -> förnyad -> inte längre i expiring."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Kontraktslivscykel System")
    today = date.today()

    contract = await create_contract(client, sys["id"],
                                      supplier_name="Vital Leverantör AB",
                                      contract_start=str(today - timedelta(days=700)),
                                      contract_end=str(today + timedelta(days=45)),
                                      notice_period_months=3,
                                      auto_renewal=False)

    expiring_resp = await client.get("/api/v1/contracts/expiring")
    assert contract["id"] in [c["id"] for c in expiring_resp.json()]

    new_end = str(today + timedelta(days=730))
    renew_resp = await client.patch(f"/api/v1/contracts/{contract['id']}", json={
        "contract_end": new_end,
        "auto_renewal": True,
    })
    assert renew_resp.status_code == 200
    assert renew_resp.json()["contract_end"] == new_end

    expiring_again = await client.get("/api/v1/contracts/expiring")
    assert contract["id"] not in [c["id"] for c in expiring_again.json()]


@pytest.mark.asyncio
async def test_e2e_integration_dependency_chain(client):
    """Beroendekedjor: System A -> B -> C med kritikalitetsnivåer."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="Kärnapplikation", criticality="kritisk")
    sys_b = await create_system(client, org["id"], name="Mellannivå", criticality="hög")
    sys_c = await create_system(client, org["id"], name="Stödsystem", criticality="medel")

    intg_ab = await create_integration(client, sys_a["id"], sys_b["id"],
                                        criticality="hög",
                                        description="A beror på B")
    intg_bc = await create_integration(client, sys_b["id"], sys_c["id"],
                                        criticality="medel",
                                        description="B beror på C")

    assert intg_ab["source_system_id"] == sys_a["id"]
    assert intg_ab["target_system_id"] == sys_b["id"]
    assert intg_bc["source_system_id"] == sys_b["id"]
    assert intg_bc["target_system_id"] == sys_c["id"]

    resp_b_out = await client.get("/api/v1/integrations/",
                                   params={"source_system_id": sys_b["id"]})
    assert resp_b_out.status_code == 200
    b_out_ids = [i["id"] for i in resp_b_out.json()]
    assert intg_bc["id"] in b_out_ids


# ---------------------------------------------------------------------------
# Parametriserade livscykel-statusövergångar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status", [
    ("planerad", "under_inforande"),
    ("planerad", "i_drift"),
    ("planerad", "avvecklad"),
    ("under_inforande", "i_drift"),
    ("under_inforande", "under_avveckling"),
    ("under_inforande", "avvecklad"),
    ("i_drift", "under_avveckling"),
    ("i_drift", "avvecklad"),
    ("under_avveckling", "avvecklad"),
    ("under_avveckling", "i_drift"),
])
async def test_lifecycle_parametrized_transition(client, from_status, to_status):
    """Parametriserade statusövergångar ska vara möjliga."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status=from_status)

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={"lifecycle_status": to_status})
    assert resp.status_code == 200, (
        f"Övergång {from_status} -> {to_status} misslyckades: {resp.status_code} {resp.text}"
    )
    assert resp.json()["lifecycle_status"] == to_status


# ---------------------------------------------------------------------------
# Parametriserade GDPR processor_agreement_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["ja", "nej", "under_framtagande", "ej_tillämpligt"])
async def test_gdpr_processor_agreement_all_statuses(client, status):
    """GDPR processor_agreement_status: alla giltiga värden accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        processor_agreement_status=status)
    assert gdpr["processor_agreement_status"] == status


# ---------------------------------------------------------------------------
# Parametriserade integrationstyper i GDPR-kontext
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("data_categories", [
    ["vanliga"],
    ["känsliga"],
    ["personnummer"],
    ["vanliga", "känsliga"],
    ["vanliga", "känsliga", "personnummer"],
])
async def test_gdpr_data_categories_variants(client, data_categories):
    """GDPR: olika kombinationer av datakategorier accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=data_categories)
    assert gdpr["data_categories"] is not None
    assert isinstance(gdpr["data_categories"], list)


# ---------------------------------------------------------------------------
# Parametriserade klassificeringskombinationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("k,r,t", [
    (0, 0, 0),
    (1, 1, 1),
    (2, 2, 2),
    (3, 3, 3),
    (4, 4, 4),
    (0, 4, 2),
    (4, 0, 3),
    (2, 3, 1),
])
async def test_classification_krt_combinations(client, k, r, t):
    """K/R/T-kombinationer 0-4 accepteras alla."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": k,
        "integrity": r,
        "availability": t,
        "classified_by": "test@example.se",
    })
    assert resp.status_code == 201, f"K={k} R={r} T={t} avvisades: {resp.text}"
    body = resp.json()
    assert body["confidentiality"] == k
    assert body["integrity"] == r
    assert body["availability"] == t


# ---------------------------------------------------------------------------
# Parametriserade ägarroller i registreringsflöde
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [
    "systemägare",
    "informationsägare",
    "systemförvaltare",
    "teknisk_förvaltare",
    "it_kontakt",
    "dataskyddsombud",
])
async def test_registration_all_owner_roles(client, role):
    """Registreringsflöde: alla ägarroller kan tilldelas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"],
                                role=role,
                                name=f"Person med roll {role}",
                                email=f"{role.replace('_', '')}@test.se")
    assert owner["role"] == role
    assert owner["system_id"] == sys["id"]


# ---------------------------------------------------------------------------
# Parametriserade kontraktsupphandlingstyper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("procurement_type", [
    "direktupphandling",
    "förenklad upphandling",
    "Upphandling LOU",
    "avrop ramavtal",
    "EU-upphandling",
])
async def test_contract_procurement_types(client, procurement_type):
    """Kontrakt: olika upphandlingstyper kan dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"],
                                      procurement_type=procurement_type)
    assert contract.get("procurement_type") == procurement_type


# ---------------------------------------------------------------------------
# Parametriserade hosting-modeller
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("hosting_model,cloud_provider,location", [
    ("on-premise", None, "Sverige"),
    ("cloud", "AWS", "EU"),
    ("cloud", "Microsoft Azure", "Sverige"),
    ("cloud", "Google Cloud", "Belgien"),
    ("hybrid", None, "Sverige"),
    ("saas", "Salesforce", "USA"),
])
async def test_registration_hosting_models(client, hosting_model, cloud_provider, location):
    """Registreringsflöde: alla hostingmodeller kan dokumenteras."""
    org = await create_org(client)
    kwargs = {
        "hosting_model": hosting_model,
        "data_location_country": location,
    }
    if cloud_provider:
        kwargs["cloud_provider"] = cloud_provider
        if location == "USA":
            kwargs["third_country_transfer"] = True
    sys = await create_system(client, org["id"], **kwargs)
    assert sys["hosting_model"] == hosting_model
    assert sys["data_location_country"] == location


# ---------------------------------------------------------------------------
# Parametriserade criticality-nivåer i NIS2-kontext
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality,nis2_cls", [
    ("kritisk", "väsentlig"),
    ("hög", "väsentlig"),
    ("hög", "viktig"),
    ("medel", "viktig"),
    ("medel", "ej_tillämplig"),
    ("låg", "ej_tillämplig"),
])
async def test_nis2_criticality_classification_combinations(client, criticality, nis2_cls):
    """NIS2: kritikalitet och klassificering kan kombineras fritt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               criticality=criticality,
                               nis2_applicable=True,
                               nis2_classification=nis2_cls)
    assert sys["criticality"] == criticality
    assert sys["nis2_classification"] == nis2_cls


# ---------------------------------------------------------------------------
# Parametriserade batch-importstorlekar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [1, 5, 10, 25])
async def test_import_batch_sizes(client, batch_size):
    """Import: olika batchstorlekar fungerar korrekt."""
    org = await create_org(client, name=f"Batch Size {batch_size} Org")
    rows = [
        {
            "name": f"Batchsys {batch_size}-{i}",
            "description": "Test",
            "system_category": "verksamhetssystem",
        }
        for i in range(batch_size)
    ]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == batch_size


# ---------------------------------------------------------------------------
# Parametriserade systemkategorier i registreringsflöde
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category", [
    "verksamhetssystem",
    "stödsystem",
    "infrastruktur",
    "plattform",
    "iot",
])
async def test_registration_all_system_categories(client, category):
    """Registreringsflöde: alla systemkategorier genomgår korrekt registrering."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                               name=f"Kategori {category}",
                               system_category=category,
                               criticality="medel")
    await create_classification(client, sys["id"])
    await create_owner(client, sys["id"], org["id"])

    verify = await client.get(f"/api/v1/systems/{sys['id']}")
    assert verify.status_code == 200
    assert verify.json()["system_category"] == category


# ---------------------------------------------------------------------------
# Parametriserade kontraktsförfallsfönster
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("days_until_expiry,should_be_expiring", [
    (1, True),
    (30, True),
    (60, True),
    (89, True),
    (90, True),
    (91, False),
    (180, False),
    (365, False),
])
async def test_contract_expiry_windows(client, days_until_expiry, should_be_expiring):
    """Kontraktsförfall: korrekt window-kontroll för expiring-endpoint."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name=f"Expiry {days_until_expiry} days")
    today = date.today()
    contract = await create_contract(client, sys["id"],
                                      contract_end=str(today + timedelta(days=days_until_expiry)))

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    if should_be_expiring:
        assert contract["id"] in ids, f"Kontrakt om {days_until_expiry} dagar borde vara i expiring"
    else:
        assert contract["id"] not in ids, f"Kontrakt om {days_until_expiry} dagar borde INTE vara i expiring"


# ---------------------------------------------------------------------------
# Parametriserade felfall vid saknade obligatoriska fält
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field,payload", [
    ("name", {"organization_id": "PLACEHOLDER", "description": "Test", "system_category": "verksamhetssystem"}),
    ("system_category", {"organization_id": "PLACEHOLDER", "name": "Test", "description": "Test"}),
    ("organization_id", {"name": "Test", "description": "Test", "system_category": "verksamhetssystem"}),
])
async def test_error_missing_required_fields(client, missing_field, payload):
    """Saknade obligatoriska fält ger 422."""
    org = await create_org(client)
    if "organization_id" in payload:
        payload["organization_id"] = org["id"]
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 422, (
        f"Saknat fält {missing_field!r} borde ge 422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Parametriserade ogiltiga enum-värden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("lifecycle_status", "aktiv"),
    ("lifecycle_status", "inaktiv"),
    ("lifecycle_status", ""),
    ("criticality", "extremt"),
    ("criticality", "normal"),
    ("system_category", "övrigt"),
    ("system_category", "applikation"),
])
async def test_error_invalid_enum_values(client, field, value):
    """Ogiltiga enum-värden ger 422."""
    org = await create_org(client)
    payload = {
        "organization_id": org["id"],
        "name": "Ogiltig Enum System",
        "description": "Test",
        "system_category": "verksamhetssystem",
        field: value,
    }
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 422, (
        f"Ogiltigt {field}={value!r} borde ge 422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Rensningsflöden — kaskad-borttagning verifieras
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("related_entity,create_fn_name", [
    ("classifications", "create_classification"),
    ("contracts", "create_contract"),
    ("owners", "create_owner"),
    ("gdpr", "create_gdpr_treatment"),
])
async def test_cascade_delete_system_removes_related(client, related_entity, create_fn_name):
    """Radering av system tar kaskad-bort relaterade entiteter."""
    import tests.factories as factories
    create_fn = getattr(factories, create_fn_name)

    org = await create_org(client)
    sys = await create_system(client, org["id"], name=f"Cascade {related_entity}")

    if create_fn_name == "create_owner":
        await create_fn(client, sys["id"], org["id"])
    elif create_fn_name == "create_integration":
        pass
    else:
        await create_fn(client, sys["id"])

    del_resp = await client.delete(f"/api/v1/systems/{sys['id']}")
    assert del_resp.status_code == 204

    verify_resp = await client.get(f"/api/v1/systems/{sys['id']}/{related_entity}")
    if verify_resp.status_code == 200:
        assert verify_resp.json() == [], (
            f"Relaterade {related_entity} borde vara tomma efter systemradering"
        )
    else:
        assert verify_resp.status_code in (404, 410)


# ---------------------------------------------------------------------------
# Export format-kontroll
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("format_path,expected_content_type_fragment", [
    ("/api/v1/export/systems.json", "json"),
    ("/api/v1/export/systems.csv", "csv"),
    ("/api/v1/export/systems.xlsx", "spreadsheet"),
])
async def test_export_formats_content_type(client, format_path, expected_content_type_fragment):
    """Export: varje format returnerar korrekt content-type."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Export Format System")

    resp = await client.get(format_path)
    assert resp.status_code == 200, f"Export {format_path} misslyckades: {resp.text}"
    content_type = resp.headers.get("content-type", "").lower()
    assert expected_content_type_fragment in content_type or "octet-stream" in content_type, (
        f"Format {format_path}: förväntad content-type fragment {expected_content_type_fragment!r}, "
        f"fick {content_type!r}"
    )


# ---------------------------------------------------------------------------
# Notifieringsflöden (notification-relaterade queries)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_contract_expiry_no_false_positives(client):
    """Notifieringskontroll: bara kontrakt inom 90 dagar triggar expiring."""
    org = await create_org(client)
    today = date.today()

    systems_and_contracts = []
    for days in [7, 30, 60, 89, 91, 180, 365]:
        sys = await create_system(client, org["id"], name=f"Notif System {days}d")
        contract = await create_contract(client, sys["id"],
                                          contract_end=str(today + timedelta(days=days)))
        systems_and_contracts.append((days, contract["id"]))

    resp = await client.get("/api/v1/contracts/expiring")
    assert resp.status_code == 200
    expiring_ids = {c["id"] for c in resp.json()}

    for days, cid in systems_and_contracts:
        if days <= 90:
            assert cid in expiring_ids, f"Kontrakt om {days} dagar borde vara i expiring"
        else:
            assert cid not in expiring_ids, f"Kontrakt om {days} dagar borde INTE vara i expiring"


@pytest.mark.asyncio
async def test_notification_nis2_report_without_risk_assessment_count(client):
    """NIS2-rapport: räknare för system utan riskbedömning är korrekt."""
    org = await create_org(client)
    no_risk_systems = []
    for i in range(3):
        sys = await create_system(client, org["id"],
                                   name=f"Ej Riskbedömd {i}",
                                   nis2_applicable=True,
                                   nis2_classification="viktig")
        no_risk_systems.append(sys["id"])

    with_risk = await create_system(client, org["id"],
                                     name="Med Riskbedömning",
                                     nis2_applicable=True,
                                     nis2_classification="viktig",
                                     last_risk_assessment_date="2025-01-01")

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert summary["without_risk_assessment"] >= 3


# ---------------------------------------------------------------------------
# Organisationshierarkiflöden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_org_hierarchy_parent_child_systems(client):
    """Organisation med hierarki: barn-org kan ha egna system."""
    parent = await create_org(client, name="Moderorganisation")
    child = await create_org(client, name="Delorganisation",
                              parent_org_id=parent["id"])

    assert child["parent_org_id"] == parent["id"]

    parent_sys = await create_system(client, parent["id"], name="Moderorg System")
    child_sys = await create_system(client, child["id"], name="Delorg System")

    parent_resp = await client.get("/api/v1/systems/",
                                    params={"organization_id": parent["id"]})
    child_resp = await client.get("/api/v1/systems/",
                                   params={"organization_id": child["id"]})

    parent_ids = [s["id"] for s in parent_resp.json()["items"]]
    child_ids = [s["id"] for s in child_resp.json()["items"]]

    assert parent_sys["id"] in parent_ids
    assert child_sys["id"] in child_ids
    assert parent_sys["id"] not in child_ids
    assert child_sys["id"] not in parent_ids


@pytest.mark.asyncio
async def test_org_hierarchy_multi_level(client):
    """Tre-nivåers hierarki: mor -> dotter -> barnbarn."""
    grandparent = await create_org(client, name="Förbund")
    parent = await create_org(client, name="Region", parent_org_id=grandparent["id"])
    child = await create_org(client, name="Kommun", parent_org_id=parent["id"])

    assert parent["parent_org_id"] == grandparent["id"]
    assert child["parent_org_id"] == parent["id"]


# ---------------------------------------------------------------------------
# Systemsökning och filtrering i flödeskontext
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_flow_find_system_by_name(client):
    """Sökning: hitta system på namn i lista med många system."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Procapita Vård")
    await create_system(client, org["id"], name="Visma Lön")
    await create_system(client, org["id"], name="Agresso ekonomi")
    await create_system(client, org["id"], name="Stratsys")

    resp = await client.get("/api/v1/systems/", params={"q": "Procapita"})
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["items"]]
    assert "Procapita Vård" in names
    assert "Visma Lön" not in names
    assert "Agresso ekonomi" not in names


@pytest.mark.asyncio
async def test_search_flow_filter_combines_correctly(client):
    """Kombinerade filter: NIS2 + status fungerar tillsammans."""
    org = await create_org(client)
    target = await create_system(client, org["id"],
                                  name="Mål System",
                                  nis2_applicable=True,
                                  lifecycle_status="i_drift")
    noise1 = await create_system(client, org["id"],
                                  name="Brus 1",
                                  nis2_applicable=False,
                                  lifecycle_status="i_drift")
    noise2 = await create_system(client, org["id"],
                                  name="Brus 2",
                                  nis2_applicable=True,
                                  lifecycle_status="avvecklad")

    resp = await client.get("/api/v1/systems/", params={
        "nis2_applicable": True,
        "lifecycle_status": "i_drift",
        "organization_id": org["id"],
    })
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert target["id"] in ids
    assert noise1["id"] not in ids
    assert noise2["id"] not in ids


@pytest.mark.asyncio
async def test_search_flow_stats_overview_reflects_data(client):
    """Statistik-overview reflekterar faktiskt antal system."""
    org = await create_org(client)
    initial_resp = await client.get("/api/v1/systems/stats/overview")
    initial_total = initial_resp.json()["total_systems"]

    for i in range(5):
        await create_system(client, org["id"], name=f"Stats System {i}")

    resp = await client.get("/api/v1/systems/stats/overview")
    assert resp.status_code == 200
    new_total = resp.json()["total_systems"]
    assert new_total >= initial_total + 5


# ---------------------------------------------------------------------------
# Parametriserade PATCH-uppdateringar på system
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("name", "Nytt Systemnamn"),
    ("description", "Uppdaterad beskrivning"),
    ("criticality", "hög"),
    ("criticality", "kritisk"),
    ("criticality", "låg"),
    ("hosting_model", "cloud"),
    ("hosting_model", "on-premise"),
    ("backup_frequency", "timvis"),
    ("rpo", "1 timme"),
    ("rto", "4 timmar"),
    ("dr_plan_exists", True),
    ("has_elevated_protection", True),
    ("treats_personal_data", True),
    ("treats_sensitive_data", True),
    ("third_country_transfer", True),
    ("nis2_applicable", True),
    ("product_name", "Uppdaterat Produktnamn"),
    ("product_version", "2.5.0"),
    ("business_area", "Utbildning"),
])
async def test_patch_system_individual_fields(client, field, value):
    """PATCH: varje fält kan uppdateras individuellt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={field: value})
    assert resp.status_code == 200, (
        f"PATCH {field}={value!r} misslyckades: {resp.status_code} {resp.text}"
    )
    assert resp.json()[field] == value


# ---------------------------------------------------------------------------
# Parametriserade GDPR retention-policies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("retention_policy", [
    "2 år",
    "5 år efter avslutat ärende",
    "10 år enligt lag",
    "Tills vidare",
    "6 månader",
])
async def test_gdpr_retention_policy_variants(client, retention_policy):
    """GDPR: olika lagringstider kan dokumenteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        data_categories=["vanliga"],
                                        retention_policy=retention_policy)
    assert gdpr.get("retention_policy") == retention_policy
