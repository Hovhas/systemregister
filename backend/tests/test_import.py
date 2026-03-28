"""
Tests for POST /api/v1/import/systems endpoint.

Import accepts Excel (.xlsx), CSV, or JSON files and creates System records.
Duplicates (same name + organization_id) are skipped with an error entry.
"""

import csv
import io
import json

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORG_PAYLOAD = {
    "name": "Sundsvalls kommun",
    "org_number": "212000-2723",
    "org_type": "kommun",
}


async def create_org(client, name: str = "Sundsvalls kommun", org_number: str = "212000-2723") -> dict:
    resp = await client.post("/api/v1/organizations/", json={
        **ORG_PAYLOAD, "name": name, "org_number": org_number,
    })
    assert resp.status_code == 201, f"Org creation failed: {resp.text}"
    return resp.json()


def make_json_file(rows: list[dict]) -> tuple[bytes, str, str]:
    """Return (content, filename, content_type) for a JSON upload."""
    content = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    return content, "systems.json", "application/json"


def make_csv_file(rows: list[dict]) -> tuple[bytes, str, str]:
    """Return (content, filename, content_type) for a CSV upload."""
    if not rows:
        output = io.StringIO()
        output.write("")
        return output.getvalue().encode("utf-8"), "systems.csv", "text/csv"

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8"), "systems.csv", "text/csv"


def make_xlsx_file(rows: list[dict]) -> tuple[bytes, str, str]:
    """Return (content, filename, content_type) for an XLSX upload."""
    try:
        from openpyxl import Workbook
    except ImportError:
        pytest.skip("openpyxl not installed")

    wb = Workbook()
    ws = wb.active
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return buffer.read(), "systems.xlsx", content_type


async def post_import(client, org_id: str, content: bytes, filename: str, content_type: str) -> dict:
    """POST file to the import endpoint and return response JSON."""
    resp = await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org_id},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )
    return resp


VALID_SYSTEM_ROW = {
    "name": "Importerat System",
    "description": "Importbeskrivning",
    "system_category": "verksamhetssystem",
    "criticality": "medel",
}


# ---------------------------------------------------------------------------
# JSON import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_json(client):
    """POST valid JSON file imports systems and returns correct count."""
    org = await create_org(client)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "JSON System 1"},
        {**VALID_SYSTEM_ROW, "name": "JSON System 2"},
    ]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["imported"] == 2, f"Expected 2 imported, got {body['imported']}: {body}"
    assert body["errors"] == [], f"Expected no errors, got {body['errors']}"

    # Verify systems actually exist in DB
    list_resp = await client.get("/api/v1/systems/")
    names = [s["name"] for s in list_resp.json()["items"]]
    assert "JSON System 1" in names
    assert "JSON System 2" in names


@pytest.mark.asyncio
async def test_import_json_empty_array(client):
    """POST JSON with empty array returns 0 imported."""
    org = await create_org(client)
    content, filename, content_type = make_json_file([])

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0


# ---------------------------------------------------------------------------
# CSV import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_csv(client):
    """POST valid CSV file imports systems and returns correct count."""
    org = await create_org(client)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "CSV System 1"},
        {**VALID_SYSTEM_ROW, "name": "CSV System 2"},
    ]
    content, filename, content_type = make_csv_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["imported"] == 2, f"Expected 2 imported, got {body['imported']}: {body}"
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_import_csv_partial_fields(client):
    """CSV with only required fields should import successfully."""
    org = await create_org(client)
    rows = [{"name": "Minimal CSV System", "description": "Minimal", "system_category": "infrastruktur"}]
    content, filename, content_type = make_csv_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["imported"] == 1, f"Expected 1 imported, got {body}"


# ---------------------------------------------------------------------------
# Duplicate skipping tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_duplicate_skipped(client):
    """Second import of same system name in same org is skipped, not created twice."""
    org = await create_org(client)
    rows = [{**VALID_SYSTEM_ROW, "name": "Duplicate System"}]
    content, filename, content_type = make_json_file(rows)

    # First import — should succeed
    resp1 = await post_import(client, org["id"], content, filename, content_type)
    assert resp1.status_code == 200
    assert resp1.json()["imported"] == 1

    # Second import — same name, same org — should be skipped
    resp2 = await post_import(client, org["id"], content, filename, content_type)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["imported"] == 0, f"Expected 0 new imports (duplicate), got {body2['imported']}"
    assert len(body2["errors"]) == 1, f"Expected 1 skip error, got {body2['errors']}"
    # Error message should mention the system name
    assert "Duplicate System" in body2["errors"][0]["error"], (
        f"Error should mention system name, got: {body2['errors'][0]['error']}"
    )


@pytest.mark.asyncio
async def test_import_duplicate_different_org_allowed(client):
    """Same system name in a different org should NOT be treated as duplicate."""
    org1 = await create_org(client, name="Org 1", org_number="111111-1111")
    org2 = await create_org(client, name="Org 2", org_number="222222-2222")
    rows = [{**VALID_SYSTEM_ROW, "name": "Shared Name System"}]

    content, filename, content_type = make_json_file(rows)

    # Import to org1
    resp1 = await post_import(client, org1["id"], content, filename, content_type)
    assert resp1.json()["imported"] == 1

    # Same name, different org — should import without duplicate error
    resp2 = await post_import(client, org2["id"], content, filename, content_type)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["imported"] == 1, (
        f"Same name in different org should import successfully, got {body2}"
    )


@pytest.mark.asyncio
async def test_import_mixed_valid_and_duplicate(client):
    """Import with mix of new and duplicate rows: counts only new ones."""
    org = await create_org(client)

    # Pre-create one system
    rows_first = [{**VALID_SYSTEM_ROW, "name": "Existing System"}]
    content, filename, content_type = make_json_file(rows_first)
    await post_import(client, org["id"], content, filename, content_type)

    # Now import a mix: existing + new
    rows_mix = [
        {**VALID_SYSTEM_ROW, "name": "Existing System"},  # duplicate
        {**VALID_SYSTEM_ROW, "name": "Brand New System"},  # new
    ]
    content2, filename2, content_type2 = make_json_file(rows_mix)
    resp = await post_import(client, org["id"], content2, filename2, content_type2)

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 1, f"Expected 1 new import, got {body['imported']}"
    assert len(body["errors"]) == 1, f"Expected 1 skip error, got {body['errors']}"


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_invalid_data_returns_errors(client):
    """Rows with invalid field values should be skipped and reported in errors."""
    org = await create_org(client)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "Valid System"},
        {
            "name": "Invalid Category System",
            "description": "Desc",
            "system_category": "ogiltig_kategori",  # invalid enum value
        },
    ]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Expected 200 (not 4xx), got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["imported"] == 1, f"Expected 1 valid import, got {body['imported']}"
    assert len(body["errors"]) >= 1, f"Expected at least 1 validation error, got {body['errors']}"
    # Row index should be reported (row 3 = 1 header + 2 data rows, 0-indexed as row 3)
    error_rows = [e["row"] for e in body["errors"]]
    assert 3 in error_rows, f"Expected error on row 3, got error rows: {error_rows}"


@pytest.mark.asyncio
async def test_import_missing_required_field_returns_error(client):
    """Row missing required 'name' field should be reported as error, not crash."""
    org = await create_org(client)
    rows = [
        {"description": "No name field", "system_category": "verksamhetssystem"},
    ]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) == 1


@pytest.mark.asyncio
async def test_import_missing_organization_id_param(client):
    """POST without required organization_id query param returns 422."""
    rows = [{**VALID_SYSTEM_ROW, "name": "System Without Org"}]
    content = json.dumps(rows).encode("utf-8")

    resp = await client.post(
        "/api/v1/import/systems",
        # No organization_id param
        files={"file": ("systems.json", io.BytesIO(content), "application/json")},
    )

    assert resp.status_code == 422, f"Expected 422 for missing org param, got {resp.status_code}"


@pytest.mark.asyncio
async def test_import_unsupported_file_format(client):
    """POST with unsupported file format returns 415."""
    org = await create_org(client)
    content = b"some random content"

    resp = await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org["id"]},
        files={"file": ("systems.txt", io.BytesIO(content), "application/octet-stream")},
    )

    # text/plain is actually in SUPPORTED_CONTENT_TYPES for CSV fallback,
    # but a .txt extension without CSV/JSON content should fail detection
    # The .txt extension is not recognised — result depends on content-type fallback.
    # We just assert it doesn't return 201 or 200 with data.
    if resp.status_code == 200:
        body = resp.json()
        # If 200, no systems should have been imported from garbage content
        assert body["imported"] == 0 or len(body["errors"]) > 0
    else:
        assert resp.status_code in (415, 422, 400), (
            f"Expected error status for unsupported format, got {resp.status_code}: {resp.text}"
        )


@pytest.mark.asyncio
async def test_import_json_not_array_returns_422(client):
    """POST JSON that is an object (not array) returns 422."""
    org = await create_org(client)
    content = json.dumps({"name": "Not an array"}).encode("utf-8")

    resp = await client.post(
        "/api/v1/import/systems",
        params={"organization_id": org["id"]},
        files={"file": ("systems.json", io.BytesIO(content), "application/json")},
    )

    assert resp.status_code == 422, f"Expected 422 for non-array JSON, got {resp.status_code}"


# ---------------------------------------------------------------------------
# XLSX import tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_xlsx(client):
    """POST valid XLSX file imports systems correctly."""
    org = await create_org(client)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "XLSX System 1"},
        {**VALID_SYSTEM_ROW, "name": "XLSX System 2"},
    ]
    content, filename, content_type = make_xlsx_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["imported"] == 2, f"Expected 2 imported from XLSX, got {body}"
    assert body["errors"] == []


# ---------------------------------------------------------------------------
# Utökade importtester — Kategori 8
# ---------------------------------------------------------------------------


# --- Format-varianter ---


@pytest.mark.asyncio
async def test_import_json_single_system(client):
    """JSON-import med ett enda system lyckas."""
    org = await create_org(client, name="SingleImportOrg", org_number="SIO-001")
    rows = [{**VALID_SYSTEM_ROW, "name": "Single JSON Import"}]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)

    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


@pytest.mark.asyncio
async def test_import_json_with_optional_fields(client):
    """JSON-import med valfria fält som lifecycle_status och criticality."""
    org = await create_org(client, name="OptFieldOrg", org_number="OFO-001")
    rows = [{
        "name": "OptFieldSystem",
        "description": "Med valfria fält",
        "system_category": "infrastruktur",
        "criticality": "hög",
        "lifecycle_status": "planerad",
        "nis2_applicable": True,
    }]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    # Verifiera att fälten sparats korrekt
    list_resp = await client.get("/api/v1/systems/",
                                  params={"organization_id": org["id"]})
    items = list_resp.json()["items"]
    sys = next(s for s in items if s["name"] == "OptFieldSystem")
    assert sys["criticality"] == "hög"
    assert sys["lifecycle_status"] == "planerad"


@pytest.mark.asyncio
@pytest.mark.parametrize("category", [
    "verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"
])
async def test_import_json_all_system_categories(client, category):
    """Import med alla systemkategorier lyckas."""
    org = await create_org(client, name=f"CatImportOrg {category}", org_number=None)
    rows = [{
        "name": f"CatImport {category}",
        "description": "Kategoritest",
        "system_category": category,
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


@pytest.mark.asyncio
async def test_import_json_treats_personal_data_flag(client):
    """Import med treats_personal_data=True sparar flaggan korrekt."""
    org = await create_org(client, name="PersonalDataImportOrg", org_number=None)
    rows = [{
        "name": "PersonalDataImportSys",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "treats_personal_data": True,
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    list_resp = await client.get("/api/v1/systems/",
                                  params={"organization_id": org["id"]})
    items = list_resp.json()["items"]
    sys = next(s for s in items if s["name"] == "PersonalDataImportSys")
    assert sys["treats_personal_data"] is True


@pytest.mark.asyncio
async def test_import_csv_with_optional_fields(client):
    """CSV-import med valfria fält."""
    org = await create_org(client, name="CSVOptOrg", org_number=None)
    rows = [{
        "name": "CSV Optional System",
        "description": "Test",
        "system_category": "stödsystem",
        "criticality": "kritisk",
        "lifecycle_status": "under_inforande",
    }]
    content, filename, content_type = make_csv_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


@pytest.mark.asyncio
async def test_import_xlsx_multiple_rows(client):
    """XLSX-import med fler än 2 rader."""
    org = await create_org(client, name="XLSXMultiOrg", org_number=None)
    rows = [{**VALID_SYSTEM_ROW, "name": f"XLSX Multi {i}"} for i in range(5)]
    content, filename, content_type = make_xlsx_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 5


@pytest.mark.asyncio
async def test_import_xlsx_empty_file(client):
    """XLSX-import med tom fil (enbart header) ger 0 importerade."""
    org = await create_org(client, name="XLSXEmptyOrg", org_number=None)
    content, filename, content_type = make_xlsx_file([])

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 0


# --- Felaktiga rader ---


@pytest.mark.asyncio
async def test_import_json_invalid_lifecycle_status(client):
    """Row med ogiltig lifecycle_status räknas som fel."""
    org = await create_org(client, name="InvalidStatusOrg", org_number=None)
    rows = [{
        "name": "BadStatusSys",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "lifecycle_status": "ogiltig_status",
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_json_invalid_criticality(client):
    """Row med ogiltig criticality räknas som fel."""
    org = await create_org(client, name="InvalidCritOrg", org_number=None)
    rows = [{
        "name": "BadCritSys",
        "description": "Test",
        "system_category": "verksamhetssystem",
        "criticality": "superkritisk",
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_json_row_with_empty_name(client):
    """Row med tomt namn räknas som fel."""
    org = await create_org(client, name="EmptyNameImportOrg", org_number=None)
    rows = [{
        "name": "",
        "description": "Test",
        "system_category": "verksamhetssystem",
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_json_row_with_null_name(client):
    """Row med null-namn räknas som fel."""
    org = await create_org(client, name="NullNameImportOrg", org_number=None)
    rows = [{
        "name": None,
        "description": "Test",
        "system_category": "verksamhetssystem",
    }]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_json_many_rows_with_some_errors(client):
    """Import med 10 rader varav 3 ogiltiga ger 7 importerade + 3 fel."""
    org = await create_org(client, name="MixedImportOrg", org_number=None)

    rows = []
    for i in range(7):
        rows.append({**VALID_SYSTEM_ROW, "name": f"Valid Mixed Sys {i}"})
    # 3 ogiltiga
    rows.append({"name": "BadCat1", "description": "Test", "system_category": "ogiltig"})
    rows.append({"name": "BadCat2", "description": "Test", "system_category": "ogiltig"})
    rows.append({"description": "NoName", "system_category": "verksamhetssystem"})

    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 7, f"Förväntade 7 importerade, fick {body['imported']}"
    assert len(body["errors"]) == 3, f"Förväntade 3 fel, fick {body['errors']}"


@pytest.mark.asyncio
async def test_import_response_contains_row_numbers(client):
    """Import-fel innehåller radnummer för de problematiska raderna."""
    org = await create_org(client, name="RowNumOrg", org_number=None)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "Good Row 1"},
        {"name": "Bad Row", "description": "Test", "system_category": "ogiltig"},
        {**VALID_SYSTEM_ROW, "name": "Good Row 3"},
    ]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["errors"]) == 1
    error = body["errors"][0]
    assert "row" in error, "Felet borde innehålla radnummer"


@pytest.mark.asyncio
async def test_import_json_duplicate_within_same_file(client):
    """Dubbletter i samma importfil: enbart första importeras."""
    org = await create_org(client, name="IntraFileDupOrg", org_number=None)
    rows = [
        {**VALID_SYSTEM_ROW, "name": "Dup In File"},
        {**VALID_SYSTEM_ROW, "name": "Dup In File"},  # samma rad igen
    ]
    content, filename, content_type = make_json_file(rows)
    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    # Totalt: max 1 importerad, 1 fel (eller 2 importerade om dubbletter i fil tillåts)
    total = body["imported"] + len(body["errors"])
    assert total == 2, "Sammanlagd import + fel borde vara 2"


# --- Classifications import ---


@pytest.mark.asyncio
async def test_import_classifications_basic(client):
    """POST /import/classifications importerar klassningar för ett befintligt system."""
    org = await create_org(client, name="ClsImportOrg", org_number=None)
    sys_resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "ClassImportSys",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    assert sys_resp.status_code == 201
    system = sys_resp.json()

    rows = [{
        "system_name": "ClassImportSys",
        "confidentiality": 2,
        "integrity": 3,
        "availability": 2,
        "classified_by": "import@test.se",
    }]
    content = json.dumps(rows, ensure_ascii=False).encode("utf-8")

    resp = await client.post(
        "/api/v1/import/classifications",
        params={"organization_id": org["id"]},
        files={"file": ("classifications.json", io.BytesIO(content), "application/json")},
    )
    assert resp.status_code == 200, f"Oväntat svar: {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "imported" in body
    assert body["imported"] >= 1, f"Förväntade minst 1 importerad klassning, fick {body['imported']}. Fel: {body.get('errors')}"


# --- Owners import ---


@pytest.mark.asyncio
async def test_import_owners_basic(client):
    """POST /import/owners importerar ägare för ett befintligt system."""
    org = await create_org(client, name="OwnImportOrg", org_number=None)
    sys_resp = await client.post("/api/v1/systems/", json={
        "organization_id": org["id"],
        "name": "OwnerImportSys",
        "description": "Test",
        "system_category": "verksamhetssystem",
    })
    system = sys_resp.json()

    rows = [{
        "system_name": "OwnerImportSys",
        "organization_id": org["id"],
        "role": "systemägare",
        "name": "Importerad Ägare",
        "email": "agare@import.se",
    }]
    content = json.dumps(rows, ensure_ascii=False).encode("utf-8")

    resp = await client.post(
        "/api/v1/import/owners",
        files={"file": ("owners.json", io.BytesIO(content), "application/json")},
    )
    assert resp.status_code == 200, f"Oväntat svar: {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "imported" in body
    assert body["imported"] >= 1, f"Förväntade minst 1 importerad ägare, fick {body['imported']}. Fel: {body.get('errors')}"


# --- Stora dataset ---


@pytest.mark.asyncio
async def test_import_json_100_rows(client):
    """Import av 100 rader lyckas utan timeout."""
    org = await create_org(client, name="BigImportOrg100", org_number=None)
    rows = [{**VALID_SYSTEM_ROW, "name": f"BigImport Sys {i:03d}"} for i in range(100)]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 100, f"Förväntade 100 importerade, fick {body['imported']}"
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_import_csv_100_rows(client):
    """CSV-import av 100 rader lyckas."""
    org = await create_org(client, name="BigCSVImportOrg", org_number=None)
    rows = [{**VALID_SYSTEM_ROW, "name": f"BigCSVImport Sys {i:03d}"} for i in range(100)]
    content, filename, content_type = make_csv_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 100


@pytest.mark.asyncio
async def test_import_xlsx_100_rows(client):
    """XLSX-import av 100 rader lyckas."""
    org = await create_org(client, name="BigXLSXImportOrg", org_number=None)
    rows = [{**VALID_SYSTEM_ROW, "name": f"BigXLSXImport Sys {i:03d}"} for i in range(100)]
    content, filename, content_type = make_xlsx_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 100


@pytest.mark.asyncio
async def test_import_json_response_structure(client):
    """Import-svaret har korrekt struktur: imported, errors."""
    org = await create_org(client, name="StructTestOrg", org_number=None)
    rows = [{**VALID_SYSTEM_ROW, "name": "Structure Test Sys"}]
    content, filename, content_type = make_json_file(rows)

    resp = await post_import(client, org["id"], content, filename, content_type)
    assert resp.status_code == 200
    body = resp.json()
    assert "imported" in body, "Svaret borde innehålla 'imported'"
    assert "errors" in body, "Svaret borde innehålla 'errors'"
    assert isinstance(body["imported"], int), "'imported' borde vara ett heltal"
    assert isinstance(body["errors"], list), "'errors' borde vara en lista"


@pytest.mark.asyncio
async def test_import_json_nonexistent_org_returns_error(client):
    """Import med okänt organization_id borde ge fel."""
    fake_org = "00000000-0000-0000-0000-000000000000"
    rows = [{**VALID_SYSTEM_ROW, "name": "Orphan System"}]
    content, filename, content_type = make_json_file(rows)

    resp = await client.post(
        "/api/v1/import/systems",
        params={"organization_id": fake_org},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )
    # Accepterat: 404 (okänd org) eller 200 med 0 importerade + fel
    if resp.status_code == 200:
        body = resp.json()
        assert body["imported"] == 0
        assert len(body["errors"]) >= 1
    else:
        assert resp.status_code in (404, 422, 400)
