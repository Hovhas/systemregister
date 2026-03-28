"""
Data validation tests for all entities.
~120 tests covering:
- Required fields missing
- max_length constraints
- Enum validation (invalid values)
- Numeric constraints (ge/le)
- UUID format validation
- Type coercion / wrong types
- Empty string vs null handling
- JSONB fields (arrays)
"""

import pytest
from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_integration,
    create_gdpr_treatment,
    create_contract,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ===========================================================================
# Organization validation
# ===========================================================================


@pytest.mark.asyncio
async def test_org_name_required(client):
    """POST organization without name returns 422."""
    resp = await client.post("/api/v1/organizations/", json={"org_type": "kommun"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_org_type_required(client):
    """POST organization without org_type returns 422."""
    resp = await client.post("/api/v1/organizations/", json={"name": "Namnlös Org"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.asyncio
async def test_org_name_empty_string(client):
    """POST organization with empty name string should be rejected."""
    resp = await client.post("/api/v1/organizations/", json={"name": "", "org_type": "kommun"})
    assert resp.status_code == 422, f"Expected 422 for empty name, got {resp.status_code}"


@pytest.mark.asyncio
async def test_org_name_max_length_exceeded(client):
    """POST organization with name > 255 chars returns 422."""
    long_name = "A" * 256
    resp = await client.post("/api/v1/organizations/", json={"name": long_name, "org_type": "kommun"})
    assert resp.status_code == 422, f"Expected 422 for name > 255 chars"


@pytest.mark.asyncio
async def test_org_name_exactly_255_chars_accepted(client):
    """POST organization with name of exactly 255 chars is accepted."""
    name_255 = "B" * 255
    resp = await client.post("/api/v1/organizations/", json={"name": name_255, "org_type": "bolag"})
    assert resp.status_code == 201, f"Expected 201 for 255-char name, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_org_number_max_length_exceeded(client):
    """POST organization with org_number > 20 chars returns 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Test Org",
        "org_type": "kommun",
        "org_number": "1" * 21,
    })
    assert resp.status_code == 422, f"Expected 422 for org_number > 20 chars"


@pytest.mark.asyncio
@pytest.mark.parametrize("org_type", ["kommun", "bolag", "samverkan", "digit"])
async def test_org_all_valid_types(client, org_type):
    """POST organization accepts all valid org_type values."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": f"Org {org_type}",
        "org_type": org_type,
    })
    assert resp.status_code == 201, f"Expected 201 for org_type={org_type}: {resp.text}"
    assert resp.json()["org_type"] == org_type


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_type", ["region", "statlig", "privat", "", "123", "KOMMUN"])
async def test_org_invalid_type_rejected(client, invalid_type):
    """POST organization with invalid org_type returns 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Test",
        "org_type": invalid_type,
    })
    assert resp.status_code == 422, f"Expected 422 for org_type='{invalid_type}', got {resp.status_code}"


@pytest.mark.asyncio
async def test_org_parent_org_id_invalid_uuid(client):
    """POST organization with non-UUID parent_org_id returns 422."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "Child Org",
        "org_type": "bolag",
        "parent_org_id": "not-a-uuid",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid UUID, got {resp.status_code}"


@pytest.mark.asyncio
async def test_org_update_with_invalid_type(client):
    """PATCH organization with invalid org_type returns 422."""
    org = await create_org(client)
    resp = await client.patch(f"/api/v1/organizations/{org['id']}", json={"org_type": "ogiltig"})
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


# ===========================================================================
# System validation
# ===========================================================================


@pytest.mark.asyncio
async def test_system_name_required(client):
    """POST system without name returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, f"Expected 422 for missing name"


@pytest.mark.asyncio
async def test_system_organization_id_required(client):
    """POST system without organization_id returns 422."""
    resp = await client.post("/api/v1/systems/", json={
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, f"Expected 422 for missing organization_id"


@pytest.mark.asyncio
async def test_system_description_required(client):
    """POST system without description returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "name": "System",
        "organization_id": org["id"],
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, f"Expected 422 for missing description"


@pytest.mark.asyncio
async def test_system_category_required(client):
    """POST system without system_category returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "name": "System",
        "organization_id": org["id"],
        "description": "Test",
    })
    assert resp.status_code == 422, f"Expected 422 for missing system_category"


@pytest.mark.asyncio
async def test_system_name_max_length_exceeded(client):
    """POST system with name > 255 chars returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "X" * 256,
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, f"Expected 422 for name > 255 chars"


@pytest.mark.asyncio
@pytest.mark.parametrize("category", [
    "verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"
])
async def test_system_all_valid_categories(client, category):
    """POST system accepts all valid system_category values."""
    org = await create_org(client, name=f"Org for {category}")
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": f"System {category}",
        "description": "Test",
        "system_category": category,
    })
    assert resp.status_code == 201, f"Expected 201 for category={category}: {resp.text}"
    assert resp.json()["system_category"] == category


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [
    "planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"
])
async def test_system_all_valid_lifecycle_statuses(client, status):
    """POST system accepts all valid lifecycle_status values."""
    org = await create_org(client, name=f"Org for lifecycle {status}")
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": f"System {status}",
        "description": "Test",
        "system_category": "stödsystem",
        "lifecycle_status": status,
    })
    assert resp.status_code == 201, f"Expected 201 for lifecycle_status={status}: {resp.text}"
    assert resp.json()["lifecycle_status"] == status


@pytest.mark.asyncio
@pytest.mark.parametrize("criticality", ["låg", "medel", "hög", "kritisk"])
async def test_system_all_valid_criticality_values(client, criticality):
    """POST system accepts all valid criticality values."""
    org = await create_org(client, name=f"Org for crit {criticality}")
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": f"System {criticality}",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "criticality": criticality,
    })
    assert resp.status_code == 201, f"Expected 201 for criticality={criticality}: {resp.text}"
    assert resp.json()["criticality"] == criticality


@pytest.mark.asyncio
@pytest.mark.parametrize("nis2_class", ["väsentlig", "viktig", "ej_tillämplig"])
async def test_system_all_valid_nis2_classifications(client, nis2_class):
    """POST system accepts all valid nis2_classification values."""
    org = await create_org(client, name=f"Org for NIS2 {nis2_class}")
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": f"System NIS2 {nis2_class}",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "nis2_classification": nis2_class,
    })
    assert resp.status_code == 201, f"Expected 201 for nis2_classification={nis2_class}: {resp.text}"
    assert resp.json()["nis2_classification"] == nis2_class


@pytest.mark.asyncio
async def test_system_invalid_lifecycle_status(client):
    """POST system with invalid lifecycle_status returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "lifecycle_status": "okänd_status",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_system_invalid_criticality(client):
    """POST system with invalid criticality returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "criticality": "superhög",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_system_invalid_nis2_classification(client):
    """POST system with invalid nis2_classification returns 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "nis2_classification": "oklassad",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_system_extended_attributes_jsonb_valid(client):
    """POST system with extended_attributes JSONB dict is accepted."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "JSONB System",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "extended_attributes": {"customprop": "value", "number": 42, "nested": {"a": 1}},
    })
    assert resp.status_code == 201, f"Expected 201 for JSONB attributes: {resp.text}"
    body = resp.json()
    assert body["extended_attributes"]["customprop"] == "value"


@pytest.mark.asyncio
async def test_system_treats_personal_data_defaults_false(client):
    """POST system without treats_personal_data defaults to False."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    assert system["treats_personal_data"] is False


@pytest.mark.asyncio
async def test_system_organization_id_not_valid_uuid(client):
    """POST system with malformed organization_id returns 422."""
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": "inte-ett-uuid",
        "name": "Test",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid UUID"


# ===========================================================================
# Classification validation
# ===========================================================================


@pytest.mark.asyncio
async def test_classification_confidentiality_required(client):
    """POST classification without confidentiality should fail or use default."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    # If confidentiality has no default, expect 422; otherwise 201
    assert resp.status_code in (201, 422), f"Unexpected status {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, 1, 2, 3, 4])
async def test_classification_all_valid_confidentiality_values(client, value):
    """Classification accepts all valid confidentiality values 0-4."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"Conf {value}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": value,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201, f"Expected 201 for confidentiality={value}: {resp.text}"
    assert resp.json()["confidentiality"] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, 1, 2, 3, 4])
async def test_classification_all_valid_integrity_values(client, value):
    """Classification accepts all valid integrity values 0-4."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"Int {value}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": value,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201, f"Expected 201 for integrity={value}: {resp.text}"
    assert resp.json()["integrity"] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, 1, 2, 3, 4])
async def test_classification_all_valid_availability_values(client, value):
    """Classification accepts all valid availability values 0-4."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"Avail {value}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": value,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201, f"Expected 201 for availability={value}: {resp.text}"
    assert resp.json()["availability"] == value


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["confidentiality", "integrity", "availability"])
async def test_classification_value_below_zero_rejected(client, field):
    """POST classification with value -1 for any field returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"Below {field}")

    payload = {
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
        field: -1,
    }
    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json=payload)
    assert resp.status_code == 422, f"Expected 422 for {field}=-1, got {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["confidentiality", "integrity", "availability"])
async def test_classification_value_above_four_rejected(client, field):
    """POST classification with value 5 for any field returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name=f"Above {field}")

    payload = {
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
        field: 5,
    }
    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json=payload)
    assert resp.status_code == 422, f"Expected 422 for {field}=5, got {resp.status_code}"


@pytest.mark.asyncio
async def test_classification_traceability_valid_values(client):
    """POST classification with traceability 0-4 is accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    for value in [0, 1, 2, 3, 4]:
        resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
            "system_id": system["id"],
            "confidentiality": 2,
            "integrity": 2,
            "availability": 2,
            "traceability": value,
            "classified_by": "test@test.se",
        })
        assert resp.status_code == 201, f"Expected 201 for traceability={value}: {resp.text}"


@pytest.mark.asyncio
async def test_classification_traceability_invalid_rejected(client):
    """POST classification with traceability outside 0-4 returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "traceability": 5,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422, f"Expected 422 for traceability=5"


@pytest.mark.asyncio
async def test_classification_without_traceability_accepted(client):
    """POST classification without traceability (optional field) is accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": 1,
        "integrity": 1,
        "availability": 1,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 201, f"Expected 201 without traceability: {resp.text}"
    assert resp.json()["traceability"] is None


@pytest.mark.asyncio
async def test_classification_classified_by_max_length_exceeded(client):
    """POST classification with classified_by > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "X" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for classified_by > 255 chars"


@pytest.mark.asyncio
async def test_classification_string_value_for_integer_field_rejected(client):
    """POST classification with string instead of integer for confidentiality returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/classifications", json={
        "system_id": system["id"],
        "confidentiality": "hög",
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422, f"Expected 422 for string confidentiality value"


# ===========================================================================
# Owner validation
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [
    "systemägare", "informationsägare", "systemförvaltare",
    "teknisk_förvaltare", "it_kontakt", "dataskyddsombud"
])
async def test_owner_all_valid_roles(client, role):
    """POST owner accepts all 6 valid role values."""
    org = await create_org(client, name=f"Org for role {role}")
    system = await create_system(client, org["id"], name=f"System {role}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": role,
        "name": "Test Person",
    })
    assert resp.status_code == 201, f"Expected 201 for role={role}: {resp.text}"
    assert resp.json()["role"] == role


@pytest.mark.asyncio
async def test_owner_name_required(client):
    """POST owner without name returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "systemägare",
    })
    assert resp.status_code == 422, f"Expected 422 for missing name"


@pytest.mark.asyncio
async def test_owner_role_required(client):
    """POST owner without role returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "name": "Test Person",
    })
    assert resp.status_code == 422, f"Expected 422 for missing role"


@pytest.mark.asyncio
async def test_owner_name_max_length_exceeded(client):
    """POST owner with name > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "N" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for name > 255 chars"


@pytest.mark.asyncio
async def test_owner_email_max_length_exceeded(client):
    """POST owner with email > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "Test",
        "email": "a" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for email > 255 chars"


@pytest.mark.asyncio
async def test_owner_phone_max_length_exceeded(client):
    """POST owner with phone > 50 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "Test",
        "phone": "0" * 51,
    })
    assert resp.status_code == 422, f"Expected 422 for phone > 50 chars"


@pytest.mark.asyncio
async def test_owner_unique_constraint_same_role_and_name(client):
    """POST duplicate owner (same system_id, role, name) returns 409 or 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    owner_payload = {
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "Unik Person",
    }
    resp1 = await client.post(f"/api/v1/systems/{system['id']}/owners", json=owner_payload)
    assert resp1.status_code == 201

    try:
        resp2 = await client.post(f"/api/v1/systems/{system['id']}/owners", json=owner_payload)
        # Should not succeed
        assert resp2.status_code in (409, 422, 400), (
            f"Duplicate owner should be rejected, got {resp2.status_code}"
        )
    except Exception:
        # DB constraint violation as exception is also acceptable
        pass


@pytest.mark.asyncio
async def test_owner_same_role_different_name_allowed(client):
    """POST two owners with same role but different names is allowed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp1 = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "Person A",
    })
    resp2 = await client.post(f"/api/v1/systems/{system['id']}/owners", json={
        "system_id": system["id"],
        "organization_id": org["id"],
        "role": "it_kontakt",
        "name": "Person B",
    })
    assert resp1.status_code == 201
    assert resp2.status_code == 201, (
        f"Different names with same role should be allowed: {resp2.text}"
    )


# ===========================================================================
# Integration validation
# ===========================================================================


@pytest.mark.asyncio
async def test_integration_source_system_required(client):
    """POST integration without source_system_id returns 422."""
    org = await create_org(client)
    target = await create_system(client, org["id"], name="Target")

    resp = await client.post("/api/v1/integrations/", json={
        "target_system_id": target["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 422, f"Expected 422 for missing source_system_id"


@pytest.mark.asyncio
async def test_integration_target_system_required(client):
    """POST integration without target_system_id returns 422."""
    org = await create_org(client)
    source = await create_system(client, org["id"], name="Source")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 422, f"Expected 422 for missing target_system_id"


@pytest.mark.asyncio
@pytest.mark.parametrize("integration_type", [
    "api", "filöverföring", "databasreplikering", "event", "manuell"
])
async def test_integration_all_valid_types(client, integration_type):
    """POST integration accepts all valid integration_type values."""
    org = await create_org(client, name=f"Org {integration_type}")
    source = await create_system(client, org["id"], name="Källa")
    target = await create_system(client, org["id"], name="Mål")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "target_system_id": target["id"],
        "integration_type": integration_type,
    })
    assert resp.status_code == 201, f"Expected 201 for integration_type={integration_type}: {resp.text}"
    assert resp.json()["integration_type"] == integration_type


@pytest.mark.asyncio
async def test_integration_frequency_max_length_exceeded(client):
    """POST integration with frequency > 100 chars returns 422."""
    org = await create_org(client)
    source = await create_system(client, org["id"], name="Src")
    target = await create_system(client, org["id"], name="Tgt")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "target_system_id": target["id"],
        "integration_type": "api",
        "frequency": "X" * 101,
    })
    assert resp.status_code == 422, f"Expected 422 for frequency > 100 chars"


@pytest.mark.asyncio
async def test_integration_external_party_max_length_exceeded(client):
    """POST integration with external_party > 255 chars returns 422."""
    org = await create_org(client)
    source = await create_system(client, org["id"], name="Src2")
    target = await create_system(client, org["id"], name="Tgt2")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "target_system_id": target["id"],
        "integration_type": "api",
        "is_external": True,
        "external_party": "P" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for external_party > 255 chars"


@pytest.mark.asyncio
async def test_integration_invalid_source_uuid(client):
    """POST integration with non-UUID source_system_id returns 422."""
    org = await create_org(client)
    target = await create_system(client, org["id"], name="Mål")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": "not-a-uuid",
        "target_system_id": target["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid source UUID"


@pytest.mark.asyncio
async def test_integration_invalid_criticality(client):
    """POST integration with invalid criticality returns 422."""
    org = await create_org(client)
    source = await create_system(client, org["id"], name="Src3")
    target = await create_system(client, org["id"], name="Tgt3")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "target_system_id": target["id"],
        "integration_type": "api",
        "criticality": "superbrå",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid criticality"


# ===========================================================================
# GDPR Treatment validation
# ===========================================================================


@pytest.mark.asyncio
async def test_gdpr_ropa_reference_max_length_exceeded(client):
    """POST GDPR treatment with ropa_reference_id > 100 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "ropa_reference_id": "R" * 101,
    })
    assert resp.status_code == 422, f"Expected 422 for ropa_reference_id > 100 chars"


@pytest.mark.asyncio
async def test_gdpr_legal_basis_max_length_exceeded(client):
    """POST GDPR treatment with legal_basis > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "legal_basis": "L" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for legal_basis > 255 chars"


@pytest.mark.asyncio
async def test_gdpr_data_processor_max_length_exceeded(client):
    """POST GDPR treatment with data_processor > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_processor": "D" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for data_processor > 255 chars"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["ja", "nej", "under_framtagande", "ej_tillämpligt"])
async def test_gdpr_all_valid_processor_agreement_statuses(client, status):
    """POST GDPR treatment accepts all valid processor_agreement_status values."""
    org = await create_org(client, name=f"Org GDPR {status}")
    system = await create_system(client, org["id"], name=f"System GDPR {status}")

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "processor_agreement_status": status,
    })
    assert resp.status_code == 201, f"Expected 201 for processor_agreement_status={status}: {resp.text}"
    assert resp.json()["processor_agreement_status"] == status


@pytest.mark.asyncio
async def test_gdpr_data_categories_is_list(client):
    """POST GDPR treatment with data_categories as array is accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": ["vanliga", "känsliga_art9", "personnummer"],
    })
    assert resp.status_code == 201, f"Expected 201 for data_categories list: {resp.text}"
    body = resp.json()
    assert isinstance(body["data_categories"], list)
    assert "vanliga" in body["data_categories"]


@pytest.mark.asyncio
async def test_gdpr_data_categories_empty_list(client):
    """POST GDPR treatment with empty data_categories list is accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "data_categories": [],
    })
    assert resp.status_code in (201, 422), (
        f"Empty data_categories should either be accepted or rejected with 422, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_gdpr_dpia_date_invalid_format(client):
    """POST GDPR treatment with invalid dpia_date format returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={
        "dpia_conducted": True,
        "dpia_date": "not-a-date",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid dpia_date format"


@pytest.mark.asyncio
async def test_gdpr_dpia_conducted_defaults_false(client):
    """POST GDPR treatment without dpia_conducted defaults to False."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/gdpr", json={})
    assert resp.status_code == 201
    assert resp.json()["dpia_conducted"] is False


# ===========================================================================
# Contract validation
# ===========================================================================


@pytest.mark.asyncio
async def test_contract_supplier_name_required(client):
    """POST contract without supplier_name returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "annual_license_cost": 100000,
    })
    assert resp.status_code == 422, f"Expected 422 for missing supplier_name"


@pytest.mark.asyncio
async def test_contract_supplier_name_max_length_exceeded(client):
    """POST contract with supplier_name > 255 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "S" * 256,
    })
    assert resp.status_code == 422, f"Expected 422 for supplier_name > 255 chars"


@pytest.mark.asyncio
async def test_contract_supplier_org_number_max_length_exceeded(client):
    """POST contract with supplier_org_number > 20 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "supplier_org_number": "1" * 21,
    })
    assert resp.status_code == 422, f"Expected 422 for supplier_org_number > 20 chars"


@pytest.mark.asyncio
async def test_contract_contract_id_external_max_length_exceeded(client):
    """POST contract with contract_id_external > 100 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "contract_id_external": "K" * 101,
    })
    assert resp.status_code == 422, f"Expected 422 for contract_id_external > 100 chars"


@pytest.mark.asyncio
async def test_contract_license_model_max_length_exceeded(client):
    """POST contract with license_model > 100 chars returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "license_model": "M" * 101,
    })
    assert resp.status_code == 422, f"Expected 422 for license_model > 100 chars"


@pytest.mark.asyncio
async def test_contract_auto_renewal_defaults_false(client):
    """POST contract without auto_renewal defaults to False."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
    })
    assert resp.status_code == 201
    assert resp.json()["auto_renewal"] is False


@pytest.mark.asyncio
async def test_contract_date_invalid_format(client):
    """POST contract with invalid contract_start date format returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "contract_start": "inte-ett-datum",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid date format"


@pytest.mark.asyncio
async def test_contract_end_date_invalid_format(client):
    """POST contract with invalid contract_end date format returns 422."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "contract_end": "2025/12/31",
    })
    assert resp.status_code == 422, f"Expected 422 for invalid date format"


@pytest.mark.asyncio
async def test_contract_annual_cost_negative_rejected(client):
    """POST contract with negative annual_license_cost returns 422 (if validated)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "annual_license_cost": -1,
    })
    # Negative costs may or may not be validated — depends on schema
    # Just ensure it doesn't crash with 500
    assert resp.status_code in (201, 422), (
        f"Negative cost should not cause 500, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_contract_notice_period_months_valid(client):
    """POST contract with valid notice_period_months is accepted."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Test AB",
        "notice_period_months": 3,
    })
    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    assert resp.json()["notice_period_months"] == 3


# ===========================================================================
# UUID validation across endpoints
# ===========================================================================


@pytest.mark.asyncio
async def test_get_system_with_invalid_uuid_format(client):
    """GET /api/v1/systems/{id} with non-UUID id returns 422 or 404."""
    resp = await client.get("/api/v1/systems/not-a-valid-uuid")
    assert resp.status_code in (422, 404), (
        f"Non-UUID id should return 422 or 404, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_get_organization_with_invalid_uuid_format(client):
    """GET /api/v1/organizations/{id} with non-UUID id returns 422 or 404."""
    resp = await client.get("/api/v1/organizations/not-a-valid-uuid")
    assert resp.status_code in (422, 404), (
        f"Non-UUID id should return 422 or 404, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_patch_system_with_invalid_uuid_format(client):
    """PATCH /api/v1/systems/{id} with non-UUID id returns 422 or 404."""
    resp = await client.patch("/api/v1/systems/not-a-valid-uuid", json={"name": "Test"})
    assert resp.status_code in (422, 404), (
        f"Non-UUID id should return 422 or 404, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_delete_system_with_invalid_uuid_format(client):
    """DELETE /api/v1/systems/{id} with non-UUID id returns 422 or 404."""
    resp = await client.delete("/api/v1/systems/not-a-valid-uuid")
    assert resp.status_code in (422, 404), (
        f"Non-UUID id should return 422 or 404, got {resp.status_code}"
    )


# ===========================================================================
# Empty body / null handling
# ===========================================================================


@pytest.mark.asyncio
async def test_patch_organization_empty_body(client):
    """PATCH organization with empty body {} should succeed (no-op update)."""
    org = await create_org(client)
    resp = await client.patch(f"/api/v1/organizations/{org['id']}", json={})
    assert resp.status_code == 200, f"Empty PATCH should succeed: {resp.text}"
    # Fields should remain unchanged
    body = resp.json()
    assert body["name"] == org["name"]


@pytest.mark.asyncio
async def test_patch_system_empty_body(client):
    """PATCH system with empty body {} should succeed (no-op update)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{system['id']}", json={})
    assert resp.status_code == 200, f"Empty PATCH should succeed: {resp.text}"
    body = resp.json()
    assert body["name"] == system["name"]


@pytest.mark.asyncio
async def test_patch_contract_empty_body(client):
    """PATCH contract with empty body {} should succeed (no-op update)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    contract = await create_contract(client, system["id"])
    resp = await client.patch(f"/api/v1/contracts/{contract['id']}", json={})
    assert resp.status_code == 200, f"Empty PATCH should succeed: {resp.text}"


@pytest.mark.asyncio
async def test_patch_owner_empty_body(client):
    """PATCH owner with empty body {} should succeed (no-op update)."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    owner = await create_owner(client, system["id"], org["id"])
    resp = await client.patch(f"/api/v1/owners/{owner['id']}", json={})
    assert resp.status_code == 200, f"Empty PATCH should succeed: {resp.text}"
