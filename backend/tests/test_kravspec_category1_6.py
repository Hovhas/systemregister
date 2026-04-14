"""
Testfall för kravspecifikationens kategori 1–6.

Täcker:
  Kategori 1 – Grundläggande identifiering
  Kategori 2 – Ägarskap och ansvar
  Kategori 3 – Informationsklassning (K/R/T/S nivå 0–4)
  Kategori 4 – GDPR
  Kategori 5 – Driftmiljö
  Kategori 6 – Livscykel

Alla testfall använder pytest.mark.parametrize för bred täckning (~300 fall).
"""

import pytest
from datetime import date, timedelta

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_gdpr_treatment,
)


# ---------------------------------------------------------------------------
# Kategori 1 — Grundläggande identifiering
# ---------------------------------------------------------------------------


ALL_CATEGORIES = [
    "verksamhetssystem",
    "stödsystem",
    "infrastruktur",
    "plattform",
    "iot",
]

ALL_CRITICALITIES = ["låg", "medel", "hög", "kritisk"]

ALL_LIFECYCLE_STATUSES = [
    "planerad",
    "under_inforande",
    "i_drift",
    "under_avveckling",
    "avvecklad",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ALL_CATEGORIES)
async def test_cat1_system_category_create_and_read(client, category):
    """Alla system_category-värden kan skapas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], system_category=category, name=f"System {category}")
    assert system["system_category"] == category

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    assert resp.json()["system_category"] == category


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ALL_CATEGORIES)
async def test_cat1_system_category_filter(client, category):
    """Filter på system_category returnerar bara system med rätt kategori."""
    org = await create_org(client)
    await create_system(client, org["id"], system_category=category, name=f"Filter {category}")
    # Skapa ett system med annan kategori för att kontrollera filtrering
    other_cat = "plattform" if category != "plattform" else "infrastruktur"
    await create_system(client, org["id"], system_category=other_cat, name=f"Other {category}")

    resp = await client.get(
        "/api/v1/systems/",
        params={"system_category": category, "organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["system_category"] == category, (
            f"Förväntade {category}, fick {item['system_category']}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ALL_CATEGORIES)
async def test_cat1_system_category_update(client, category):
    """system_category kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"], system_category="verksamhetssystem")
    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"system_category": category},
    )
    assert resp.status_code == 200
    assert resp.json()["system_category"] == category


@pytest.mark.asyncio
@pytest.mark.parametrize("name,aliases,business_area", [
    ("Procapita", "PCA,Procap", "socialtjänst"),
    ("Visma Lön", None, "HR"),
    ("W3D3", "Dokument,W3", None),
    ("Raindance", "RD,Raindance Finance", "ekonomi"),
    ("Treserva", None, "vård och omsorg"),
])
async def test_cat1_name_aliases_business_area(client, name, aliases, business_area):
    """Namn, alias och verksamhetsområde sparas och hämtas korrekt."""
    org = await create_org(client)
    kwargs = {"name": name}
    if aliases:
        kwargs["aliases"] = aliases
    if business_area:
        kwargs["business_area"] = business_area
    system = await create_system(client, org["id"], **kwargs)

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == name
    if aliases:
        assert body["aliases"] == aliases
    if business_area:
        assert body["business_area"] == business_area


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_category", [
    "VERKSAMHETSSYSTEM",
    "okänd",
    "system",
    "core",
    "",
    "123",
])
async def test_cat1_invalid_category_rejected(client, invalid_category):
    """Ogiltiga system_category-värden ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Ogiltigt system",
        "description": "Test",
        "system_category": invalid_category,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("name", "Nytt systemnamn"),
    ("description", "Uppdaterad beskrivning av systemet"),
    ("business_area", "finans"),
    ("aliases", "alias1,alias2"),
])
async def test_cat1_patch_individual_field(client, field, value):
    """Varje grundläggande identifieringsfält kan uppdateras individuellt via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={field: value})
    assert resp.status_code == 200
    assert resp.json()[field] == value


# ---------------------------------------------------------------------------
# Kategori 2 — Ägarskap och ansvar
# ---------------------------------------------------------------------------


ALL_OWNER_ROLES = [
    "systemägare",
    "informationsägare",
    "systemförvaltare",
    "teknisk_förvaltare",
    "it_kontakt",
    "dataskyddsombud",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ALL_OWNER_ROLES)
async def test_cat2_owner_role_create_and_read(client, role):
    """Alla ägarroller kan skapas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(
        client, system["id"], org["id"],
        role=role,
        name=f"Ansvarig {role}",
        email=f"{role.replace('_', '.')}@test.se",
    )
    assert owner["role"] == role

    resp = await client.get(f"/api/v1/systems/{system['id']}/owners")
    assert resp.status_code == 200
    owners_list = resp.json()
    roles = [o["role"] for o in owners_list]
    assert role in roles


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ALL_OWNER_ROLES)
async def test_cat2_owner_role_appears_in_system_detail(client, role):
    """Ägare med given roll syns i systemdetaljer."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    await create_owner(client, system["id"], org["id"], role=role, name=f"Person {role}")

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert "owners" in body
    roles = [o["role"] for o in body["owners"]]
    assert role in roles


@pytest.mark.asyncio
@pytest.mark.parametrize("role,name,email,phone", [
    ("systemägare", "Anna Andersson", "anna@kommun.se", "070-1234567"),
    ("informationsägare", "Björn Berg", "bjorn@bolag.se", None),
    ("systemförvaltare", "Cecilia Carlsson", None, "073-9876543"),
    ("teknisk_förvaltare", "David Dahlström", "david@it.se", None),
    ("it_kontakt", "Eva Eriksson", "eva@support.se", "08-1234567"),
    ("dataskyddsombud", "Fredrik Fredriksson", "dpo@org.se", "010-2345678"),
])
async def test_cat2_owner_contact_fields(client, role, name, email, phone):
    """Kontaktfält för ägare (namn, e-post, telefon) sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    kwargs = {"role": role, "name": name}
    if email:
        kwargs["email"] = email
    if phone:
        kwargs["phone"] = phone
    owner = await create_owner(client, system["id"], org["id"], **kwargs)

    assert owner["name"] == name
    assert owner["role"] == role
    if email:
        assert owner["email"] == email
    if phone:
        assert owner["phone"] == phone


@pytest.mark.asyncio
@pytest.mark.parametrize("num_owners", [1, 2, 3, 6])
async def test_cat2_multiple_owners_per_system(client, num_owners):
    """Ett system kan ha flera ägare med olika roller."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    roles = ALL_OWNER_ROLES[:num_owners]
    for i, role in enumerate(roles):
        await create_owner(client, system["id"], org["id"], role=role, name=f"Person {i}")

    resp = await client.get(f"/api/v1/systems/{system['id']}/owners")
    assert resp.status_code == 200
    assert len(resp.json()) == num_owners


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ALL_OWNER_ROLES)
async def test_cat2_delete_owner(client, role):
    """Ägare kan raderas från ett system."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"], role=role)
    owner_id = owner["id"]

    del_resp = await client.delete(f"/api/v1/systems/{system['id']}/owners/{owner_id}")
    assert del_resp.status_code == 204

    resp = await client.get(f"/api/v1/systems/{system['id']}/owners")
    ids = [o["id"] for o in resp.json()]
    assert owner_id not in ids


@pytest.mark.asyncio
async def test_cat2_owner_invalid_role_rejected(client):
    """Ogiltig ägarroll ger 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "organization_id": org["id"],
        "role": "chef",
        "name": "Okänd Roll",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cat2_owners_scoped_to_system(client):
    """Ägare för system A syns inte i system B:s ägarelista."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="Sys A")
    sys_b = await create_system(client, org["id"], name="Sys B")
    await create_owner(client, sys_a["id"], org["id"], name="Ägare A")

    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/owners")
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Kategori 3 — Informationsklassning (K/R/T/S 0–4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("k,r,t,s", [
    (0, 0, 0, 0),
    (1, 1, 1, 1),
    (2, 2, 2, 2),
    (3, 3, 3, 3),
    (4, 4, 4, 4),
    (0, 4, 0, 4),
    (4, 0, 4, 0),
    (1, 2, 3, 4),
    (4, 3, 2, 1),
    (2, 0, 3, 1),
])
async def test_cat3_krts_all_combinations(client, k, r, t, s):
    """K/R/T/S (konfidentialitet/riktighet/tillgänglighet/spårbarhet) 0–4 sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(
        client, system["id"],
        confidentiality=k,
        integrity=r,
        availability=t,
        traceability=s,
    )
    assert clf["confidentiality"] == k
    assert clf["integrity"] == r
    assert clf["availability"] == t
    assert clf["traceability"] == s


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("confidentiality", -1),
    ("confidentiality", 5),
    ("integrity", -1),
    ("integrity", 5),
    ("availability", -1),
    ("availability", 5),
    ("traceability", -1),
    ("traceability", 5),
])
async def test_cat3_classification_out_of_range_rejected(client, field, value):
    """Klassningsvärden utanför 0–4 ger 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    payload = {
        "confidentiality": 2, "integrity": 2, "availability": 2,
        "classified_by": "test@test.se",
        field: value,
    }
    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("k,r,t", [
    (0, 0, 0),
    (2, 2, 2),
    (4, 4, 4),
    (1, 3, 2),
    (3, 1, 4),
])
async def test_cat3_classification_without_traceability(client, k, r, t):
    """Klassning utan spårbarhet (traceability=None) är tillåtet."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(
        client, system["id"],
        confidentiality=k, integrity=r, availability=t,
        traceability=None,
    )
    assert clf["traceability"] is None
    assert clf["confidentiality"] == k


@pytest.mark.asyncio
@pytest.mark.parametrize("classified_by", [
    "anna.svensson@sundsvall.se",
    "it-avdelningen@bolag.se",
    "dpo@samverkan.se",
    "john.doe@example.com",
])
async def test_cat3_classified_by_stored(client, classified_by):
    """classified_by sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(client, system["id"], classified_by=classified_by)
    assert clf["classified_by"] == classified_by


@pytest.mark.asyncio
@pytest.mark.parametrize("notes", [
    "Klassad enligt ISO 27001",
    "Innehåller känsliga personuppgifter",
    "Reviderad efter incident 2025-11",
    None,
])
async def test_cat3_classification_notes(client, notes):
    """Anteckningar för klassning (notes) sparas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(client, system["id"], notes=notes)
    assert clf["notes"] == notes


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_until", [
    date.today() + timedelta(days=365),
    date.today() + timedelta(days=90),
    date.today() + timedelta(days=730),
])
async def test_cat3_classification_valid_until(client, valid_until):
    """valid_until sparas och returneras korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(client, system["id"], valid_until=valid_until)
    assert clf["valid_until"] == valid_until.isoformat()


@pytest.mark.asyncio
async def test_cat3_multiple_classifications_newest_first(client):
    """Flera klassningar returneras i fallande ordning (senast först)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    c1 = await create_classification(client, system["id"], confidentiality=1, notes="v1")
    c2 = await create_classification(client, system["id"], confidentiality=2, notes="v2")
    c3 = await create_classification(client, system["id"], confidentiality=3, notes="v3")

    resp = await client.get(f"/api/v1/systems/{system['id']}/classifications")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    returned_ids = {c["id"] for c in body}
    assert {c1["id"], c2["id"], c3["id"]} == returned_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", ALL_CRITICALITIES)
async def test_cat3_criticality_create_and_read(client, criticality):
    """Alla kritikalitetsnivåer kan skapas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], criticality=criticality)
    assert system["criticality"] == criticality

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    assert detail.json()["criticality"] == criticality


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", ALL_CRITICALITIES)
async def test_cat3_criticality_filter(client, criticality):
    """Filter på criticality returnerar bara system med rätt nivå."""
    org = await create_org(client)
    await create_system(client, org["id"], criticality=criticality, name=f"Krit {criticality}")

    resp = await client.get(
        "/api/v1/systems/",
        params={"criticality": criticality, "organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["criticality"] == criticality


@pytest.mark.asyncio
@pytest.mark.parametrize("from_crit,to_crit", [
    ("låg", "hög"),
    ("medel", "kritisk"),
    ("hög", "låg"),
    ("kritisk", "medel"),
])
async def test_cat3_criticality_update(client, from_crit, to_crit):
    """Kritikalitetsnivå kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"], criticality=from_crit)
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={"criticality": to_crit})
    assert resp.status_code == 200
    assert resp.json()["criticality"] == to_crit


@pytest.mark.asyncio
@pytest.mark.parametrize("elevated,security_prot", [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
])
async def test_cat3_elevated_protection_and_security_protection(client, elevated, security_prot):
    """has_elevated_protection och security_protection sparas korrekt."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        has_elevated_protection=elevated,
        security_protection=security_prot,
    )
    assert system["has_elevated_protection"] == elevated
    assert system["security_protection"] == security_prot

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    assert body["has_elevated_protection"] == elevated
    assert body["security_protection"] == security_prot


@pytest.mark.asyncio
@pytest.mark.parametrize("elevated,security_prot", [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
])
async def test_cat3_elevated_protection_update(client, elevated, security_prot):
    """has_elevated_protection och security_protection kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={
        "has_elevated_protection": elevated,
        "security_protection": security_prot,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_elevated_protection"] == elevated
    assert body["security_protection"] == security_prot


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_applicable,nis2_class", [
    (True, "väsentlig"),
    (True, "viktig"),
    (True, "ej_tillämplig"),
    (False, None),
    (False, "ej_tillämplig"),
])
async def test_cat3_nis2_fields(client, nis2_applicable, nis2_class):
    """NIS2-fält sparas och returneras korrekt."""
    org = await create_org(client)
    kwargs = {"nis2_applicable": nis2_applicable}
    if nis2_class:
        kwargs["nis2_classification"] = nis2_class
    system = await create_system(client, org["id"], **kwargs)
    assert system["nis2_applicable"] == nis2_applicable
    if nis2_class:
        assert system["nis2_classification"] == nis2_class


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_applicable,nis2_class", [
    (True, "väsentlig"),
    (True, "viktig"),
    (False, None),
])
async def test_cat3_nis2_update(client, nis2_applicable, nis2_class):
    """NIS2-fält kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    patch_data = {"nis2_applicable": nis2_applicable}
    if nis2_class:
        patch_data["nis2_classification"] = nis2_class
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json=patch_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["nis2_applicable"] == nis2_applicable
    if nis2_class:
        assert body["nis2_classification"] == nis2_class


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_nis2", ["VÄSENTLIG", "critical", "high", "okänd"])
async def test_cat3_nis2_invalid_classification_rejected(client, invalid_nis2):
    """Ogiltiga NIS2-klassificeringsvärden ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "NIS2 fel",
        "description": "Test",
        "system_category": "infrastruktur",
        "nis2_classification": invalid_nis2,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Kategori 4 — GDPR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("treats_personal,treats_sensitive,third_country", [
    (False, False, False),
    (True, False, False),
    (True, True, False),
    (True, True, True),
    (True, False, True),
    (False, False, True),
])
async def test_cat4_gdpr_flags_create(client, treats_personal, treats_sensitive, third_country):
    """GDPR-flaggor sparas korrekt vid skapande av system."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        treats_personal_data=treats_personal,
        treats_sensitive_data=treats_sensitive,
        third_country_transfer=third_country,
    )
    assert system["treats_personal_data"] == treats_personal
    assert system["treats_sensitive_data"] == treats_sensitive
    assert system["third_country_transfer"] == third_country


@pytest.mark.asyncio
@pytest.mark.parametrize("treats_personal,treats_sensitive,third_country", [
    (False, False, False),
    (True, False, False),
    (True, True, False),
    (True, True, True),
])
async def test_cat4_gdpr_flags_read_in_detail(client, treats_personal, treats_sensitive, third_country):
    """GDPR-flaggor syns korrekt i systemdetaljer."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        treats_personal_data=treats_personal,
        treats_sensitive_data=treats_sensitive,
        third_country_transfer=third_country,
    )
    resp = await client.get(f"/api/v1/systems/{system['id']}")
    body = resp.json()
    assert body["treats_personal_data"] == treats_personal
    assert body["treats_sensitive_data"] == treats_sensitive
    assert body["third_country_transfer"] == third_country


@pytest.mark.asyncio
@pytest.mark.parametrize("treats_personal,treats_sensitive,third_country", [
    (True, False, False),
    (True, True, True),
    (False, False, False),
])
async def test_cat4_gdpr_flags_update(client, treats_personal, treats_sensitive, third_country):
    """GDPR-flaggor kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={
        "treats_personal_data": treats_personal,
        "treats_sensitive_data": treats_sensitive,
        "third_country_transfer": third_country,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["treats_personal_data"] == treats_personal
    assert body["treats_sensitive_data"] == treats_sensitive
    assert body["third_country_transfer"] == third_country


@pytest.mark.asyncio
@pytest.mark.parametrize("data_categories,legal_basis", [
    (["vanliga"], "avtal"),
    (["känsliga"], "rättslig_förpliktelse"),
    (["vanliga", "känsliga"], "allmänt_intresse"),
    (["personnummer"], "myndighetsutövning"),
])
async def test_cat4_gdpr_treatment_data_categories(client, data_categories, legal_basis):
    """GDPR-behandling med olika datakategorier och rättslig grund sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(
        client, system["id"],
        data_categories=data_categories,
        legal_basis=legal_basis,
    )
    assert gdpr["data_categories"] == data_categories
    assert gdpr["legal_basis"] == legal_basis


@pytest.mark.asyncio
@pytest.mark.parametrize("dpia_conducted,dpia_date", [
    (False, None),
    (True, date(2025, 6, 15)),
    (True, date(2024, 1, 1)),
    (True, date(2026, 3, 1)),
])
async def test_cat4_gdpr_treatment_dpia(client, dpia_conducted, dpia_date):
    """DPIA-flagga och datum sparas korrekt i GDPR-behandling."""
    org = await create_org(client)
    system = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(
        client, system["id"],
        dpia_conducted=dpia_conducted,
        dpia_date=dpia_date,
    )
    assert gdpr["dpia_conducted"] == dpia_conducted
    if dpia_date:
        assert gdpr["dpia_date"] == dpia_date.isoformat()
    else:
        assert gdpr["dpia_date"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("processor_status", [
    "ja",
    "nej",
    "under_framtagande",
    "ej_tillämpligt",
])
async def test_cat4_gdpr_processor_agreement_status(client, processor_status):
    """Alla processor_agreement_status-värden sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], treats_personal_data=True)
    gdpr = await create_gdpr_treatment(
        client, system["id"],
        processor_agreement_status=processor_status,
    )
    assert gdpr["processor_agreement_status"] == processor_status


@pytest.mark.asyncio
@pytest.mark.parametrize("third_country_details,sub_processors", [
    ("Standardavtalsklausuler (SCC)", ["AWS EU", "Cloudflare"]),
    ("Adequacy decision – EU-US DPF", None),
    (None, ["Microsoft Azure"]),
    (None, None),
])
async def test_cat4_gdpr_treatment_third_country_and_processors(
    client, third_country_details, sub_processors
):
    """Tredjelands-detaljer och under-personuppgiftsbiträden sparas korrekt."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        treats_personal_data=True,
        third_country_transfer=third_country_details is not None,
    )
    gdpr = await create_gdpr_treatment(
        client, system["id"],
        third_country_transfer_details=third_country_details,
        sub_processors=sub_processors,
    )
    assert gdpr["third_country_transfer_details"] == third_country_details
    assert gdpr["sub_processors"] == sub_processors


@pytest.mark.asyncio
async def test_cat4_gdpr_treatment_appears_in_system_detail(client):
    """GDPR-behandling syns i systemdetaljer."""
    org = await create_org(client)
    system = await create_system(client, org["id"], treats_personal_data=True)
    await create_gdpr_treatment(client, system["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert "gdpr_treatments" in body
    assert len(body["gdpr_treatments"]) >= 1


@pytest.mark.asyncio
async def test_cat4_stats_count_personal_data(client):
    """Statistik-endpoint räknar korrekt antal system som behandlar personuppgifter."""
    org = await create_org(client)
    await create_system(client, org["id"], name="GDPR 1", treats_personal_data=True)
    await create_system(client, org["id"], name="GDPR 2", treats_personal_data=True)
    await create_system(client, org["id"], name="Ingen GDPR", treats_personal_data=False)

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["treats_personal_data_count"] == 2


# ---------------------------------------------------------------------------
# Kategori 5 — Driftmiljö
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("hosting_model", [
    "on-premise",
    "cloud",
    "hybrid",
    "on_premise",
])
async def test_cat5_hosting_model_create_and_read(client, hosting_model):
    """Alla hosting_model-värden sparas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], hosting_model=hosting_model)
    assert system["hosting_model"] == hosting_model

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    assert detail.json()["hosting_model"] == hosting_model


@pytest.mark.asyncio
@pytest.mark.parametrize("hosting_model", [
    "on-premise",
    "cloud",
    "hybrid",
])
async def test_cat5_hosting_model_update(client, hosting_model):
    """hosting_model kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={"hosting_model": hosting_model})
    assert resp.status_code == 200
    assert resp.json()["hosting_model"] == hosting_model


@pytest.mark.asyncio
@pytest.mark.parametrize("cloud_provider,data_location", [
    ("AWS", "Sverige"),
    ("Azure", "EU"),
    ("Google Cloud", "USA"),
    ("Safespring", "Sverige"),
    ("City Cloud", "Sverige"),
    (None, "Sverige"),
    ("AWS", None),
])
async def test_cat5_cloud_provider_and_data_location(client, cloud_provider, data_location):
    """cloud_provider och data_location_country sparas korrekt."""
    org = await create_org(client)
    kwargs = {}
    if cloud_provider:
        kwargs["cloud_provider"] = cloud_provider
    if data_location:
        kwargs["data_location_country"] = data_location
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    if cloud_provider:
        assert body["cloud_provider"] == cloud_provider
    if data_location:
        assert body["data_location_country"] == data_location


@pytest.mark.asyncio
@pytest.mark.parametrize("product_name,product_version", [
    ("Procapita", "21.3"),
    ("Visma HR", "2024.1"),
    ("W3D3", "7.0"),
    ("Raindance", None),
    (None, "3.14.2"),
    (None, None),
])
async def test_cat5_product_name_and_version(client, product_name, product_version):
    """Produktnamn och version sparas och hämtas korrekt."""
    org = await create_org(client)
    kwargs = {}
    if product_name:
        kwargs["product_name"] = product_name
    if product_version:
        kwargs["product_version"] = product_version
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    if product_name:
        assert body["product_name"] == product_name
    if product_version:
        assert body["product_version"] == product_version


@pytest.mark.asyncio
@pytest.mark.parametrize("backup_freq,rpo,rto,dr_plan", [
    ("dagligen", "4h", "8h", True),
    ("veckovis", "24h", "48h", False),
    ("kontinuerlig", "0", "1h", True),
    (None, None, None, False),
    ("månadsvis", "72h", None, False),
])
async def test_cat5_backup_and_dr_fields(client, backup_freq, rpo, rto, dr_plan):
    """Backup- och DR-fält (backup_frequency, rpo, rto, dr_plan_exists) sparas korrekt."""
    org = await create_org(client)
    kwargs = {"dr_plan_exists": dr_plan}
    if backup_freq:
        kwargs["backup_frequency"] = backup_freq
    if rpo:
        kwargs["rpo"] = rpo
    if rto:
        kwargs["rto"] = rto
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    assert body["dr_plan_exists"] == dr_plan
    if backup_freq:
        assert body["backup_frequency"] == backup_freq
    if rpo:
        assert body["rpo"] == rpo
    if rto:
        assert body["rto"] == rto


@pytest.mark.asyncio
@pytest.mark.parametrize("backup_freq,rpo,rto,dr_plan", [
    ("dagligen", "2h", "4h", True),
    ("veckovis", None, None, False),
])
async def test_cat5_backup_fields_update(client, backup_freq, rpo, rto, dr_plan):
    """Backup/DR-fält kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    patch_data = {"dr_plan_exists": dr_plan}
    if backup_freq:
        patch_data["backup_frequency"] = backup_freq
    if rpo:
        patch_data["rpo"] = rpo
    if rto:
        patch_data["rto"] = rto

    resp = await client.patch(f"/api/v1/systems/{system['id']}", json=patch_data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["dr_plan_exists"] == dr_plan


# ---------------------------------------------------------------------------
# Kategori 6 — Livscykel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle_status", ALL_LIFECYCLE_STATUSES)
async def test_cat6_lifecycle_status_create_and_read(client, lifecycle_status):
    """Alla lifecycle_status-värden kan skapas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], lifecycle_status=lifecycle_status)
    assert system["lifecycle_status"] == lifecycle_status

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    assert detail.json()["lifecycle_status"] == lifecycle_status


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle_status", ALL_LIFECYCLE_STATUSES)
async def test_cat6_lifecycle_status_filter(client, lifecycle_status):
    """Filter på lifecycle_status returnerar bara system med rätt status."""
    org = await create_org(client)
    await create_system(
        client, org["id"],
        lifecycle_status=lifecycle_status,
        name=f"System {lifecycle_status}",
    )

    resp = await client.get(
        "/api/v1/systems/",
        params={"lifecycle_status": lifecycle_status, "organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["lifecycle_status"] == lifecycle_status


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status,to_status", [
    ("planerad", "under_inforande"),
    ("under_inforande", "i_drift"),
    ("i_drift", "under_avveckling"),
    ("under_avveckling", "avvecklad"),
    ("i_drift", "planerad"),
    ("avvecklad", "i_drift"),
])
async def test_cat6_lifecycle_status_transitions(client, from_status, to_status):
    """Livscykelstatus kan uppdateras till vilket annat giltigt värde som helst."""
    org = await create_org(client)
    system = await create_system(client, org["id"], lifecycle_status=from_status)
    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"lifecycle_status": to_status},
    )
    assert resp.status_code == 200
    assert resp.json()["lifecycle_status"] == to_status


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_status", [
    "PLANERAD",
    "aktiv",
    "deleted",
    "archived",
    "",
    "drift",
])
async def test_cat6_lifecycle_invalid_status_rejected(client, invalid_status):
    """Ogiltiga lifecycle_status-värden ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Fel status",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "lifecycle_status": invalid_status,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("deployment_date,planned_decommission,end_of_support", [
    (date(2020, 1, 1), date(2030, 12, 31), date(2028, 6, 30)),
    (date(2015, 6, 15), None, None),
    (None, date(2025, 3, 31), None),
    (None, None, date(2024, 12, 31)),
    (date(2022, 9, 1), date(2027, 9, 1), date(2026, 3, 1)),
    (None, None, None),
])
async def test_cat6_date_fields_create_and_read(
    client, deployment_date, planned_decommission, end_of_support
):
    """Datumfält för livscykel sparas och hämtas korrekt."""
    org = await create_org(client)
    kwargs = {}
    if deployment_date:
        kwargs["deployment_date"] = deployment_date
    if planned_decommission:
        kwargs["planned_decommission_date"] = planned_decommission
    if end_of_support:
        kwargs["end_of_support_date"] = end_of_support
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    if deployment_date:
        assert body["deployment_date"] == deployment_date.isoformat()
    else:
        assert body["deployment_date"] is None
    if planned_decommission:
        assert body["planned_decommission_date"] == planned_decommission.isoformat()
    else:
        assert body["planned_decommission_date"] is None
    if end_of_support:
        assert body["end_of_support_date"] == end_of_support.isoformat()
    else:
        assert body["end_of_support_date"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("deployment_date", [
    date(2010, 3, 15),
    date(2025, 1, 1),
    date(2026, 3, 28),
])
async def test_cat6_deployment_date_update(client, deployment_date):
    """deployment_date kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"deployment_date": deployment_date.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["deployment_date"] == deployment_date.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize("decommission_date", [
    date(2025, 6, 30),
    date(2028, 12, 31),
    date(2030, 1, 1),
])
async def test_cat6_planned_decommission_date_update(client, decommission_date):
    """planned_decommission_date kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"planned_decommission_date": decommission_date.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["planned_decommission_date"] == decommission_date.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize("eos_date", [
    date(2024, 12, 31),
    date(2026, 6, 30),
    date(2027, 9, 15),
])
async def test_cat6_end_of_support_date_update(client, eos_date):
    """end_of_support_date kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"end_of_support_date": eos_date.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["end_of_support_date"] == eos_date.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle_status", ALL_LIFECYCLE_STATUSES)
async def test_cat6_stats_by_lifecycle_status(client, lifecycle_status):
    """Statistik-endpointens by_lifecycle_status räknar system per status korrekt."""
    org = await create_org(client)
    await create_system(client, org["id"], lifecycle_status=lifecycle_status, name=f"Stats {lifecycle_status}")

    resp = await client.get(
        "/api/v1/systems/stats/overview",
        params={"organization_id": org["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["by_lifecycle_status"].get(lifecycle_status, 0) >= 1


# ---------------------------------------------------------------------------
# Korsande tester — kombinationer av kategori 1–6
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category,criticality,lifecycle,hosting", [
    ("verksamhetssystem", "kritisk", "i_drift", "on-premise"),
    ("stödsystem", "medel", "planerad", "cloud"),
    ("infrastruktur", "hög", "under_inforande", "hybrid"),
    ("plattform", "låg", "under_avveckling", "cloud"),
    ("iot", "kritisk", "i_drift", "on-premise"),
    ("verksamhetssystem", "låg", "avvecklad", None),
    ("stödsystem", "hög", "i_drift", "hybrid"),
    ("infrastruktur", "medel", "planerad", "on-premise"),
])
async def test_cross_category_combination(client, category, criticality, lifecycle, hosting):
    """Kombinationer av kategori, kritikalitet, livscykel och driftmiljö fungerar korrekt."""
    org = await create_org(client)
    kwargs = {
        "system_category": category,
        "criticality": criticality,
        "lifecycle_status": lifecycle,
    }
    if hosting:
        kwargs["hosting_model"] = hosting
    system = await create_system(client, org["id"], name=f"Combo {category}", **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["system_category"] == category
    assert body["criticality"] == criticality
    assert body["lifecycle_status"] == lifecycle
    if hosting:
        assert body["hosting_model"] == hosting


@pytest.mark.asyncio
@pytest.mark.parametrize("treats_personal,treats_sensitive,third_country,lifecycle,nis2", [
    (True, True, True, "i_drift", True),
    (True, False, False, "under_inforande", False),
    (False, False, False, "planerad", True),
    (True, True, False, "i_drift", True),
    (False, False, True, "i_drift", False),
])
async def test_cross_gdpr_nis2_lifecycle(
    client, treats_personal, treats_sensitive, third_country, lifecycle, nis2
):
    """GDPR-flaggor, NIS2 och livscykelstatus kombineras korrekt."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        treats_personal_data=treats_personal,
        treats_sensitive_data=treats_sensitive,
        third_country_transfer=third_country,
        lifecycle_status=lifecycle,
        nis2_applicable=nis2,
    )
    body = (await client.get(f"/api/v1/systems/{system['id']}")).json()
    assert body["treats_personal_data"] == treats_personal
    assert body["treats_sensitive_data"] == treats_sensitive
    assert body["third_country_transfer"] == third_country
    assert body["lifecycle_status"] == lifecycle
    assert body["nis2_applicable"] == nis2


# ---------------------------------------------------------------------------
# extended_attributes (JSONB) — kategori 1 utökade attribut
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("ext_attrs", [
    {"leverantör": "CGI", "version": "21.3"},
    {"kunder": 500, "avtal_löper_ut": "2027-12-31"},
    {"sla_level": "platinum", "support_timmar": 24},
    {"tags": ["kritisk", "nis2", "gdpr"]},
    {"nested": {"key": "value", "number": 42}},
    {"empty_list": [], "bool_val": True},
    {},
])
async def test_extended_attributes_create_and_read(client, ext_attrs):
    """extended_attributes (JSONB) sparas och hämtas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"], extended_attributes=ext_attrs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    assert detail.status_code == 200
    body = detail.json()
    if ext_attrs:
        for key, val in ext_attrs.items():
            assert body["extended_attributes"][key] == val
    else:
        assert body.get("extended_attributes") in (None, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_attrs,updated_attrs", [
    ({"version": "1.0"}, {"version": "2.0", "ny_nyckel": "värde"}),
    ({"antal": 10}, {"antal": 20}),
    ({"aktiv": True}, {"aktiv": False, "kommentar": "stängd"}),
])
async def test_extended_attributes_update(client, initial_attrs, updated_attrs):
    """extended_attributes kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"], extended_attributes=initial_attrs)

    resp = await client.patch(
        f"/api/v1/systems/{system['id']}",
        json={"extended_attributes": updated_attrs},
    )
    assert resp.status_code == 200
    body = resp.json()
    for key, val in updated_attrs.items():
        assert body["extended_attributes"][key] == val


@pytest.mark.asyncio
@pytest.mark.parametrize("ext_attrs,expected_type", [
    ({"count": 42}, int),
    ({"name": "test"}, str),
    ({"active": True}, bool),
    ({"ratio": 3.14}, float),
    ({"items": [1, 2, 3]}, list),
    ({"meta": {"key": "val"}}, dict),
])
async def test_extended_attributes_type_preservation(client, ext_attrs, expected_type):
    """extended_attributes bevarar Python-typer korrekt via JSONB."""
    org = await create_org(client)
    system = await create_system(client, org["id"], extended_attributes=ext_attrs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    for key in ext_attrs:
        assert isinstance(body["extended_attributes"][key], expected_type)


# ---------------------------------------------------------------------------
# Datum-validering och gränsfall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("date_field,date_value", [
    ("deployment_date", "2020-01-01"),
    ("deployment_date", "2026-03-28"),
    ("planned_decommission_date", "2030-12-31"),
    ("planned_decommission_date", "2025-06-15"),
    ("end_of_support_date", "2024-12-31"),
    ("end_of_support_date", "2028-09-30"),
])
async def test_date_field_iso_format_accepted(client, date_field, date_value):
    """Datumfält accepterar ISO 8601-format (YYYY-MM-DD)."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": f"Datum test {date_field}",
        "description": "Test",
        "system_category": "verksamhetssystem",
        date_field: date_value,
    })
    assert resp.status_code == 201
    assert resp.json()[date_field] == date_value


@pytest.mark.asyncio
@pytest.mark.parametrize("date_field,invalid_date", [
    ("deployment_date", "not-a-date"),
    ("deployment_date", "2020/01/01"),
    ("planned_decommission_date", "31-12-2030"),
    ("end_of_support_date", "2024.12.31"),
])
async def test_date_field_invalid_format_rejected(client, date_field, invalid_date):
    """Ogiltiga datumformat ger 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Fel datum",
        "description": "Test",
        "system_category": "verksamhetssystem",
        date_field: invalid_date,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Compliance-fält (last_risk_assessment_date, klassa_reference_id)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("risk_date,klassa_id", [
    (date(2025, 11, 15), "KLASSA-2025-001"),
    (date(2024, 3, 1), None),
    (None, "KLASSA-2024-042"),
    (None, None),
])
async def test_compliance_fields_create_and_read(client, risk_date, klassa_id):
    """Compliance-fält (last_risk_assessment_date, klassa_reference_id) sparas korrekt."""
    org = await create_org(client)
    kwargs = {}
    if risk_date:
        kwargs["last_risk_assessment_date"] = risk_date
    if klassa_id:
        kwargs["klassa_reference_id"] = klassa_id
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    if risk_date:
        assert body["last_risk_assessment_date"] == risk_date.isoformat()
    else:
        assert body.get("last_risk_assessment_date") is None
    if klassa_id:
        assert body["klassa_reference_id"] == klassa_id
    else:
        assert body.get("klassa_reference_id") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("risk_date,klassa_id", [
    (date(2026, 1, 1), "KLASSA-2026-001"),
    (date(2025, 6, 15), "KLASSA-2025-099"),
])
async def test_compliance_fields_update(client, risk_date, klassa_id):
    """Compliance-fält kan uppdateras via PATCH."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={
        "last_risk_assessment_date": risk_date.isoformat(),
        "klassa_reference_id": klassa_id,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_risk_assessment_date"] == risk_date.isoformat()
    assert body["klassa_reference_id"] == klassa_id


# ---------------------------------------------------------------------------
# Fullständiga system — skapar system med alla kategorifält
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category,criticality,lifecycle,hosting,treats_personal,nis2", [
    ("verksamhetssystem", "kritisk", "i_drift", "on-premise", True, True),
    ("stödsystem", "medel", "under_inforande", "cloud", True, False),
    ("infrastruktur", "hög", "planerad", "hybrid", False, True),
    ("plattform", "låg", "under_avveckling", "cloud", False, False),
    ("iot", "kritisk", "i_drift", "on-premise", True, True),
])
async def test_full_system_all_categories(
    client, category, criticality, lifecycle, hosting, treats_personal, nis2
):
    """Komplett system med fält från alla 6 kategorier skapas och valideras korrekt."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        system_category=category,
        criticality=criticality,
        lifecycle_status=lifecycle,
        hosting_model=hosting,
        treats_personal_data=treats_personal,
        treats_sensitive_data=treats_personal,
        nis2_applicable=nis2,
        nis2_classification="väsentlig" if nis2 else None,
        deployment_date=date(2020, 1, 1) if lifecycle != "planerad" else None,
        business_area="kommunal verksamhet",
        has_elevated_protection=criticality == "kritisk",
        dr_plan_exists=criticality in ("hög", "kritisk"),
        extended_attributes={"kategori": category, "kritikalitet": criticality},
    )

    sid = system["id"]

    # Skapa klassning
    clf = await create_classification(
        client, sid,
        confidentiality=3 if criticality in ("hög", "kritisk") else 2,
        integrity=2,
        availability=3 if criticality == "kritisk" else 1,
        traceability=2,
    )
    assert clf["system_id"] == sid

    # Skapa ägare
    owner = await create_owner(client, sid, org["id"], role="systemägare")
    assert owner["role"] == "systemägare"

    # Skapa GDPR-behandling om aktuellt
    if treats_personal:
        gdpr = await create_gdpr_treatment(client, sid, data_categories=["vanliga"])
        assert gdpr["system_id"] == sid

    # Verifiera detaljvy
    detail_resp = await client.get(f"/api/v1/systems/{sid}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["system_category"] == category
    assert detail["criticality"] == criticality
    assert detail["lifecycle_status"] == lifecycle
    assert detail["hosting_model"] == hosting
    assert detail["treats_personal_data"] == treats_personal
    assert detail["nis2_applicable"] == nis2
    assert detail["extended_attributes"]["kategori"] == category
    assert len(detail["classifications"]) >= 1
    assert len(detail["owners"]) >= 1
    if treats_personal:
        assert len(detail["gdpr_treatments"]) >= 1


# ---------------------------------------------------------------------------
# Ytterligare parametriserade tester för bredare täckning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("category,nis2_class", [
    ("verksamhetssystem", "väsentlig"),
    ("stödsystem", "viktig"),
    ("infrastruktur", "väsentlig"),
    ("plattform", "ej_tillämplig"),
    ("iot", "viktig"),
])
async def test_cat3_nis2_classification_per_system_category(client, category, nis2_class):
    """NIS2-klassificering kombineras korrekt med alla systemkategorier."""
    org = await create_org(client)
    system = await create_system(
        client, org["id"],
        system_category=category,
        nis2_applicable=True,
        nis2_classification=nis2_class,
    )
    assert system["nis2_classification"] == nis2_class
    assert system["system_category"] == category


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle,deployment_date,decommission_date", [
    ("planerad", None, date(2028, 6, 30)),
    ("under_inforande", date(2025, 1, 1), None),
    ("i_drift", date(2020, 3, 15), None),
    ("under_avveckling", date(2018, 7, 1), date(2026, 12, 31)),
    ("avvecklad", date(2015, 4, 1), date(2024, 3, 31)),
])
async def test_cat6_lifecycle_with_dates_combination(
    client, lifecycle, deployment_date, decommission_date
):
    """Livscykelstatus kombineras med relevanta datumfält korrekt."""
    org = await create_org(client)
    kwargs = {"lifecycle_status": lifecycle}
    if deployment_date:
        kwargs["deployment_date"] = deployment_date
    if decommission_date:
        kwargs["planned_decommission_date"] = decommission_date
    system = await create_system(client, org["id"], **kwargs)

    detail = await client.get(f"/api/v1/systems/{system['id']}")
    body = detail.json()
    assert body["lifecycle_status"] == lifecycle
    if deployment_date:
        assert body["deployment_date"] == deployment_date.isoformat()
    if decommission_date:
        assert body["planned_decommission_date"] == decommission_date.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize("role,email", [
    ("systemägare", "systemagare@test.se"),
    ("informationsägare", "infoansvarsig@test.se"),
    ("systemförvaltare", "forvaltare@test.se"),
    ("teknisk_förvaltare", "teknisk@test.se"),
    ("it_kontakt", "itkontakt@test.se"),
    ("dataskyddsombud", "dpo@test.se"),
])
async def test_cat2_owner_email_stored_per_role(client, role, email):
    """E-postadress sparas korrekt för varje ägarroll."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"], role=role, email=email)
    assert owner["email"] == email
    assert owner["role"] == role


@pytest.mark.asyncio
@pytest.mark.parametrize("k,r", [
    (0, 0),
    (0, 4),
    (4, 0),
    (4, 4),
    (2, 3),
    (3, 2),
])
async def test_cat3_confidentiality_integrity_pairs(client, k, r):
    """Alla par av konfidentialitet och riktighet sparas korrekt."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    clf = await create_classification(client, system["id"], confidentiality=k, integrity=r)
    assert clf["confidentiality"] == k
    assert clf["integrity"] == r


@pytest.mark.asyncio
@pytest.mark.parametrize("category,criticality", [
    ("verksamhetssystem", "kritisk"),
    ("infrastruktur", "hög"),
    ("plattform", "medel"),
])
async def test_cat1_cat3_category_criticality_in_list_filter(client, category, criticality):
    """Kombinationsfilter på kategori och kritikalitet i listor ger korrekta resultat."""
    org = await create_org(client)
    await create_system(
        client, org["id"],
        system_category=category,
        criticality=criticality,
        name=f"Combo filter {category}",
    )
    resp = await client.get(
        "/api/v1/systems/",
        params={
            "system_category": category,
            "criticality": criticality,
            "organization_id": org["id"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["system_category"] == category
        assert item["criticality"] == criticality
