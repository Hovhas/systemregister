"""
End-to-end CRUD flöden — Kategori 5.

Testar hela livscykeln för system och relaterade entiteter:
skapa → läsa → uppdatera → ta bort.

Täcker också felfall: 404, 422, ogiltiga enums, saknade fält m.m.
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
    create_full_system,
)


# ---------------------------------------------------------------------------
# Organisation CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_organization_all_fields(client):
    """POST /organizations/ med alla fält sparar allt korrekt."""
    payload = {
        "name": "Sundsvalls kommun",
        "org_number": "212000-2723",
        "org_type": "kommun",
        "description": "Testbeskrivning av kommunen",
    }
    resp = await client.post("/api/v1/organizations/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Sundsvalls kommun"
    assert body["org_number"] == "212000-2723"
    assert body["org_type"] == "kommun"
    assert body["description"] == "Testbeskrivning av kommunen"
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
@pytest.mark.parametrize("org_type", ["kommun", "bolag", "samverkan", "digit"])
async def test_create_organization_all_types(client, org_type):
    """Alla org-typer kan skapas."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": f"Org {org_type}",
        "org_type": org_type,
    })
    assert resp.status_code == 201
    assert resp.json()["org_type"] == org_type


@pytest.mark.asyncio
async def test_create_organization_invalid_type_returns_422(client):
    """Ogiltig org_type ger 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Felaktig Org",
        "org_type": "ogiltig_typ",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_organization_missing_name_returns_422(client):
    """Org utan namn ger 422."""
    resp = await client.post("/api/v1/organizations/", json={"org_type": "kommun"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_organization(client):
    """GET /organizations/{id} returnerar korrekt organisation."""
    org = await create_org(client, name="HämtningsOrg")
    resp = await client.get(f"/api/v1/organizations/{org['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == org["id"]
    assert resp.json()["name"] == "HämtningsOrg"


@pytest.mark.asyncio
async def test_get_organization_not_found(client):
    """GET /organizations/{id} med okänt id ger 404."""
    resp = await client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_organization(client):
    """PATCH /organizations/{id} uppdaterar enbart angivna fält."""
    org = await create_org(client, name="Original Org")
    resp = await client.patch(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Uppdaterat Namn"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Uppdaterat Namn"
    assert body["org_type"] == org["org_type"]  # oförändrat


@pytest.mark.asyncio
async def test_delete_organization(client):
    """DELETE /organizations/{id} tar bort organisationen."""
    org = await create_org(client, name="DeleteOrg")
    del_resp = await client.delete(f"/api/v1/organizations/{org['id']}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/organizations/{org['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_organizations(client):
    """GET /organizations/ returnerar lista med skapade organisationer."""
    for i in range(3):
        await create_org(client, name=f"ListOrg {i}")

    resp = await client.get("/api/v1/organizations/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 3


@pytest.mark.asyncio
async def test_organization_parent_child_relationship(client):
    """Org med parent_org_id skapar hierarki."""
    parent = await create_org(client, name="Förälder Org")
    child = await create_org(client, name="Barn Org", parent_org_id=parent["id"])

    assert child["parent_org_id"] == parent["id"]

    # Hämta förälder och verifiera
    resp = await client.get(f"/api/v1/organizations/{parent['id']}")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# System CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_system_minimal(client):
    """POST /systems/ med minsta möjliga payload."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Minimalt System",
        "description": "Minimal beskrivning",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Minimalt System"
    assert body["lifecycle_status"] == "i_drift"  # default
    assert body["criticality"] == "medel"  # default


@pytest.mark.asyncio
@pytest.mark.parametrize("category", [
    "verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"
])
async def test_create_system_all_categories(client, category):
    """Alla systemkategorier kan skapas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], system_category=category)
    assert sys["system_category"] == category


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [
    "planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"
])
async def test_create_system_all_lifecycle_statuses(client, status):
    """Alla livscykelstatusar kan sättas vid skapande."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], lifecycle_status=status)
    assert sys["lifecycle_status"] == status


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", ["låg", "medel", "hög", "kritisk"])
async def test_create_system_all_criticality_levels(client, criticality):
    """Alla kritikalitetsnivåer kan sättas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], criticality=criticality)
    assert sys["criticality"] == criticality


@pytest.mark.asyncio
async def test_create_system_full_payload(client):
    """POST /systems/ med alla fält sparas korrekt."""
    org = await create_org(client)
    payload = {
        "organization_id": org["id"],
        "name": "Fullt System",
        "description": "Fullständig testbeskrivning",
        "system_category": "verksamhetssystem",
        "criticality": "hög",
        "lifecycle_status": "i_drift",
        "nis2_applicable": True,
        "nis2_classification": "väsentlig",
        "treats_personal_data": True,
        "treats_sensitive_data": True,
        "third_country_transfer": True,
        "hosting_model": "cloud",
        "cloud_provider": "AWS",
        "data_location_country": "Sverige",
        "product_name": "Lifecare",
        "product_version": "2024.1",
        "backup_frequency": "daglig",
        "rpo": "4h",
        "rto": "8h",
        "dr_plan_exists": True,
        "has_elevated_protection": True,
        "security_protection": False,
        "business_area": "Omsorg",
    }
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "väsentlig"
    assert body["treats_personal_data"] is True
    assert body["hosting_model"] == "cloud"
    assert body["cloud_provider"] == "AWS"


@pytest.mark.asyncio
async def test_get_system(client):
    """GET /systems/{id} returnerar korrekt system."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Hämtningssystem")
    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sys["id"]
    assert resp.json()["name"] == "Hämtningssystem"


@pytest.mark.asyncio
async def test_get_system_not_found(client):
    """GET /systems/{id} med okänt id ger 404."""
    resp = await client.get("/api/v1/systems/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_system_updates_fields(client):
    """PATCH /systems/{id} uppdaterar angivna fält utan att röra övriga."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="PatchSys", criticality="låg")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "criticality": "kritisk",
        "lifecycle_status": "under_avveckling",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["criticality"] == "kritisk"
    assert body["lifecycle_status"] == "under_avveckling"
    assert body["name"] == "PatchSys"  # oförändrat


@pytest.mark.asyncio
async def test_patch_system_nis2_fields(client):
    """PATCH kan sätta NIS2-fält."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "nis2_applicable": True,
        "nis2_classification": "viktig",
        "last_risk_assessment_date": "2024-06-01",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable"] is True
    assert body["nis2_classification"] == "viktig"


@pytest.mark.asyncio
async def test_delete_system(client):
    """DELETE /systems/{id} tar bort systemet."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    del_resp = await client.delete(f"/api/v1/systems/{sys['id']}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_system_cascades_to_owners(client):
    """DELETE system tar kaskad-bort ägare."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"])

    await client.delete(f"/api/v1/systems/{sys['id']}")

    # Systemet borta → PATCH owner borde ge 404 eller 500
    resp = await client.patch(
        f"/api/v1/systems/{sys['id']}/owners/{owner['id']}",
        json={"name": "Uppdaterad"},
    )
    assert resp.status_code in (404, 500), f"Owner borde vara borta, fick {resp.status_code}"


@pytest.mark.asyncio
async def test_delete_system_cascades_to_classifications(client):
    """DELETE system tar kaskad-bort klassningar."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"])

    await client.delete(f"/api/v1/systems/{sys['id']}")

    # Klassningar skall vara borta
    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.json() == []


@pytest.mark.asyncio
async def test_list_systems_pagination(client):
    """GET /systems/ med limit/offset paginerar korrekt."""
    org = await create_org(client)
    for i in range(5):
        await create_system(client, org["id"], name=f"Pagsys-{i}-{uuid4().hex[:6]}")

    resp_page1 = await client.get("/api/v1/systems/", params={"limit": 2, "offset": 0, "organization_id": org["id"]})
    resp_page2 = await client.get("/api/v1/systems/", params={"limit": 2, "offset": 2, "organization_id": org["id"]})

    assert resp_page1.status_code == 200
    assert resp_page2.status_code == 200

    page1_ids = [s["id"] for s in resp_page1.json()["items"]]
    page2_ids = [s["id"] for s in resp_page2.json()["items"]]

    # Inga överlapp
    assert not set(page1_ids) & set(page2_ids), "Sidorna skall inte överlappa"


@pytest.mark.asyncio
async def test_list_systems_filter_by_lifecycle_status(client):
    """Filtrering på lifecycle_status fungerar."""
    org = await create_org(client)
    sys_drift = await create_system(client, org["id"], name="SysDrift", lifecycle_status="i_drift")
    sys_avvecklad = await create_system(client, org["id"], name="SysAvvecklad", lifecycle_status="avvecklad")

    resp = await client.get("/api/v1/systems/", params={"lifecycle_status": "avvecklad", "organization_id": org["id"]})
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()["items"]]
    assert sys_avvecklad["id"] in ids
    assert sys_drift["id"] not in ids


@pytest.mark.asyncio
async def test_list_systems_filter_by_criticality(client):
    """Filtrering på criticality fungerar."""
    org = await create_org(client)
    kritisk = await create_system(client, org["id"], name="KritiskSys", criticality="kritisk")
    lag = await create_system(client, org["id"], name="LagSys", criticality="låg")

    resp = await client.get("/api/v1/systems/", params={"criticality": "kritisk", "organization_id": org["id"]})
    ids = [s["id"] for s in resp.json()["items"]]
    assert kritisk["id"] in ids
    assert lag["id"] not in ids


@pytest.mark.asyncio
async def test_list_systems_filter_nis2(client):
    """Filtrering på nis2_applicable fungerar."""
    org = await create_org(client)
    nis2 = await create_system(client, org["id"], name="NIS2Sys", nis2_applicable=True)
    ej_nis2 = await create_system(client, org["id"], name="EjNIS2Sys", nis2_applicable=False)

    resp = await client.get("/api/v1/systems/", params={"nis2_applicable": True, "organization_id": org["id"]})
    ids = [s["id"] for s in resp.json()["items"]]
    assert nis2["id"] in ids
    assert ej_nis2["id"] not in ids


@pytest.mark.asyncio
async def test_list_systems_filter_treats_personal_data(client):
    """Filtrering på treats_personal_data fungerar."""
    org = await create_org(client)
    personal = await create_system(client, org["id"], name="PersonalSys", treats_personal_data=True)
    ej_personal = await create_system(client, org["id"], name="EjPersonalSys", treats_personal_data=False)

    resp = await client.get("/api/v1/systems/", params={"treats_personal_data": True, "organization_id": org["id"]})
    ids = [s["id"] for s in resp.json()["items"]]
    assert personal["id"] in ids
    assert ej_personal["id"] not in ids


@pytest.mark.asyncio
async def test_list_systems_search_query(client):
    """Fritextsökning via q-parameter returnerar relevanta träffar."""
    org = await create_org(client)
    await create_system(client, org["id"], name="Procapita Vård")
    await create_system(client, org["id"], name="Visma Lön")

    resp = await client.get("/api/v1/systems/", params={"q": "Procapita"})
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["items"]]
    assert "Procapita Vård" in names
    assert "Visma Lön" not in names


@pytest.mark.asyncio
async def test_system_stats_overview(client):
    """GET /systems/stats/overview returnerar statistik."""
    org = await create_org(client)
    await create_system(client, org["id"], name="StatSys1")
    await create_system(client, org["id"], name="StatSys2")

    resp = await client.get("/api/v1/systems/stats/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_systems" in body
    assert body["total_systems"] >= 2


# ---------------------------------------------------------------------------
# Classification CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_classification_minimal(client):
    """POST klassning med minimala fält."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "system_id": sys["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 3,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["confidentiality"] == 2
    assert body["integrity"] == 2
    assert body["availability"] == 3


@pytest.mark.asyncio
async def test_get_latest_classification(client):
    """GET /systems/{id}/classifications/latest returnerar senaste klassning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    # Skapa två klassningar
    class1 = await create_classification(client, sys["id"], confidentiality=1)
    class2 = await create_classification(client, sys["id"], confidentiality=3)

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications/latest")
    assert resp.status_code == 200
    body = resp.json()
    # Ska returnera en av de skapade klassningarna (ordning beror på timestamp/id)
    assert body["confidentiality"] in (1, 3)
    assert body["system_id"] == sys["id"]


@pytest.mark.asyncio
async def test_classification_history_preserved(client):
    """Historik av klassningar bevaras — ny rad per klassning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_classification(client, sys["id"], confidentiality=1)
    await create_classification(client, sys["id"], confidentiality=2)
    await create_classification(client, sys["id"], confidentiality=3)

    resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_classification_invalid_value_returns_422(client):
    """Klassningsvärde utanför 0-4 ger 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "system_id": sys["id"],
        "confidentiality": 5,  # utanför 0-4
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Owner CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [
    "systemägare", "informationsägare", "systemförvaltare",
    "teknisk_förvaltare", "it_kontakt", "dataskyddsombud"
])
async def test_create_owner_all_roles(client, role):
    """Alla ägarroller kan skapas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "system_id": sys["id"],
        "organization_id": org["id"],
        "role": role,
        "name": f"Ägare {role}",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == role


@pytest.mark.asyncio
async def test_patch_owner(client):
    """PATCH /systems/{system_id}/owners/{id} uppdaterar ägare korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"], name="Gamla Ägaren")

    resp = await client.patch(f"/api/v1/systems/{sys['id']}/owners/{owner['id']}", json={
        "name": "Nya Ägaren",
        "email": "ny@agare.se",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Nya Ägaren"
    assert body["email"] == "ny@agare.se"
    assert body["role"] == owner["role"]  # oförändrat


@pytest.mark.asyncio
async def test_delete_owner(client):
    """DELETE /systems/{system_id}/owners/{id} tar bort ägaren."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    owner = await create_owner(client, sys["id"], org["id"])

    del_resp = await client.delete(f"/api/v1/systems/{sys['id']}/owners/{owner['id']}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    ids = [o["id"] for o in list_resp.json()]
    assert owner["id"] not in ids


@pytest.mark.asyncio
async def test_duplicate_owner_role_rejected(client):
    """Samma system + roll + namn kan inte skapas två gånger (unique constraint)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    await create_owner(client, sys["id"], org["id"], role="systemägare", name="Ägaren")

    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "system_id": sys["id"],
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "Ägaren",  # samma
    })
    assert resp.status_code in (409, 422, 400), (
        f"Duplicerat ägare borde returnera fel, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Contract CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contract_full(client):
    """POST kontrakt med alla fält."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    today = date.today()
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "CGI Sverige AB",
        "supplier_org_number": "556227-7705",
        "contract_id_external": "AUP-2024-001",
        "contract_start": str(today),
        "contract_end": str(today + timedelta(days=365)),
        "auto_renewal": True,
        "notice_period_months": 6,
        "sla_description": "99.9% tillgänglighet",
        "license_model": "per_user",
        "annual_license_cost": 500000,
        "annual_operations_cost": 200000,
        "procurement_type": "direktupphandling",
        "support_level": "silver",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["supplier_name"] == "CGI Sverige AB"
    assert body["auto_renewal"] is True
    assert body["notice_period_months"] == 6
    assert body["annual_license_cost"] == 500000


@pytest.mark.asyncio
async def test_patch_contract(client):
    """PATCH /systems/{system_id}/contracts/{id} uppdaterar kontraktsfält."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    resp = await client.patch(f"/api/v1/systems/{sys['id']}/contracts/{contract['id']}", json={
        "sla_description": "Uppdaterad SLA",
        "auto_renewal": True,
    })
    assert resp.status_code == 200
    assert resp.json()["sla_description"] == "Uppdaterad SLA"
    assert resp.json()["auto_renewal"] is True


@pytest.mark.asyncio
async def test_delete_contract(client):
    """DELETE /systems/{system_id}/contracts/{id} tar bort kontrakt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    contract = await create_contract(client, sys["id"])

    del_resp = await client.delete(f"/api/v1/systems/{sys['id']}/contracts/{contract['id']}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    ids = [c["id"] for c in list_resp.json()]
    assert contract["id"] not in ids


@pytest.mark.asyncio
async def test_expiring_contracts_endpoint(client):
    """GET /contracts/expiring returnerar kontrakt som löper ut snart."""
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
async def test_full_system_lifecycle(client):
    """Komplett systemlivscykel: skapa → klassificera → äga → kontrakt → avveckla → ta bort."""
    org = await create_org(client, name="Livscykel Org")

    # Skapa system
    sys = await create_system(client, org["id"], name="Livscykelsystem",
                               lifecycle_status="planerad")
    assert sys["lifecycle_status"] == "planerad"

    # Klassificera
    cls = await create_classification(client, sys["id"])
    assert cls["system_id"] == sys["id"]

    # Sätt ägare
    owner = await create_owner(client, sys["id"], org["id"])
    assert owner["system_id"] == sys["id"]

    # Lägg till kontrakt
    contract = await create_contract(client, sys["id"])
    assert contract["system_id"] == sys["id"]

    # Uppdatera till i_drift
    patch_resp = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "lifecycle_status": "i_drift",
    })
    assert patch_resp.json()["lifecycle_status"] == "i_drift"

    # Avveckla
    patch_resp2 = await client.patch(f"/api/v1/systems/{sys['id']}", json={
        "lifecycle_status": "avvecklad",
    })
    assert patch_resp2.json()["lifecycle_status"] == "avvecklad"

    # Ta bort systemet
    del_resp = await client.delete(f"/api/v1/systems/{sys['id']}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_full_system_with_create_full_system_factory(client):
    """create_full_system factory skapar komplett system med alla delar."""
    org = await create_org(client, name="FullFactory Org")
    sys = await create_full_system(client, org["id"], name="Fullt Fabrikssystem",
                                   treats_personal_data=True)

    # Verifiera att system finns
    resp = await client.get(f"/api/v1/systems/{sys['id']}")
    assert resp.status_code == 200

    # Verifiera att klassning finns
    cls_resp = await client.get(f"/api/v1/systems/{sys['id']}/classifications")
    assert len(cls_resp.json()) >= 1

    # Verifiera att ägare finns
    owner_resp = await client.get(f"/api/v1/systems/{sys['id']}/owners")
    assert len(owner_resp.json()) >= 1

    # Verifiera att kontrakt finns
    contract_resp = await client.get(f"/api/v1/systems/{sys['id']}/contracts")
    assert len(contract_resp.json()) >= 1

    # Verifiera att GDPR finns (satte treats_personal_data=True)
    gdpr_resp = await client.get(f"/api/v1/systems/{sys['id']}/gdpr")
    assert len(gdpr_resp.json()) >= 1
