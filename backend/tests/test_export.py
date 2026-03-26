"""
Tests for /api/v1/export endpoints (JSON, CSV, XLSX).
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

SYSTEM_BASE = {
    "description": "Testbeskrivning",
    "system_category": "verksamhetssystem",
    "criticality": "medel",
}


async def create_org(client, name: str = "Sundsvalls kommun", org_number: str = "212000-2723") -> dict:
    payload = {**ORG_PAYLOAD, "name": name, "org_number": org_number}
    resp = await client.post("/api/v1/organizations/", json=payload)
    assert resp.status_code == 201, f"Org creation failed: {resp.text}"
    return resp.json()


async def create_system(client, org_id: str, name: str) -> dict:
    payload = {**SYSTEM_BASE, "organization_id": org_id, "name": name}
    resp = await client.post("/api/v1/systems/", json=payload)
    assert resp.status_code == 201, f"System creation failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_json(client):
    """GET /api/v1/export/systems.json returns a valid JSON array of systems."""
    org = await create_org(client)
    await create_system(client, org["id"], "Procapita")
    await create_system(client, org["id"], "Visma Lön")

    resp = await client.get("/api/v1/export/systems.json")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"

    # Verify Content-Disposition header
    content_disposition = resp.headers.get("content-disposition", "")
    assert "systems.json" in content_disposition, (
        f"Expected filename in Content-Disposition, got: {content_disposition}"
    )

    # Verify parseable JSON array
    data = resp.json()
    assert isinstance(data, list), "Response should be a JSON array"
    assert len(data) >= 2, f"Expected at least 2 systems, got {len(data)}"

    # Verify expected fields are present
    first = data[0]
    assert "name" in first
    assert "system_category" in first
    assert "criticality" in first
    assert "lifecycle_status" in first


@pytest.mark.asyncio
async def test_export_json_empty(client):
    """GET /api/v1/export/systems.json with no systems returns empty array."""
    resp = await client.get("/api/v1/export/systems.json")

    assert resp.status_code == 200
    data = resp.json()
    assert data == [], f"Expected empty array, got {data}"


@pytest.mark.asyncio
async def test_export_csv(client):
    """GET /api/v1/export/systems.csv returns valid CSV with headers and data rows."""
    org = await create_org(client)
    await create_system(client, org["id"], "Procapita")
    await create_system(client, org["id"], "Pulsen Combine")

    resp = await client.get("/api/v1/export/systems.csv")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"

    # Verify Content-Type
    content_type = resp.headers.get("content-type", "")
    assert "text/csv" in content_type, f"Expected text/csv, got: {content_type}"

    # Verify Content-Disposition
    content_disposition = resp.headers.get("content-disposition", "")
    assert "systems.csv" in content_disposition, (
        f"Expected filename in Content-Disposition, got: {content_disposition}"
    )

    # Parse and validate CSV
    text = resp.text
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) >= 2, f"Expected at least 2 data rows, got {len(rows)}"

    # Header should include expected columns
    fieldnames = reader.fieldnames or []
    assert "name" in fieldnames, "CSV should have 'name' column"
    assert "system_category" in fieldnames, "CSV should have 'system_category' column"
    assert "criticality" in fieldnames, "CSV should have 'criticality' column"

    # Data values should be populated
    names = [row["name"] for row in rows]
    assert "Procapita" in names or "Pulsen Combine" in names, (
        f"Expected created systems in export, got names: {names}"
    )


@pytest.mark.asyncio
async def test_export_csv_empty(client):
    """GET /api/v1/export/systems.csv with no systems returns only header row."""
    resp = await client.get("/api/v1/export/systems.csv")

    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/csv" in content_type

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert rows == [], "Expected no data rows in empty export"


@pytest.mark.asyncio
async def test_export_xlsx(client):
    """GET /api/v1/export/systems.xlsx returns valid XLSX with correct Content-Type."""
    org = await create_org(client)
    await create_system(client, org["id"], "Procapita")

    resp = await client.get("/api/v1/export/systems.xlsx")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"

    # Verify Content-Type for Excel
    content_type = resp.headers.get("content-type", "")
    assert "spreadsheetml.sheet" in content_type, (
        f"Expected OOXML content-type, got: {content_type}"
    )

    # Verify Content-Disposition
    content_disposition = resp.headers.get("content-disposition", "")
    assert "systems.xlsx" in content_disposition, (
        f"Expected xlsx filename in Content-Disposition, got: {content_disposition}"
    )

    # Verify the bytes are a valid XLSX (ZIP magic bytes: PK\x03\x04)
    content = resp.content
    assert content[:4] == b"PK\x03\x04", "XLSX file should start with ZIP magic bytes"


@pytest.mark.asyncio
async def test_export_xlsx_parseable(client):
    """GET /api/v1/export/systems.xlsx returns a file parseable by openpyxl."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        pytest.skip("openpyxl not installed")

    org = await create_org(client)
    await create_system(client, org["id"], "Procapita")
    await create_system(client, org["id"], "Visma Lön")

    resp = await client.get("/api/v1/export/systems.xlsx")
    assert resp.status_code == 200

    wb = load_workbook(filename=io.BytesIO(resp.content))
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    # First row is header, subsequent rows are data
    assert len(rows) >= 3, f"Expected header + at least 2 data rows, got {len(rows)}"
    header = rows[0]
    assert "name" in header, "Header row should contain 'name'"


@pytest.mark.asyncio
async def test_export_filtered_by_org(client):
    """Export with organization_id filter returns only that org's systems."""
    org1 = await create_org(client, name="Org 1", org_number="111111-1111")
    org2 = await create_org(client, name="Org 2", org_number="222222-2222")

    await create_system(client, org1["id"], "Org1 System")
    await create_system(client, org2["id"], "Org2 System")

    # Export only org1's systems as JSON
    resp = await client.get("/api/v1/export/systems.json", params={"organization_id": org1["id"]})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1, f"Expected 1 system for org1, got {len(data)}"
    assert data[0]["name"] == "Org1 System", f"Expected 'Org1 System', got {data[0]['name']}"


@pytest.mark.asyncio
async def test_export_filtered_by_org_csv(client):
    """CSV export with organization_id filter returns only that org's systems."""
    org1 = await create_org(client, name="Filter Org A", org_number="333333-3333")
    org2 = await create_org(client, name="Filter Org B", org_number="444444-4444")

    await create_system(client, org1["id"], "Org A System")
    await create_system(client, org2["id"], "Org B System")

    resp = await client.get("/api/v1/export/systems.csv", params={"organization_id": org1["id"]})

    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1, f"Expected 1 row for org A, got {len(rows)}"
    assert rows[0]["name"] == "Org A System"

    # Verify the filename includes the org id
    content_disposition = resp.headers.get("content-disposition", "")
    assert org1["id"] in content_disposition, (
        f"Filtered export filename should include org id, got: {content_disposition}"
    )


@pytest.mark.asyncio
async def test_export_sorted_by_name(client):
    """Exported JSON should be sorted alphabetically by name."""
    org = await create_org(client)
    await create_system(client, org["id"], "Zebra System")
    await create_system(client, org["id"], "Alpha System")
    await create_system(client, org["id"], "Medel System")

    resp = await client.get("/api/v1/export/systems.json")

    assert resp.status_code == 200
    data = resp.json()
    names = [row["name"] for row in data]
    assert names == sorted(names), f"Export should be sorted by name, got: {names}"
