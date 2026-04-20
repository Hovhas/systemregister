"""
Kravspecifikation-validering — verifiera att API:et stöder alla 67 attribut.

Kategori 17: Kravspecifikation-validering (~67 testfall)

Täcker:
- Kat 1: Systemidentitet (system_id, name, aliases, description, system_category, business_area, organization_id)
- Kat 3: Säkerhet (criticality, has_elevated_protection, security_protection, nis2_applicable, nis2_classification, K/R/T/S 0-4)
- Kat 4: GDPR (treats_personal_data, treats_sensitive_data, third_country_transfer, gdpr_treatments)
- Kat 5: Hosting (hosting_model, cloud_provider, data_location_country, product_name, product_version)
- Kat 6: Livscykel (lifecycle_status, deployment_date, planned_decommission_date, end_of_support_date)
- Kat 7: Integrationer (source/target, type, data_types, frequency, criticality, is_external, external_party)
- Kat 8: Avtal (supplier_name, supplier_org_number, contract_start/end, auto_renewal, notice_period_months,
         sla_description, license_model, annual_license_cost, annual_operations_cost, procurement_type, support_level)
- Kat 9: Backup (backup_frequency, rpo, rto, dr_plan_exists)
- Kat 11: Audit (table_name, record_id, action, changed_by, old_values, new_values)
- Kat 12: Risk (last_risk_assessment_date, klassa_reference_id)
- Flexibelt: extended_attributes (JSONB)
"""

import pytest
from datetime import date, timedelta
from tests.factories import (
    create_org, create_system, create_integration, create_gdpr_treatment,
    create_contract,
)


# ---------------------------------------------------------------------------
# Kat 1: Systemidentitet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_system_id_is_uuid(client):
    """system_id (auto) ska vara ett UUID format."""
    import re
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, sys["id"]), (
        f"system_id ska vara UUID, fick: {sys['id']}"
    )


@pytest.mark.asyncio
async def test_compliance_system_name_stored_and_returned(client):
    """name-attributet ska lagras och returneras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Specifikt Systemnamn")
    assert sys["name"] == "Specifikt Systemnamn"


@pytest.mark.asyncio
async def test_compliance_system_aliases_field_exists(client):
    """aliases-fältet ska existera i systemresponsen."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert "aliases" in sys, "aliases-fältet saknas i systemresponsen"


@pytest.mark.asyncio
async def test_compliance_system_aliases_can_be_set(client):
    """aliases ska kunna sättas vid skapande."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], aliases="GAMLA-NAMN, FÖRKORTNING")
    assert sys["aliases"] is not None
    assert "GAMLA-NAMN" in sys["aliases"] or sys["aliases"] == "GAMLA-NAMN, FÖRKORTNING"


@pytest.mark.asyncio
async def test_compliance_system_description_field(client):
    """description ska lagras och returneras."""
    org = await create_org(client)
    desc = "Detaljerad beskrivning av systemets syfte och funktion"
    sys = await create_system(client, org["id"], description=desc)
    assert sys["description"] == desc


@pytest.mark.asyncio
async def test_compliance_system_category_all_values(client):
    """Alla giltiga system_category-värden ska accepteras."""
    org = await create_org(client)
    valid_categories = ["verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"]
    for cat in valid_categories:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"System {cat}",
            "description": "Test",
            "system_category": cat,
        })
        assert resp.status_code == 201, (
            f"Kategori {cat!r} avvisades: {resp.status_code} {resp.text}"
        )
        assert resp.json()["system_category"] == cat


@pytest.mark.asyncio
async def test_compliance_business_area_field(client):
    """business_area ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], business_area="Individ och familjeomsorgen")
    assert sys["business_area"] == "Individ och familjeomsorgen"


@pytest.mark.asyncio
async def test_compliance_organization_id_in_response(client):
    """organization_id ska returneras i systemresponsen."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert "organization_id" in sys
    assert sys["organization_id"] == org["id"]


# ---------------------------------------------------------------------------
# Kat 3: Säkerhetsklassning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_criticality_all_values(client):
    """Alla giltiga criticality-värden (låg, medel, hög, kritisk) ska accepteras."""
    org = await create_org(client)
    for crit in ["låg", "medel", "hög", "kritisk"]:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"Criticality {crit}",
            "description": "Test",
            "system_category": "verksamhetssystem",
            "criticality": crit,
        })
        assert resp.status_code == 201, f"criticality={crit!r} avvisades"
        assert resp.json()["criticality"] == crit


@pytest.mark.asyncio
async def test_compliance_has_elevated_protection_field(client):
    """has_elevated_protection ska kunna sättas till True/False."""
    org = await create_org(client)
    sys_high = await create_system(client, org["id"], has_elevated_protection=True)
    sys_low = await create_system(client, org["id"], has_elevated_protection=False)
    assert sys_high["has_elevated_protection"] is True
    assert sys_low["has_elevated_protection"] is False


@pytest.mark.asyncio
async def test_compliance_security_protection_field(client):
    """security_protection ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], security_protection=True)
    assert "security_protection" in sys
    assert sys["security_protection"] is True


@pytest.mark.asyncio
async def test_compliance_nis2_applicable_field(client):
    """nis2_applicable ska kunna sättas till True och returneras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], nis2_applicable=True)
    assert sys["nis2_applicable"] is True


@pytest.mark.asyncio
async def test_compliance_nis2_classification_values(client):
    """nis2_classification ska acceptera väsentlig, viktig, ej_tillämplig."""
    org = await create_org(client)
    for val in ["väsentlig", "viktig", "ej_tillämplig"]:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"NIS2 {val}",
            "description": "Test",
            "system_category": "infrastruktur",
            "nis2_classification": val,
        })
        assert resp.status_code == 201, f"nis2_classification={val!r} avvisades"
        assert resp.json()["nis2_classification"] == val


@pytest.mark.asyncio
async def test_compliance_classification_krtv_values(client):
    """Klassningsvärdena K/R/T/S (confidentiality/integrity/availability/traceability) ska acceptera 0-4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for val in [0, 1, 2, 3, 4]:
        resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
            "system_id": sys["id"],
            "confidentiality": val,
            "integrity": val,
            "availability": val,
            "classified_by": "test@test.se",
        })
        assert resp.status_code == 201, (
            f"Klassningsvärde {val} avvisades: {resp.status_code} {resp.text}"
        )


@pytest.mark.asyncio
async def test_compliance_classification_traceability_optional(client):
    """traceability är ett valfritt klassningsvärde (0-4)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "system_id": sys["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "traceability": 3,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("traceability") == 3


# ---------------------------------------------------------------------------
# Kat 4: GDPR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_treats_personal_data_field(client):
    """treats_personal_data ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    assert sys["treats_personal_data"] is True


@pytest.mark.asyncio
async def test_compliance_treats_sensitive_data_field(client):
    """treats_sensitive_data ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_sensitive_data=True)
    assert sys["treats_sensitive_data"] is True


@pytest.mark.asyncio
async def test_compliance_third_country_transfer_field(client):
    """third_country_transfer ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], third_country_transfer=True)
    assert sys["third_country_transfer"] is True


@pytest.mark.asyncio
async def test_compliance_gdpr_ropa_reference_id(client):
    """GDPR treatment: ropa_reference_id ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"], ropa_reference_id="ROPA-2024-001")
    assert gdpr.get("ropa_reference_id") == "ROPA-2024-001"


@pytest.mark.asyncio
async def test_compliance_gdpr_data_categories_field(client):
    """GDPR treatment: data_categories ska lagras som lista."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    categories = ["vanliga", "känsliga", "personnummer"]
    gdpr = await create_gdpr_treatment(client, sys["id"], data_categories=categories)
    assert gdpr.get("data_categories") is not None
    assert isinstance(gdpr["data_categories"], list)


@pytest.mark.asyncio
async def test_compliance_gdpr_legal_basis_field(client):
    """GDPR treatment: legal_basis ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        legal_basis="Rättslig förpliktelse (art. 6.1 c)")
    assert gdpr.get("legal_basis") == "Rättslig förpliktelse (art. 6.1 c)"


@pytest.mark.asyncio
async def test_compliance_gdpr_processor_agreement_status(client):
    """GDPR treatment: processor_agreement_status ska acceptera alla giltiga värden."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    for status in ["ja", "nej", "under_framtagande", "ej_tillämpligt"]:
        gdpr = await create_gdpr_treatment(client, sys["id"],
                                            processor_agreement_status=status)
        assert gdpr.get("processor_agreement_status") == status


@pytest.mark.asyncio
async def test_compliance_gdpr_dpia_fields(client):
    """GDPR treatment: dpia_conducted, dpia_date, dpia_link ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    dpia_date = (date.today() - timedelta(days=30)).isoformat()
    gdpr = await create_gdpr_treatment(
        client, sys["id"],
        dpia_conducted=True,
        dpia_date=dpia_date,
        dpia_link="https://example.com/dpia-2024.pdf",
    )
    assert gdpr["dpia_conducted"] is True
    assert gdpr.get("dpia_date") == dpia_date
    assert gdpr.get("dpia_link") == "https://example.com/dpia-2024.pdf"


@pytest.mark.asyncio
async def test_compliance_gdpr_retention_policy_field(client):
    """GDPR treatment: retention_policy ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    gdpr = await create_gdpr_treatment(client, sys["id"],
                                        retention_policy="5 år efter avslutat ärende")
    assert gdpr.get("retention_policy") == "5 år efter avslutat ärende"


# ---------------------------------------------------------------------------
# Kat 5: Hosting och produkt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_hosting_model_field(client):
    """hosting_model ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], hosting_model="cloud")
    assert sys["hosting_model"] == "cloud"


@pytest.mark.asyncio
async def test_compliance_cloud_provider_field(client):
    """cloud_provider ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], cloud_provider="Microsoft Azure")
    assert sys["cloud_provider"] == "Microsoft Azure"


@pytest.mark.asyncio
async def test_compliance_data_location_country_field(client):
    """data_location_country ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], data_location_country="Sverige")
    assert sys["data_location_country"] == "Sverige"


@pytest.mark.asyncio
async def test_compliance_product_name_field(client):
    """product_name ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], product_name="Procapita")
    assert sys["product_name"] == "Procapita"


@pytest.mark.asyncio
async def test_compliance_product_version_field(client):
    """product_version ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], product_version="12.3.4")
    assert sys["product_version"] == "12.3.4"


# ---------------------------------------------------------------------------
# Kat 6: Livscykel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_lifecycle_status_all_values(client):
    """Alla lifecycle_status-värden ska accepteras."""
    org = await create_org(client)
    for status in ["planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"]:
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"Status {status}",
            "description": "Test",
            "system_category": "verksamhetssystem",
            "lifecycle_status": status,
        })
        assert resp.status_code == 201, f"lifecycle_status={status!r} avvisades"
        assert resp.json()["lifecycle_status"] == status


@pytest.mark.asyncio
async def test_compliance_deployment_date_field(client):
    """deployment_date ska kunna sättas och returneras."""
    org = await create_org(client)
    d = "2022-06-15"
    sys = await create_system(client, org["id"], deployment_date=d)
    assert sys["deployment_date"] == d


@pytest.mark.asyncio
async def test_compliance_planned_decommission_date_field(client):
    """planned_decommission_date ska kunna sättas och returneras."""
    org = await create_org(client)
    d = "2028-12-31"
    sys = await create_system(client, org["id"], planned_decommission_date=d)
    assert sys["planned_decommission_date"] == d


@pytest.mark.asyncio
async def test_compliance_end_of_support_date_field(client):
    """end_of_support_date ska kunna sättas och returneras."""
    org = await create_org(client)
    d = "2027-03-01"
    sys = await create_system(client, org["id"], end_of_support_date=d)
    assert sys["end_of_support_date"] == d


# ---------------------------------------------------------------------------
# Kat 7: Integrationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_integration_source_target_fields(client):
    """Integration ska ha source_system_id och target_system_id."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Källa")
    tgt = await create_system(client, org["id"], name="Mål")
    intg = await create_integration(client, src["id"], tgt["id"])
    assert intg["source_system_id"] == src["id"]
    assert intg["target_system_id"] == tgt["id"]


@pytest.mark.asyncio
async def test_compliance_integration_type_all_values(client):
    """integration_type ska acceptera api, filöverföring, databasreplikering, event, manuell."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Avsändarsystem")
    tgt = await create_system(client, org["id"], name="Mottagarsystem")
    for itype in ["api", "filöverföring", "databasreplikering", "event", "manuell"]:
        resp = await client.post("/api/v1/integrations/", json={
            "source_system_id": src["id"],
            "target_system_id": tgt["id"],
            "integration_type": itype,
        })
        assert resp.status_code == 201, (
            f"integration_type={itype!r} avvisades: {resp.status_code} {resp.text}"
        )
        assert resp.json()["integration_type"] == itype


@pytest.mark.asyncio
async def test_compliance_integration_data_types_field(client):
    """integration: data_types ska kunna sättas."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Int Src")
    tgt = await create_system(client, org["id"], name="Int Tgt")
    intg = await create_integration(client, src["id"], tgt["id"],
                                     data_types="Personuppgifter, ärendedata")
    assert intg.get("data_types") == "Personuppgifter, ärendedata"


@pytest.mark.asyncio
async def test_compliance_integration_is_external_field(client):
    """integration: is_external ska kunna sättas till True."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Internal Src")
    tgt = await create_system(client, org["id"], name="External Tgt")
    intg = await create_integration(client, src["id"], tgt["id"],
                                     is_external=True,
                                     external_party="Skatteverket")
    assert intg["is_external"] is True
    assert intg.get("external_party") == "Skatteverket"


@pytest.mark.asyncio
async def test_compliance_integration_criticality_field(client):
    """integration: criticality ska kunna sättas."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Crit Src")
    tgt = await create_system(client, org["id"], name="Crit Tgt")
    intg = await create_integration(client, src["id"], tgt["id"], criticality="hög")
    assert intg.get("criticality") == "hög"


# ---------------------------------------------------------------------------
# Kat 8: Avtal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_contract_supplier_name(client):
    """contract: supplier_name ska lagras och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], supplier_name="CGI Sverige AB")
    assert contract["supplier_name"] == "CGI Sverige AB"


@pytest.mark.asyncio
async def test_compliance_contract_supplier_org_number(client):
    """contract: supplier_org_number ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"],
                                      supplier_org_number="556841-8049")
    assert contract.get("supplier_org_number") == "556841-8049"


@pytest.mark.asyncio
async def test_compliance_contract_start_end_dates(client):
    """contract: contract_start och contract_end ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(
        client, sys["id"],
        contract_start="2024-01-01",
        contract_end="2026-12-31",
    )
    assert contract.get("contract_start") == "2024-01-01"
    assert contract.get("contract_end") == "2026-12-31"


@pytest.mark.asyncio
async def test_compliance_contract_auto_renewal_field(client):
    """contract: auto_renewal ska kunna sättas till True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], auto_renewal=True)
    assert contract["auto_renewal"] is True


@pytest.mark.asyncio
async def test_compliance_contract_notice_period_months(client):
    """contract: notice_period_months ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], notice_period_months=3)
    assert contract.get("notice_period_months") == 3


@pytest.mark.asyncio
async def test_compliance_contract_sla_description(client):
    """contract: sla_description ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"],
                                      sla_description="99.9% tillgänglighet, 4h responstid")
    assert contract.get("sla_description") == "99.9% tillgänglighet, 4h responstid"


@pytest.mark.asyncio
async def test_compliance_contract_license_model(client):
    """contract: license_model ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], license_model="Per användare")
    assert contract.get("license_model") == "Per användare"


@pytest.mark.asyncio
async def test_compliance_contract_annual_costs(client):
    """contract: annual_license_cost och annual_operations_cost ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(
        client, sys["id"],
        annual_license_cost=250000.0,
        annual_operations_cost=75000.0,
    )
    assert contract.get("annual_license_cost") == 250000.0
    assert contract.get("annual_operations_cost") == 75000.0


@pytest.mark.asyncio
async def test_compliance_contract_procurement_type(client):
    """contract: procurement_type ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"],
                                      procurement_type="Upphandling LOU")
    assert contract.get("procurement_type") == "Upphandling LOU"


@pytest.mark.asyncio
async def test_compliance_contract_support_level(client):
    """contract: support_level ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"], support_level="Premium 24/7")
    assert contract.get("support_level") == "Premium 24/7"


# ---------------------------------------------------------------------------
# Kat 9: Backup och kontinuitet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_backup_frequency_field(client):
    """backup_frequency ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], backup_frequency="dagligen")
    assert sys["backup_frequency"] == "dagligen"


@pytest.mark.asyncio
async def test_compliance_rpo_field(client):
    """rpo (Recovery Point Objective) ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rpo="4 timmar")
    assert sys["rpo"] == "4 timmar"


@pytest.mark.asyncio
async def test_compliance_rto_field(client):
    """rto (Recovery Time Objective) ska kunna sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], rto="8 timmar")
    assert sys["rto"] == "8 timmar"


@pytest.mark.asyncio
async def test_compliance_dr_plan_exists_field(client):
    """dr_plan_exists ska kunna sättas till True."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], dr_plan_exists=True)
    assert sys["dr_plan_exists"] is True


# ---------------------------------------------------------------------------
# Kat 11: Audit log-fält
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_audit_endpoint_returns_list(client):
    """GET /audit/ ska returnera en lista med pagination."""
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_compliance_audit_entry_has_table_name(client):
    """Audit entries ska ha table_name-fältet."""
    org = await create_org(client)
    await create_system(client, org["id"])
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    items = resp.json()["items"]
    for item in items:
        assert "table_name" in item, "Audit entry saknar table_name"


@pytest.mark.asyncio
async def test_compliance_audit_entry_has_action_field(client):
    """Audit entries ska ha action-fältet."""
    org = await create_org(client)
    await create_system(client, org["id"])
    resp = await client.get("/api/v1/audit/")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "action" in item, "Audit entry saknar action"


@pytest.mark.asyncio
async def test_compliance_audit_record_endpoint_works(client):
    """GET /audit/record/{id} ska returnera en lista."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.get(f"/api/v1/audit/record/{sys['id']}")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Kat 12: Risk och referens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_last_risk_assessment_date_field(client):
    """last_risk_assessment_date ska kunna sättas och returneras."""
    org = await create_org(client)
    d = "2025-11-01"
    sys = await create_system(client, org["id"], last_risk_assessment_date=d)
    assert sys["last_risk_assessment_date"] == d


@pytest.mark.asyncio
async def test_compliance_klassa_reference_id_field(client):
    """klassa_reference_id ska kunna sättas och returneras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], klassa_reference_id="KLASSA-2024-042")
    assert sys["klassa_reference_id"] == "KLASSA-2024-042"


# ---------------------------------------------------------------------------
# Flexibelt: extended_attributes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_extended_attributes_jsonb(client):
    """extended_attributes ska acceptera godtycklig JSONB-data."""
    org = await create_org(client)
    attrs = {
        "intern_referens": "PRJ-2024-001",
        "ansvarig_avdelning": "IT-avdelningen",
        "antal_licenser": 150,
    }
    sys = await create_system(client, org["id"], extended_attributes=attrs)
    assert sys["extended_attributes"] is not None
    assert sys["extended_attributes"]["intern_referens"] == "PRJ-2024-001"


@pytest.mark.asyncio
async def test_compliance_extended_attributes_empty_dict(client):
    """extended_attributes ska acceptera tom dict."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], extended_attributes={})
    # Tom dict ska accepteras utan fel
    assert sys is not None


@pytest.mark.asyncio
async def test_compliance_extended_attributes_nested_json(client):
    """extended_attributes ska acceptera nästlad JSON."""
    org = await create_org(client)
    attrs = {
        "kontakter": [
            {"namn": "Alice", "roll": "Systemägare"},
            {"namn": "Bob", "roll": "Förvaltare"},
        ],
        "metadata": {"version": 2, "senast_granskad": "2024-11-01"},
    }
    sys = await create_system(client, org["id"], extended_attributes=attrs)
    assert sys["extended_attributes"] is not None


# ---------------------------------------------------------------------------
# Ägare och roller
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_owner_roles_all_values(client):
    """Alla ägarroller ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    roles = [
        "systemägare", "informationsägare", "systemförvaltare",
        "teknisk_förvaltare", "it_kontakt", "dataskyddsombud",
    ]
    for role in roles:
        resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
            "system_id": sys["id"],
            "organization_id": org["id"],
            "role": role,
            "name": f"Person {role}",
        })
        assert resp.status_code == 201, (
            f"Ägarroll {role!r} avvisades: {resp.status_code} {resp.text}"
        )
        assert resp.json()["role"] == role


@pytest.mark.asyncio
async def test_compliance_system_created_at_field(client):
    """Nyskapat system ska ha created_at-tidsstämpel."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert "created_at" in sys
    assert sys["created_at"] is not None


@pytest.mark.asyncio
async def test_compliance_system_updated_at_field(client):
    """System ska ha updated_at-tidsstämpel."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    assert "updated_at" in sys
    assert sys["updated_at"] is not None
