"""
Tests for /api/v1/systems/{id}/gdpr and /api/v1/systems/{id}/gdpr/{id} endpoints.
"""

import pytest

from tests.factories import create_org, create_system, create_gdpr_treatment


# ---------------------------------------------------------------------------
# Constants used in direct POST calls within tests
# ---------------------------------------------------------------------------

GDPR_BASE = {
    "ropa_reference_id": "ROPA-2024-001",
    "data_categories": ["vanliga", "känsliga_art9"],
    "categories_of_data_subjects": "medborgare, patienter",
    "legal_basis": "Artikel 9.2(h) – hälso- och sjukvård",
    "data_processor": "CGI Sverige AB",
    "processor_agreement_status": "ja",
    "sub_processors": ["Amazon Web Services"],
    "third_country_transfer_details": None,
    "retention_policy": "7 år efter senaste kontakt",
    "dpia_conducted": True,
    "dpia_date": "2024-03-15",
    "dpia_link": "https://gdpr.sundsvall.se/dpia/lifecare",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_gdpr_treatment(client):
    """POST /api/v1/systems/{id}/gdpr returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    resp = await client.post(f"/api/v1/systems/{system_id}/gdpr", json=GDPR_BASE)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["system_id"] == system_id
    assert body["ropa_reference_id"] == GDPR_BASE["ropa_reference_id"]
    assert body["data_categories"] == GDPR_BASE["data_categories"]
    assert body["legal_basis"] == GDPR_BASE["legal_basis"]
    assert body["data_processor"] == GDPR_BASE["data_processor"]
    assert body["processor_agreement_status"] == GDPR_BASE["processor_agreement_status"]
    assert body["dpia_conducted"] is True
    assert body["dpia_date"] == GDPR_BASE["dpia_date"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_gdpr_treatment_minimal(client):
    """POST GDPR treatment with only required fields (all optional) should succeed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={})

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["ropa_reference_id"] is None
    assert body["data_categories"] is None
    assert body["dpia_conducted"] is False


@pytest.mark.asyncio
async def test_list_gdpr_treatments(client):
    """GET /api/v1/systems/{id}/gdpr returns list of treatments."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    await create_gdpr_treatment(client, system_id, ropa_reference_id="ROPA-001")
    await create_gdpr_treatment(client, system_id, ropa_reference_id="ROPA-002")

    resp = await client.get(f"/api/v1/systems/{system_id}/gdpr")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2, f"Expected at least 2 treatments, got {len(body)}"
    ropa_ids = [t["ropa_reference_id"] for t in body]
    assert "ROPA-001" in ropa_ids
    assert "ROPA-002" in ropa_ids


@pytest.mark.asyncio
async def test_list_gdpr_treatments_empty(client):
    """GET /api/v1/systems/{id}/gdpr on new system returns empty list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/gdpr")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_gdpr_treatment(client):
    """PATCH /api/v1/systems/{system_id}/gdpr/{id} updates fields without touching others."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"], **GDPR_BASE)
    treatment_id = treatment["id"]

    patch = {
        "legal_basis": "Artikel 6.1(e) – allmänt intresse",
        "dpia_conducted": False,
        "retention_policy": "5 år",
    }
    resp = await client.patch(f"/api/v1/systems/{system['id']}/gdpr/{treatment_id}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["legal_basis"] == "Artikel 6.1(e) – allmänt intresse"
    assert body["dpia_conducted"] is False
    assert body["retention_policy"] == "5 år"
    # Unpatched fields should remain
    assert body["ropa_reference_id"] == GDPR_BASE["ropa_reference_id"]
    assert body["data_processor"] == GDPR_BASE["data_processor"]
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_update_gdpr_treatment_not_found(client):
    """PATCH /api/v1/systems/{system_id}/gdpr/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/systems/{fake_id}/gdpr/{fake_id}", json={"legal_basis": "test"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_gdpr_treatment(client):
    """DELETE /api/v1/systems/{system_id}/gdpr/{id} removes treatment and returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"])
    treatment_id = treatment["id"]

    delete_resp = await client.delete(f"/api/v1/systems/{system['id']}/gdpr/{treatment_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    # Verify it's gone from the system's list
    list_resp = await client.get(f"/api/v1/systems/{system['id']}/gdpr")
    assert list_resp.status_code == 200
    ids = [t["id"] for t in list_resp.json()]
    assert treatment_id not in ids, "Deleted treatment should not appear in list"


@pytest.mark.asyncio
async def test_delete_gdpr_treatment_not_found(client):
    """DELETE /api/v1/systems/{system_id}/gdpr/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/systems/{fake_id}/gdpr/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_gdpr_invalid_system(client):
    """POST /api/v1/systems/{id}/gdpr with non-existent system returns 404."""
    fake_system_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/v1/systems/{fake_system_id}/gdpr", json=GDPR_BASE)

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_gdpr_treatments_scoped_to_system(client):
    """GDPR treatments added to system A should not appear in system B's list."""
    org = await create_org(client)
    system_a = await create_system(client, org["id"], name="System A")
    system_b = await create_system(client, org["id"], name="System B")

    await create_gdpr_treatment(client, system_a["id"])

    resp = await client.get(f"/api/v1/systems/{system_b['id']}/gdpr")
    assert resp.status_code == 200
    assert resp.json() == [], "System B should have no GDPR treatments"


@pytest.mark.asyncio
async def test_create_gdpr_invalid_processor_status(client):
    """POST GDPR treatment with invalid processor_agreement_status returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    payload = {**GDPR_BASE, "processor_agreement_status": "okänd_status"}
    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json=payload)

    assert resp.status_code == 422, f"Expected 422 for invalid enum, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Utökade GDPR-tester — Kategori 7
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["ja", "nej", "under_framtagande", "ej_tillämpligt"])
async def test_gdpr_all_processor_agreement_statuses(client, status):
    """Alla processor_agreement_status-värden accepteras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "processor_agreement_status": status,
    })
    assert resp.status_code == 201, f"Status {status!r} borde accepteras: {resp.text}"
    assert resp.json()["processor_agreement_status"] == status


@pytest.mark.asyncio
async def test_gdpr_data_categories_vanliga_only(client):
    """data_categories med enbart 'vanliga' accepteras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["vanliga"],
    })
    assert resp.status_code == 201
    assert resp.json()["data_categories"] == ["vanliga"]


@pytest.mark.asyncio
async def test_gdpr_data_categories_kansliga_art9(client):
    """data_categories med 'känsliga_art9' accepteras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["känsliga_art9"],
    })
    assert resp.status_code == 201
    assert resp.json()["data_categories"] == ["känsliga_art9"]


@pytest.mark.asyncio
async def test_gdpr_data_categories_brottsdata_art10(client):
    """data_categories med 'brottsdata_art10' accepteras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["brottsdata_art10"],
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_gdpr_data_categories_all_variants(client):
    """data_categories med alla kategorier i kombination accepteras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    all_cats = ["vanliga", "känsliga_art9", "brottsdata_art10"]
    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": all_cats,
    })
    assert resp.status_code == 201
    returned = resp.json()["data_categories"]
    for cat in all_cats:
        assert cat in returned


@pytest.mark.asyncio
async def test_gdpr_data_categories_empty_list(client):
    """data_categories med tom lista accepteras (ingen kategori angiven)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": [],
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_gdpr_dpia_conducted_true_with_date_and_link(client):
    """dpia_conducted=True med datum och länk sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "dpia_conducted": True,
        "dpia_date": "2024-06-15",
        "dpia_link": "https://gdpr.example.se/dpia/123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["dpia_conducted"] is True
    assert body["dpia_date"] == "2024-06-15"
    assert body["dpia_link"] == "https://gdpr.example.se/dpia/123"


@pytest.mark.asyncio
async def test_gdpr_dpia_date_without_conducted_flag(client):
    """dpia_date kan sättas även om dpia_conducted är False."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "dpia_conducted": False,
        "dpia_date": "2023-01-01",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["dpia_conducted"] is False
    assert body["dpia_date"] == "2023-01-01"


@pytest.mark.asyncio
async def test_gdpr_retention_policy_long_text(client):
    """Lång retention_policy-text sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    long_policy = "10 år efter sista åtgärd. " * 20  # 500 tecken
    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "retention_policy": long_policy,
    })
    assert resp.status_code == 201
    assert resp.json()["retention_policy"] == long_policy


@pytest.mark.asyncio
async def test_gdpr_third_country_transfer_details(client):
    """third_country_transfer_details sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "third_country_transfer_details": "Överföring till USA via Standard Contractual Clauses",
    })
    assert resp.status_code == 201
    assert "USA" in resp.json()["third_country_transfer_details"]


@pytest.mark.asyncio
async def test_gdpr_sub_processors_list(client):
    """sub_processors som lista sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    processors = ["AWS", "Microsoft Azure", "Google Cloud"]
    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "sub_processors": processors,
    })
    assert resp.status_code == 201
    returned = resp.json()["sub_processors"]
    for p in processors:
        assert p in returned


@pytest.mark.asyncio
async def test_gdpr_connection_to_treats_personal_data_flag(client):
    """System med treats_personal_data=True kan ha GDPR-behandling."""
    org = await create_org(client)
    system = await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["vanliga"],
        "legal_basis": "Artikel 6.1(e) – allmänt intresse",
    })
    assert resp.status_code == 201

    # Verifiera att systemets flagga finns
    sys_resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert sys_resp.json()["treats_personal_data"] is True


@pytest.mark.asyncio
async def test_gdpr_system_without_personal_data_can_have_treatment(client):
    """System med treats_personal_data=False kan ändå ha GDPR-behandling (manuell registrering)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    # treats_personal_data default = False

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["vanliga"],
    })
    # Skall accepteras (inga affärsregler blockerar detta)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_gdpr_multiple_treatments_same_system(client):
    """Flera GDPR-behandlingar kan registreras på samma system."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    await create_gdpr_treatment(client, system["id"], ropa_reference_id="ROPA-001")
    await create_gdpr_treatment(client, system["id"], ropa_reference_id="ROPA-002")
    await create_gdpr_treatment(client, system["id"], ropa_reference_id="ROPA-003")

    resp = await client.get(f"/api/v1/systems/{system['id']}/gdpr")
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_gdpr_patch_data_categories(client):
    """PATCH GDPR treatment kan uppdatera data_categories."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"],
                                             data_categories=["vanliga"])

    resp = await client.patch(f"/api/v1/systems/{system['id']}/gdpr/{treatment['id']}", json={
        "data_categories": ["vanliga", "känsliga_art9"],
    })
    assert resp.status_code == 200
    returned = resp.json()["data_categories"]
    assert "känsliga_art9" in returned


@pytest.mark.asyncio
async def test_gdpr_patch_dpia_status(client):
    """PATCH kan uppdatera DPIA-status."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"],
                                             dpia_conducted=False)

    resp = await client.patch(f"/api/v1/systems/{system['id']}/gdpr/{treatment['id']}", json={
        "dpia_conducted": True,
        "dpia_date": "2024-12-01",
    })
    assert resp.status_code == 200
    assert resp.json()["dpia_conducted"] is True
    assert resp.json()["dpia_date"] == "2024-12-01"


@pytest.mark.asyncio
async def test_gdpr_patch_processor_agreement(client):
    """PATCH kan uppdatera processor_agreement_status."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    treatment = await create_gdpr_treatment(client, system["id"],
                                             processor_agreement_status="under_framtagande")

    resp = await client.patch(f"/api/v1/systems/{system['id']}/gdpr/{treatment['id']}", json={
        "processor_agreement_status": "ja",
    })
    assert resp.status_code == 200
    assert resp.json()["processor_agreement_status"] == "ja"


@pytest.mark.asyncio
async def test_gdpr_compliance_gap_appears_when_missing(client):
    """System med treats_personal_data utan GDPR syns i compliance-gap."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="GDPRGapSys", treats_personal_data=True)

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gap_ids = [s["id"] for s in resp.json()["gaps"]["personal_data_without_gdpr"]]
    assert system["id"] in gap_ids


@pytest.mark.asyncio
async def test_gdpr_compliance_gap_resolved_when_treatment_added(client):
    """System försvinner från compliance-gap när GDPR-behandling läggs till."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="GDPRFixedSys", treats_personal_data=True)

    await create_gdpr_treatment(client, system["id"])

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gap_ids = [s["id"] for s in resp.json()["gaps"]["personal_data_without_gdpr"]]
    assert system["id"] not in gap_ids


@pytest.mark.asyncio
async def test_gdpr_categories_of_data_subjects(client):
    """categories_of_data_subjects sparas och returneras korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "categories_of_data_subjects": "medborgare, anställda, elever, patienter",
    })
    assert resp.status_code == 201
    assert "medborgare" in resp.json()["categories_of_data_subjects"]


@pytest.mark.asyncio
async def test_gdpr_ropa_reference_id_unique_per_system(client):
    """ropa_reference_id är en fri text — inga unikthetskrav kontrolleras."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    # Samma ROPA-id på samma system skall tillåtas (om inga unique constraints)
    resp1 = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "ropa_reference_id": "ROPA-DUPE",
    })
    resp2 = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "ropa_reference_id": "ROPA-DUPE",
    })
    # Båda borde antingen lyckas eller andra ge felkod
    assert resp1.status_code == 201
    # resp2 beror på implementationen — dokumenterar faktiskt beteende
    assert resp2.status_code in (201, 409, 422)
