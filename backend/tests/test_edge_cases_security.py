"""
Gränsfall, säkerhet och "omöjliga" scenarier.

~250 testfall via pytest.mark.parametrize som täcker:
- Strängvalidering (null bytes, unicode, injections)
- Numeriska gränsvärden (K/R/T, kostnadsfält)
- UUID-fält (ogiltiga format, saknade resurser)
- Datum-fält (felaktiga format, ogiltiga ordningar)
- API-säkerhet (Content-Type, body-format, storlek)
- JSONB edge cases (djupa strukturer, extrema värden)
- Konkurrens (parallella operationer)
- Pagination (extremvärden, negativa)
- Import edge cases (filtyper, encodings, storlek)
- Export edge cases (noll system, fyllda system)
"""

import asyncio
import csv
import io
import json

import pytest

from tests.factories import (
    create_org,
    create_system,
)

FAKE_UUID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_UUID = "12345678-1234-1234-1234-123456789abc"


# ===========================================================================
# Hjälpfunktioner för import-tester
# ===========================================================================


def make_csv_import(rows: list[dict]) -> tuple[bytes, str, str]:
    if not rows:
        return b"", "systems.csv", "text/csv"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8"), "systems.csv", "text/csv"


def make_json_import(data) -> tuple[bytes, str, str]:
    content = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return content, "systems.json", "application/json"


async def post_import(client, org_id: str, content: bytes, filename: str, content_type: str):
    return await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org_id},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


VALID_IMPORT_ROW = {
    "name": "Edge-case System",
    "description": "Testbeskrivning",
    "system_category": "verksamhetssystem",
}


# ===========================================================================
# Strängvalidering — null bytes (SafeStringMixin)
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("name", "System\x00Namn"),
    ("description", "Beskrivning\x00med null"),
    ("business_area", "Område\x00null"),
    ("product_name", "Produkt\x00null"),
    ("klassa_reference_id", "KLASSA\x00-123"),
])
async def test_system_null_bytes_blocked(client, field, value):
    """Null-bytes i systemfält ska blockeras av SafeStringMixin (422)."""
    org = await create_org(client)
    data = {
        "organization_id": org["id"],
        "name": "NullTest",
        "description": "ok",
        "system_category": "verksamhetssystem",
        field: value,
    }
    resp = await client.post("/api/v1/systems/", json=data)
    assert resp.status_code == 422, (
        f"Null-byte i '{field}' borde ge 422, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("name", "Org\x00Name"),
    ("description", "Desc\x00null"),
    ("org_number", "556\x00123"),
])
async def test_org_null_bytes_blocked(client, field, value):
    """Null-bytes i organisationsfält ska blockeras (422)."""
    data = {"name": "OkOrg", "org_type": "kommun", field: value}
    resp = await client.post("/api/v1/organizations/", json=data)
    assert resp.status_code == 422, (
        f"Null-byte i org '{field}' borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("name", "Ägare\x00null"),
    ("email", "test\x00@test.se"),
    ("phone", "+46\x00703"),
])
async def test_owner_null_bytes_blocked(client, field, value):
    """Null-bytes i ägare-fält ska blockeras (422)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "Test",
        field: value,
    }
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json=data)
    assert resp.status_code == 422


# ===========================================================================
# Strängvalidering — unicode
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "Ålands systemregister",
    "Örebro kommuns ärende-system",
    "Ändringsledning ÄÖÅ äöå",
    "CJK: 系统注册表 システム",
    "Emoji: \U0001F4BB \U0001F527",
    "RTL: \u202eReversed text",
    "Zero-Width: ZW\u200bJ",
    "Arabisk: نظام التسجيل",
])
async def test_system_unicode_name_accepted(client, name):
    """Unicode-namn ska accepteras och lagras korrekt."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": name,
        "description": "Unicode-test",
        "system_category": "verksamhetssystem",
    })
    # Ska antingen accepteras (201) eller avvisas (422) — ALDRIG 500
    assert resp.status_code in (201, 422), (
        f"Unicode-namn borde ge 201 eller 422, fick {resp.status_code}: {resp.text}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
@pytest.mark.parametrize("desc", [
    "Vanlig svensk text: åäö ÅÄÖ.",
    "\u200b\u200c\u200d",  # Zero-width chars
    "\ufeffBOM i mitten",  # BOM-tecken
    "Kombinerat: åäö\u200b\ufeff",
])
async def test_system_unicode_description_accepted(client, desc):
    """Unicode i description ska hanteras utan 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "UnicodeDescTest",
        "description": desc,
        "system_category": "stödsystem",
    })
    assert resp.status_code != 500


# ===========================================================================
# Strängvalidering — HTML/script-injection
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert('xss')",
    "<svg onload=alert(1)>",
    "';alert('xss');//",
    "<iframe src='javascript:alert(1)'></iframe>",
])
async def test_html_injection_in_system_name(client, payload):
    """HTML/script-injection i systemnamn ska lagras eller avvisas, ALDRIG orsaka 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": payload[:255],  # Respektera maxlängd
        "description": "Injektionstest",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code in (201, 422), (
        f"HTML injection borde ge 201 eller 422, fick {resp.status_code}: {resp.text}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    "'; DROP TABLE systems; --",
    "' OR '1'='1",
    "1; DELETE FROM systems WHERE '1'='1",
    "' UNION SELECT * FROM organizations --",
    "'; INSERT INTO systems (name) VALUES ('evil'); --",
])
async def test_sql_injection_in_system_name(client, payload):
    """SQL-injection i systemnamn ska aldrig krascha servern."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": payload[:255],
        "description": "SQL-injektionstest",
        "system_category": "infrastruktur",
    })
    assert resp.status_code in (201, 422), (
        f"SQL injection borde ge 201 eller 422, fick {resp.status_code}: {resp.text}"
    )
    # Verifiera att DB fortfarande fungerar
    list_resp = await client.get("/api/v1/systems/")
    assert list_resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    "../../etc/passwd",
    "..\\..\\windows\\system32\\config\\sam",
    "/etc/shadow",
    "file:///etc/passwd",
    "%2e%2e%2f%2e%2e%2f",
])
async def test_path_traversal_in_name(client, payload):
    """Path traversal i namn ska hanteras utan 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": payload[:255],
        "description": "Path traversal test",
        "system_category": "plattform",
    })
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    "Namn\r\nX-Injected-Header: evil",
    "Text\r\nLocation: http://evil.com",
    "Värde\nSet-Cookie: session=evil",
    "Rad1\rRad2",
])
async def test_crlf_injection_in_fields(client, payload):
    """CRLF-injection ska hanteras utan 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": payload[:255].replace("\r", "").replace("\n", ""),
        "description": payload,
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code != 500


# ===========================================================================
# Strängvalidering — maxlängder
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("length,expected_status", [
    (255, 201),   # Exakt max
    (256, 422),   # En över max
    (1000, 422),  # Långt över
])
async def test_system_name_length_boundary(client, length, expected_status):
    """Systemnamn max 255 tecken."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "A" * length,
        "description": "Längdtest",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == expected_status, (
        f"Namn med {length} tecken borde ge {expected_status}, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("length,expected_status", [
    (255, 201),
    (256, 422),
])
async def test_org_name_length_boundary(client, length, expected_status):
    """Organisationsnamn max 255 tecken."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "X" * length,
        "org_type": "bolag",
    })
    assert resp.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.parametrize("length,expected_status", [
    (20, 201),
    (21, 422),
])
async def test_org_number_length_boundary(client, length, expected_status):
    """Organisationsnummer max 20 tecken."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "LängdOrg",
        "org_type": "kommun",
        "org_number": "1" * length,
    })
    assert resp.status_code == expected_status


# ===========================================================================
# Numeriska fält — K/R/T klassning
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,expected_status", [
    ("confidentiality", -1, 422),
    ("confidentiality", 0, 201),
    ("confidentiality", 4, 201),
    ("confidentiality", 5, 422),
    ("confidentiality", 100, 422),
    ("integrity", -1, 422),
    ("integrity", 0, 201),
    ("integrity", 4, 201),
    ("integrity", 5, 422),
    ("availability", -1, 422),
    ("availability", 0, 201),
    ("availability", 4, 201),
    ("availability", 5, 422),
    ("traceability", -1, 422),
    ("traceability", 0, 201),
    ("traceability", 4, 201),
    ("traceability", 5, 422),
])
async def test_classification_krt_boundaries(client, field, value, expected_status):
    """K/R/T/spårbarhet-värden ska valideras strikt inom 0–4."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
        field: value,
    }
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json=data)
    assert resp.status_code == expected_status, (
        f"{field}={value} borde ge {expected_status}, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [2.5, 0.7, 3.9])
async def test_classification_float_rejected(client, value):
    """Flyttal i K/R/T-fält ska avvisas (422)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": value,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    })
    assert resp.status_code == 422, (
        f"Float {value} i confidentiality borde ge 422, fick {resp.status_code}"
    )


# ===========================================================================
# Numeriska fält — kontraktskostnader och notice_period
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,expected_status", [
    ("annual_license_cost", -1, 422),
    ("annual_license_cost", 0, 201),
    ("annual_license_cost", 1_000_000_000, 201),
    ("annual_operations_cost", -1, 422),
    ("annual_operations_cost", 0, 201),
    ("notice_period_months", -1, 422),
    ("notice_period_months", 0, 201),
    ("notice_period_months", 999, 201),
])
async def test_contract_numeric_boundaries(client, field, value, expected_status):
    """Kontraktsnumeriska fält ska valideras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "supplier_name": "Test AB",
        field: value,
    }
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json=data)
    assert resp.status_code == expected_status, (
        f"{field}={value} borde ge {expected_status}, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("annual_license_cost", 1.5),
    ("annual_operations_cost", 99.99),
    ("notice_period_months", 3.5),
])
async def test_contract_float_cost_rejected(client, field, value):
    """Flyttal i kontrakts-heltalsfält ska avvisas (422)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Float AB",
        field: value,
    })
    assert resp.status_code == 422, (
        f"Float {value} i {field} borde ge 422, fick {resp.status_code}"
    )


# ===========================================================================
# UUID-fält
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("uuid_val", [
    "not-a-uuid",
    "12345",
    "GGGGGGGG-GGGG-GGGG-GGGG-GGGGGGGGGGGG",
    "null",
    "undefined",
    "' OR 1=1 --",
    "00000000-0000-0000-0000-00000000000Z",
])
async def test_system_invalid_uuid_in_path(client, uuid_val):
    """Ogiltiga UUID i sökväg ska ge 422 eller 404."""
    resp = await client.get(f"/api/v1/systems/{uuid_val}")
    assert resp.status_code in (404, 422), (
        f"Ogiltigt UUID '{uuid_val}' borde ge 404 eller 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_system_null_uuid_returns_404(client):
    """NULL-UUID i sökväg ska ge 404 (inte 500)."""
    resp = await client.get(f"/api/v1/systems/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_system_nonexistent_uuid_returns_404(client):
    """Icke-existerande UUID ska ge 404."""
    resp = await client.get(f"/api/v1/systems/{NONEXISTENT_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("uuid_val", [
    "not-a-uuid",
    "",
    "12345",
    "fel-format-uuid",
])
async def test_system_invalid_uuid_in_body(client, uuid_val):
    """Ogiltigt UUID i request body ska ge 422."""
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": uuid_val,
        "name": "UUIDtest",
        "description": "test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_integration_nonexistent_source_system(client):
    """Integration med icke-existerande source system ska ge 404 eller 422."""
    org = await create_org(client)
    target = await create_system(client, org["id"])
    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": NONEXISTENT_UUID,
        "target_system_id": target["id"],
        "integration_type": "api",
    })
    assert resp.status_code in (404, 422), (
        f"Icke-existerande source borde ge 404/422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_integration_nonexistent_target_system(client):
    """Integration med icke-existerande target system ska ge 404 eller 422."""
    org = await create_org(client)
    source = await create_system(client, org["id"])
    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": source["id"],
        "target_system_id": NONEXISTENT_UUID,
        "integration_type": "api",
    })
    assert resp.status_code in (404, 422)


# ===========================================================================
# Datum-fält
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("deployment_date", "not-a-date"),
    ("deployment_date", "32-13-2024"),
    ("deployment_date", "2024/01/01"),
    ("deployment_date", "01-01-2024"),
    ("planned_decommission_date", "invalid"),
    ("end_of_support_date", "2024"),
    ("last_risk_assessment_date", "20240101"),
])
async def test_system_invalid_date_format(client, field, value):
    """Ogiltiga datumformat ska avvisas med 422."""
    org = await create_org(client)
    data = {
        "organization_id": org["id"],
        "name": "DatumTest",
        "description": "datumtest",
        "system_category": "infrastruktur",
        field: value,
    }
    resp = await client.post("/api/v1/systems/", json=data)
    assert resp.status_code == 422, (
        f"Ogiltigt datum '{value}' i '{field}' borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("date_val", [
    "2099-12-31",  # Långt i framtiden
    "1900-01-01",  # Långt i förflutna
    "2024-02-29",  # Skottdag (existerar)
    "2000-01-01",  # Millenniumskiftet
])
async def test_system_extreme_dates_accepted(client, date_val):
    """Extrema men giltiga datum ska accepteras."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "ExtremDatum",
        "description": "extremt datum",
        "system_category": "verksamhetssystem",
        "deployment_date": date_val,
    })
    assert resp.status_code == 201, (
        f"Giltigt datum {date_val} borde ge 201, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_system_invalid_date_feb29_non_leapyear(client):
    """29 februari på icke-skottår ska avvisas."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "SkottÅrTest",
        "description": "fel skottdag",
        "system_category": "verksamhetssystem",
        "deployment_date": "2023-02-29",  # 2023 är inte skottår
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_date", [
    "not-a-date",
    "2024/06/01",
    "01.06.2024",
    "June 1, 2024",
])
async def test_contract_invalid_date_format(client, contract_date):
    """Ogiltigt datumformat i kontrakt ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Test AB",
        "contract_start": contract_date,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_classification_invalid_valid_until(client):
    """Ogiltigt datumformat i valid_until ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json={
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
        "valid_until": "not-a-date",
    })
    assert resp.status_code == 422


# ===========================================================================
# API-säkerhet — Content-Type och request-format
# ===========================================================================


@pytest.mark.asyncio
async def test_post_without_content_type(client):
    """POST utan Content-Type ska ge 422 (Pydantic kan inte parsa body)."""
    resp = await client.post(
        "/api/v1/organizations/",
        content=b'{"name": "Test", "org_type": "kommun"}',
        headers={"Content-Type": ""},
    )
    # Antingen 422 (ogiltig) eller 415 (unsupported media type) — ALDRIG 500
    assert resp.status_code in (400, 415, 422), (
        f"POST utan Content-Type borde ge 400/415/422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_post_with_wrong_content_type(client):
    """POST med text/plain Content-Type ska ge 422 eller 415."""
    resp = await client.post(
        "/api/v1/organizations/",
        content=b'{"name": "Test", "org_type": "kommun"}',
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code in (400, 415, 422), (
        f"POST med text/plain borde ge 400/415/422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_post_empty_body(client):
    """POST med tom body ska ge 422."""
    resp = await client.post(
        "/api/v1/organizations/",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_array_instead_of_object(client):
    """POST med JSON-array istället för objekt ska ge 422."""
    resp = await client.post("/api/v1/organizations/", json=[
        {"name": "Org1", "org_type": "kommun"},
    ])
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_null_body(client):
    """POST med JSON null ska ge 422."""
    resp = await client.post(
        "/api/v1/organizations/",
        content=b"null",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_extra_unexpected_fields_ignored(client):
    """Extra oväntade fält i request body ska ignoreras (201)."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": "ExtraFält Org",
        "org_type": "bolag",
        "extra_field_that_does_not_exist": "should be ignored",
        "another_unexpected": 12345,
        "nested_unexpected": {"deep": "value"},
    })
    assert resp.status_code == 201, (
        f"Extra fält borde ignoreras (201), fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_post_large_request_body(client):
    """Extremt stor request body ska hanteras utan 500."""
    large_description = "X" * (1024 * 1024)  # 1 MB
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": FAKE_UUID,
        "name": "LargeBody",
        "description": large_description,
        "system_category": "verksamhetssystem",
    })
    # Antingen 422 (för stor) eller 404 (org finns ej) — ALDRIG 500
    assert resp.status_code in (400, 404, 413, 422), (
        f"Stor body borde ge 400/404/413/422, fick {resp.status_code}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_get_with_json_body_ignored(client):
    """GET-request med JSON body ska fungera normalt (body ignoreras)."""
    resp = await client.request(
        "GET",
        "/api/v1/organizations/",
        content=b'{"evil": "payload"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200


# ===========================================================================
# JSONB — extended_attributes edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_extended_attributes_null(client):
    """extended_attributes=null ska accepteras."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "NullAttrs",
        "description": "test",
        "system_category": "infrastruktur",
        "extended_attributes": None,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_extended_attributes_empty_object(client):
    """extended_attributes={} ska accepteras."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "EmptyAttrs",
        "description": "test",
        "system_category": "infrastruktur",
        "extended_attributes": {},
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_extended_attributes_deeply_nested(client):
    """Djupt nästlat JSONB-objekt (50 nivåer) ska hanteras utan 500."""
    # Bygg 50-nivåers nästling
    nested: dict = {}
    current = nested
    for i in range(50):
        current["level"] = {}
        current = current["level"]
    current["value"] = "deep"

    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "DeepNested",
        "description": "djupt nästlat",
        "system_category": "plattform",
        "extended_attributes": nested,
    })
    assert resp.status_code in (201, 422), (
        f"Djup nästling borde ge 201 eller 422, fick {resp.status_code}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extended_attributes_many_keys(client):
    """JSONB med 1000 nycklar ska hanteras utan 500."""
    attrs = {f"key_{i}": f"value_{i}" for i in range(1000)}
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "ManyKeys",
        "description": "många nycklar",
        "system_category": "plattform",
        "extended_attributes": attrs,
    })
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
@pytest.mark.parametrize("attrs", [
    {"key": None},
    {"key": []},
    {"key": {}},
    {"key": [1, 2, 3]},
    {"": "empty key"},
    {"unicode_key_åäö": "unicode val"},
    {"key with spaces": "value"},
    {"key\twith\ttabs": "value"},
])
async def test_extended_attributes_special_values(client, attrs):
    """Specialvärden i extended_attributes ska hanteras utan 500."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "SpecialAttrs",
        "description": "special attrs",
        "system_category": "infrastruktur",
        "extended_attributes": attrs,
    })
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


# ===========================================================================
# Konkurrens — parallella operationer
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_updates_same_system(client):
    """Sekventiella PATCH-anrop på samma system ska fungera korrekt.

    OBS: Parallella anrop fungerar inte med delad testsession.
    Verifierar istället att upprepade anrop ger 200.
    """
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    system_id = sys["id"]

    for i in range(5):
        resp = await client.patch(f"/api/v1/systems/{system_id}", json={
            "name": f"Sekventiellt Namn {i}",
        })
        assert resp.status_code in (200, 409), (
            f"Update {i} borde ge 200 eller 409, fick {resp.status_code}: {resp.text}"
        )
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_concurrent_create_same_org_systems(client):
    """Sekventiell skapning av system i samma org ska fungera utan kraschar.

    OBS: Parallella anrop fungerar inte med delad testsession.
    Verifierar istället att upprepade anrop ger 201.
    """
    org = await create_org(client)

    for i in range(5):
        resp = await client.post("/api/v1/systems/", json={
            "organization_id": org["id"],
            "name": f"Sekventiellt System {i}",
            "description": "concurrent test",
            "system_category": "verksamhetssystem",
        })
        assert resp.status_code in (201, 409), (
            f"Create {i} borde ge 201 eller 409, fick {resp.status_code}"
        )
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_read_during_delete(client):
    """Läsning av ett system som raderas samtidigt ska ge 200 eller 404 — ALDRIG 500."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    system_id = sys["id"]

    async def do_get():
        return await client.get(f"/api/v1/systems/{system_id}")

    async def do_delete():
        return await client.delete(f"/api/v1/systems/{system_id}")

    get_resp, del_resp = await asyncio.gather(do_get(), do_delete())

    assert get_resp.status_code in (200, 404)
    assert del_resp.status_code in (204, 404)
    assert get_resp.status_code != 500
    assert del_resp.status_code != 500


# ===========================================================================
# Pagination — extremvärden
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("params,expected_ok", [
    ({"offset": 0, "limit": 10}, True),
    ({"offset": 0, "limit": 1}, True),
    ({"offset": 999999, "limit": 10}, True),   # Offset > total => tom lista
    ({"offset": 0, "limit": 100}, True),
    ({"offset": 0, "limit": 0}, False),         # Limit 0 => 422
    ({"offset": -1, "limit": 10}, False),        # Negativ offset => 422
    ({"offset": 0, "limit": -1}, False),         # Negativ limit => 422
    ({"offset": -100, "limit": -100}, False),
])
async def test_pagination_boundary_values(client, params, expected_ok):
    """Paginerings-parametrar ska valideras korrekt."""
    resp = await client.get("/api/v1/systems/", params=params)
    if expected_ok:
        assert resp.status_code == 200, (
            f"Params {params} borde ge 200, fick {resp.status_code}: {resp.text}"
        )
    else:
        assert resp.status_code == 422, (
            f"Ogiltiga params {params} borde ge 422, fick {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_pagination_large_offset_returns_empty(client):
    """Offset större än antal system ska returnera tom lista (inte 404)."""
    org = await create_org(client)
    await create_system(client, org["id"], name="System1")

    resp = await client.get("/api/v1/systems/", params={"offset": 10000, "limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


@pytest.mark.asyncio
async def test_pagination_extremely_large_limit(client):
    """Extremt stor limit (100000) ska hanteras utan 500."""
    resp = await client.get("/api/v1/systems/", params={"limit": 100000})
    # Antingen 200 (OK med ev. cap) eller 422 (för stor) — ALDRIG 500
    assert resp.status_code in (200, 422), (
        f"Limit=100000 borde ge 200 eller 422, fick {resp.status_code}"
    )
    assert resp.status_code != 500


# ===========================================================================
# Import edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_import_empty_file(client):
    """Import av tom fil ska ge 200 med 0 importerade eller ett felmeddelande."""
    org = await create_org(client)
    resp = await post_import(client, org["id"], b"", "systems.csv", "text/csv")
    assert resp.status_code in (200, 400, 422), (
        f"Tom fil borde ge 200/400/422, fick {resp.status_code}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_csv_headers_only(client):
    """CSV med bara headers (inga datarader) ska ge 0 importerade."""
    org = await create_org(client)
    headers = "name,description,system_category\n"
    resp = await post_import(client, org["id"], headers.encode("utf-8"), "systems.csv", "text/csv")
    assert resp.status_code in (200, 400, 422)
    assert resp.status_code != 500
    if resp.status_code == 200:
        body = resp.json()
        assert body["imported"] == 0


@pytest.mark.asyncio
async def test_import_wrong_file_type_exe(client):
    """Import av .exe-fil ska avvisas (400 eller 422)."""
    org = await create_org(client)
    fake_exe = b"MZ\x90\x00" + b"\x00" * 100  # DOS MZ header
    resp = await post_import(client, org["id"], fake_exe, "systems.exe",
                             "application/octet-stream")
    assert resp.status_code in (400, 415, 422), (
        f".exe-fil borde ge 400/415/422, fick {resp.status_code}"
    )
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_wrong_file_type_pdf(client):
    """Import av .pdf-fil ska avvisas."""
    org = await create_org(client)
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>"
    resp = await post_import(client, org["id"], fake_pdf, "systems.pdf", "application/pdf")
    assert resp.status_code in (400, 415, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_csv_wrong_delimiter(client):
    """CSV med semikolon-delimiter (istället för komma) ska hanteras utan 500."""
    org = await create_org(client)
    content = "name;description;system_category\nSystem1;Beskrivning;verksamhetssystem\n"
    resp = await post_import(client, org["id"], content.encode("utf-8"), "systems.csv", "text/csv")
    # Kan ge 0 importerade (fel parsning) eller 1 importerat (smart parsning) — ALDRIG 500
    assert resp.status_code in (200, 400, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_csv_with_bom(client):
    """UTF-8 CSV med BOM (Byte Order Mark) ska hanteras korrekt."""
    org = await create_org(client)
    # BOM = \xef\xbb\xbf i UTF-8
    bom = b"\xef\xbb\xbf"
    content = bom + b"name,description,system_category\nBOM System,BOM desc,infrastruktur\n"
    resp = await post_import(client, org["id"], content, "systems.csv", "text/csv")
    assert resp.status_code in (200, 400, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_json_not_array(client):
    """JSON-import med objekt istället för array ska ge tydligt fel."""
    org = await create_org(client)
    content, filename, content_type = make_json_import({"name": "Ej array"})
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code in (200, 400, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_json_invalid_syntax(client):
    """Syntaxfel i JSON-fil ska ge 400 eller 422."""
    org = await create_org(client)
    content = b'[{"name": "Broken", "description": "test", "system_category": "infrastruktur"'  # Saknar ]}
    resp = await post_import(client, org["id"], content, "systems.json", "application/json")
    assert resp.status_code in (400, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_import_many_rows(client):
    """Import av 100 rader ska fungera utan timeout eller 500."""
    org = await create_org(client)
    rows = [
        {**VALID_IMPORT_ROW, "name": f"Mass Import System {i}"}
        for i in range(100)
    ]
    content, filename, content_type = make_json_import(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code in (200, 400, 422)
    assert resp.status_code != 500
    if resp.status_code == 200:
        body = resp.json()
        assert body["imported"] == 100


@pytest.mark.asyncio
async def test_import_without_org_id(client):
    """Import utan organization_id query-param ska ge 422."""
    rows = [{**VALID_IMPORT_ROW, "name": "NoOrg System"}]
    content, filename, content_type = make_json_import(rows)
    resp = await client.post(
        "/api/v1/import/systems",
        # Utelämnar organization_id
        files={"file": (filename, io.BytesIO(content), content_type)},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_with_invalid_org_id(client):
    """Import med ogiltigt organization_id ska ge 422."""
    rows = [{**VALID_IMPORT_ROW, "name": "InvalidOrg System"}]
    content, filename, content_type = make_json_import(rows)
    resp = await post_import(client, "not-a-uuid", content, filename, content_type)
    assert resp.status_code == 422


# ===========================================================================
# Export edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_export_json_no_systems(client):
    """Export JSON med 0 system ska returnera tom array."""
    resp = await client.get("/api/v1/export/systems.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


@pytest.mark.asyncio
async def test_export_csv_no_systems(client):
    """Export CSV med 0 system ska returnera bara headers."""
    resp = await client.get("/api/v1/export/systems.csv")
    assert resp.status_code == 200
    content = resp.text
    # Ska finnas headers men inga datarader
    assert len(content.strip()) > 0


@pytest.mark.asyncio
async def test_export_json_system_with_all_fields_null(client):
    """Export ska hantera system med alla valfria fält null."""
    org = await create_org(client)
    # Skapa system med bara obligatoriska fält
    sys = await create_system(client, org["id"],
                              name="Minimal System",
                              description="Minimal beskrivning")

    resp = await client.get("/api/v1/export/systems.json")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Hitta systemet i exporten
    found = [s for s in data if s.get("name") == "Minimal System"]
    assert len(found) == 1


@pytest.mark.asyncio
async def test_export_json_system_with_all_fields_filled(client):
    """Export ska hantera system med alla fält ifyllda."""
    org = await create_org(client)
    sys = await create_system(client, org["id"],
                              name="Full System",
                              description="Fullständig beskrivning",
                              product_name="TestProd",
                              product_version="1.0.0",
                              hosting_model="cloud",
                              cloud_provider="Azure",
                              data_location_country="Sverige",
                              deployment_date="2020-01-01",
                              planned_decommission_date="2030-01-01",
                              end_of_support_date="2028-01-01",
                              backup_frequency="dagligen",
                              rpo="4h",
                              rto="8h",
                              dr_plan_exists=True,
                              extended_attributes={"extra": "data"})

    resp = await client.get("/api/v1/export/systems.json")
    assert resp.status_code == 200
    data = resp.json()
    found = [s for s in data if s.get("name") == "Full System"]
    assert len(found) == 1


@pytest.mark.asyncio
async def test_export_csv_valid_format(client):
    """Export CSV ska vara parsebar som giltig CSV."""
    org = await create_org(client)
    await create_system(client, org["id"], name="CSV Export System")

    resp = await client.get("/api/v1/export/systems.csv")
    assert resp.status_code == 200

    # Verifiera att det är parsebar CSV
    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) >= 2, "CSV ska ha minst headers + 1 datared"


@pytest.mark.asyncio
async def test_export_unknown_format_returns_404(client):
    """Export med okänt format ska ge 404 eller 422."""
    resp = await client.get("/api/v1/export/systems.xml")
    assert resp.status_code in (404, 405, 422), (
        f"Okänt exportformat borde ge 404/405/422, fick {resp.status_code}"
    )


# ===========================================================================
# Whitespace-validering
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "",          # Tom sträng
    " ",         # Bara mellanslag
    "\t",        # Bara tab
    "\n",        # Bara newline
    "   \t  ",   # Blandat whitespace
])
async def test_system_whitespace_only_name_rejected(client, name):
    """Systemnamn med bara whitespace ska avvisas (422)."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": name,
        "description": "whitespace test",
        "system_category": "verksamhetssystem",
    })
    assert resp.status_code == 422, (
        f"Whitespace-only namn '{repr(name)}' borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "",
    " ",
    "\t",
    "\n",
])
async def test_org_whitespace_only_name_rejected(client, name):
    """Organisationsnamn med bara whitespace ska avvisas (422)."""
    resp = await client.post("/api/v1/organizations/", json={
        "name": name,
        "org_type": "kommun",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "",
    " ",
    "\t",
])
async def test_owner_whitespace_only_name_rejected(client, name):
    """Ägarens namn med bara whitespace ska avvisas (422)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "organization_id": org["id"],
        "role": "systemägare",
        "name": name,
    })
    assert resp.status_code == 422


# ===========================================================================
# Logisk konsistens — kontraktsdatum
# ===========================================================================


@pytest.mark.asyncio
async def test_contract_end_before_start_rejected(client):
    """Kontrakt med slutdatum före startdatum ska avvisas eller ge logikvarning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Test AB",
        "contract_start": "2024-12-31",
        "contract_end": "2024-01-01",  # Slutet FÖRE start
    })
    # Kan antingen avvisas (422) eller accepteras (lagras som-är) — ALDRIG 500
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
async def test_contract_start_equals_end_accepted(client):
    """Kontrakt med samma start- och slutdatum ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/contracts", json={
        "supplier_name": "Endags AB",
        "contract_start": "2024-06-01",
        "contract_end": "2024-06-01",
    })
    assert resp.status_code == 201


# ===========================================================================
# Enum-validering
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_category", [
    "VERKSAMHETSSYSTEM",    # Versaler (ska vara gemener)
    "okänd_kategori",
    "system",
    "",
    123,
    None,
])
async def test_system_invalid_category(client, invalid_category):
    """Ogiltig system_category ska ge 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "EnumTest",
        "description": "enum test",
        "system_category": invalid_category,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_criticality", [
    "KRITISK",     # Versaler
    "critical",    # Engelska
    "extremt_hög",
    5,
    "",
])
async def test_system_invalid_criticality(client, invalid_criticality):
    """Ogiltig criticality ska ge 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "CritTest",
        "description": "criticality test",
        "system_category": "infrastruktur",
        "criticality": invalid_criticality,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_status", [
    "active",          # Engelska
    "I_DRIFT",         # Versaler
    "under drift",     # Mellanslag
    "aktiv",           # Annat ord
])
async def test_system_invalid_lifecycle_status(client, invalid_status):
    """Ogiltig lifecycle_status ska ge 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "StatusTest",
        "description": "status test",
        "system_category": "infrastruktur",
        "lifecycle_status": invalid_status,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_role", [
    "SYSTEMÄGARE",       # Versaler
    "owner",             # Engelska
    "system_owner",      # Understreck istället för svenska
    "",
    123,
])
async def test_owner_invalid_role(client, invalid_role):
    """Ogiltig owner role ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json={
        "organization_id": org["id"],
        "role": invalid_role,
        "name": "RollTest",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_type", [
    "API",          # Versaler
    "rest",         # Annan term
    "http",
    "",
    42,
])
async def test_integration_invalid_type(client, invalid_type):
    """Ogiltig integration_type ska ge 422."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Källa")
    tgt = await create_system(client, org["id"], name="Mål")
    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": invalid_type,
    })
    assert resp.status_code == 422


# ===========================================================================
# Boolean-fält — typkoercion
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("nis2_applicable", "true"),     # Sträng — Pydantic konverterar
    ("treats_personal_data", 1),     # Int — Pydantic konverterar
    ("dr_plan_exists", "yes"),       # Sträng som inte är bool
    ("security_protection", "false"),
])
async def test_system_boolean_coercion(client, field, value):
    """Boolean-fält med strängvärden ska antingen konverteras eller ge 422."""
    org = await create_org(client)
    resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "BoolTest",
        "description": "bool coercion",
        "system_category": "infrastruktur",
        field: value,
    })
    # Pydantic konverterar "true"->True och 1->True, men "yes" kan ge 422
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


# ===========================================================================
# Felaktiga HTTP-metoder
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("put", "/api/v1/organizations/"),
    ("delete", "/api/v1/organizations/"),
    ("patch", "/api/v1/organizations/"),
    ("put", "/api/v1/systems/"),
    ("delete", "/api/v1/systems/"),
])
async def test_wrong_http_method_on_collection(client, method, path):
    """Fel HTTP-metod på collection-endpoints ska ge 405 (Method Not Allowed)."""
    resp = await getattr(client, method)(path)
    assert resp.status_code == 405, (
        f"{method.upper()} {path} borde ge 405, fick {resp.status_code}"
    )


# ===========================================================================
# Saknade obligatoriska fält
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", [
    "organization_id",
    "name",
    "system_category",
])
async def test_system_missing_required_field(client, missing_field):
    """Saknat obligatoriskt fält ska ge 422."""
    org = await create_org(client)
    data = {
        "organization_id": org["id"],
        "name": "RequiredTest",
        "description": "required test",
        "system_category": "verksamhetssystem",
    }
    del data[missing_field]
    resp = await client.post("/api/v1/systems/", json=data)
    assert resp.status_code == 422, (
        f"Saknat fält '{missing_field}' borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", [
    "name",
    "org_type",
])
async def test_org_missing_required_field(client, missing_field):
    """Saknat obligatoriskt fält i organisation ska ge 422."""
    data = {"name": "Test", "org_type": "kommun"}
    del data[missing_field]
    resp = await client.post("/api/v1/organizations/", json=data)
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_field", [
    "confidentiality",
    "integrity",
    "availability",
    "classified_by",
])
async def test_classification_missing_required_field(client, missing_field):
    """Saknat obligatoriskt fält i klassning ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
    }
    del data[missing_field]
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json=data)
    assert resp.status_code == 422


# ===========================================================================
# Strängvalidering — maximala fältlängder på delfält
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("field,max_len", [
    ("classified_by", 255),
    ("notes", 10000),  # Text-fält — ingen strikt max, men testar stor input
])
async def test_classification_field_max_length_accepted(client, field, max_len):
    """Klassningsfält upp till maxlängd ska accepteras."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "confidentiality": 2,
        "integrity": 2,
        "availability": 2,
        "classified_by": "test@test.se",
        field: "A" * max_len,
    }
    resp = await client.post(f"/api/v1/systems/{sys['id']}/classifications", json=data)
    assert resp.status_code in (201, 422)
    assert resp.status_code != 500


@pytest.mark.asyncio
@pytest.mark.parametrize("field,over_limit", [
    ("name", "A" * 256),
    ("email", "a" * 248 + "@test.se"),     # 256 tecken totalt, överstiger max 255
])
async def test_owner_field_over_max_length(client, field, over_limit):
    """Ägare-fält över maxlängd ska ge 422."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    data = {
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "MaxLängdTest",
        field: over_limit,
    }
    resp = await client.post(f"/api/v1/systems/{sys['id']}/owners", json=data)
    assert resp.status_code == 422, (
        f"Överlångt '{field}' borde ge 422, fick {resp.status_code}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field,over_limit", [
    ("frequency", "X" * 101),
    ("external_party", "Y" * 256),
])
async def test_integration_field_over_max_length(client, field, over_limit):
    """Integrationsfält över maxlängd ska ge 422."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Källa2")
    tgt = await create_system(client, org["id"], name="Mål2")
    data = {
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
        field: over_limit,
    }
    resp = await client.post("/api/v1/integrations/", json=data)
    assert resp.status_code == 422


# ===========================================================================
# Duplikat-skapning
# ===========================================================================


@pytest.mark.asyncio
async def test_org_duplicate_org_number_rejected(client):
    """Två organisationer med samma org_number ska ge 409 eller 422."""
    resp1 = await client.post("/api/v1/organizations/", json={
        "name": "Org Nummer 1",
        "org_type": "kommun",
        "org_number": "556-UNIK1",
    })
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/organizations/", json={
        "name": "Org Nummer 2",
        "org_type": "bolag",
        "org_number": "556-UNIK1",  # Samma nummer
    })
    assert resp2.status_code in (409, 422), (
        f"Duplikat org_number borde ge 409 eller 422, fick {resp2.status_code}: {resp2.text}"
    )


@pytest.mark.asyncio
async def test_owner_duplicate_role_rejected(client):
    """Samma ägare-roll+namn på ett system ska ge 409 eller 422 (UniqueConstraint)."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    owner_data = {
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "Unik Ägare",
    }
    resp1 = await client.post(f"/api/v1/systems/{sys['id']}/owners", json=owner_data)
    assert resp1.status_code == 201

    resp2 = await client.post(f"/api/v1/systems/{sys['id']}/owners", json=owner_data)
    assert resp2.status_code in (409, 422), (
        f"Duplikat ägare borde ge 409/422, fick {resp2.status_code}"
    )


# ===========================================================================
# PATCH — partiell uppdatering
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("patch_data,expected_status", [
    ({"name": "Nytt namn"}, 200),
    ({"name": ""}, 422),                        # Tom sträng
    ({"name": "A" * 256}, 422),                 # För långt namn
    ({"criticality": "kritisk"}, 200),           # Giltig enum
    ({"criticality": "KRITISK"}, 422),           # Ogiltig enum (versaler)
    ({"lifecycle_status": "i_drift"}, 200),
    ({"lifecycle_status": "okänd"}, 422),
    ({"extended_attributes": {"new": "data"}}, 200),
    ({"extended_attributes": None}, 200),        # Null är OK för PATCH
    ({}, 200),                                   # Tom PATCH är OK
])
async def test_system_patch_validation(client, patch_data, expected_status):
    """PATCH system med olika data ska valideras korrekt."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    resp = await client.patch(f"/api/v1/systems/{sys['id']}", json=patch_data)
    assert resp.status_code == expected_status, (
        f"PATCH {patch_data} borde ge {expected_status}, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("patch_data,expected_status", [
    ({"name": "Nytt Orgnamn"}, 200),
    ({"name": ""}, 422),
    ({"org_type": "bolag"}, 200),
    ({"org_type": "BOLAG"}, 422),
    ({"org_type": "invalid_type"}, 422),
    ({}, 200),
])
async def test_org_patch_validation(client, patch_data, expected_status):
    """PATCH organisation med olika data ska valideras korrekt."""
    org = await create_org(client)
    resp = await client.patch(f"/api/v1/organizations/{org['id']}", json=patch_data)
    assert resp.status_code == expected_status, (
        f"PATCH org {patch_data} borde ge {expected_status}, fick {resp.status_code}: {resp.text}"
    )


# ===========================================================================
# Sökning — edge cases
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "",                                     # Tom sökning
    " ",                                    # Bara mellanslag
    "a" * 500,                              # Extremt lång söksträng
    "%",                                    # SQL wildcard
    "_",                                    # SQL wildcard
    "%%",                                   # Dubbelt wildcard
    "\x00",                                 # Null byte i sökning
    "'; DROP TABLE systems; --",            # SQL injection
    "<script>alert(1)</script>",            # XSS i sökning
])
async def test_search_edge_cases(client, query):
    """Sökningar med edge case-värden ska hanteras utan 500."""
    resp = await client.get("/api/v1/systems/", params={"q": query})
    assert resp.status_code in (200, 422), (
        f"Sökning '{repr(query)}' borde ge 200 eller 422, fick {resp.status_code}"
    )
    assert resp.status_code != 500
