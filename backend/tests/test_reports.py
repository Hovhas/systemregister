"""
Tests for /api/v1/reports/nis2, /api/v1/reports/nis2.xlsx,
and /api/v1/reports/compliance-gap endpoints.

NOTE: These tests will FAIL until reports_router is registered in main.py.
The import exists (line 17) but app.include_router(reports_router, ...) is missing.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from tests.factories import (
    create_org,
    create_system,
    create_classification,
    create_owner,
    create_gdpr_treatment,
    create_contract,
)


# ---------------------------------------------------------------------------
# NIS2 Report (JSON)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_report_json(client):
    """GET /api/v1/reports/nis2 returns JSON with summary and systems list."""
    org = await create_org(client)

    # Create a NIS2-applicable system
    system = await create_system(client, org["id"],
        nis2_applicable=True,
        nis2_classification="väsentlig",
        criticality="kritisk",
        last_risk_assessment_date="2024-06-01",
    )

    resp = await client.get("/api/v1/reports/nis2")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()

    assert "generated_at" in body
    assert "summary" in body
    assert "systems" in body

    summary = body["summary"]
    assert "total" in summary
    assert "without_classification" in summary
    assert "without_risk_assessment" in summary
    assert isinstance(summary["total"], int)

    # The NIS2 system we created should appear
    system_ids = [s["id"] for s in body["systems"]]
    assert system["id"] in system_ids, "NIS2-applicable system should appear in report"

    # Verify structure of a system entry
    entry = next(s for s in body["systems"] if s["id"] == system["id"])
    assert entry["name"] == system["name"]
    assert entry["nis2_classification"] == "väsentlig"
    assert entry["criticality"] == "kritisk"
    assert "has_gdpr_treatment" in entry
    assert "owner_names" in entry
    assert isinstance(entry["owner_names"], list)


@pytest.mark.asyncio
async def test_nis2_report_excludes_non_nis2_systems(client):
    """GET /api/v1/reports/nis2 should not include systems with nis2_applicable=False."""
    org = await create_org(client)

    non_nis2 = await create_system(client, org["id"], name="NonNIS2System", nis2_applicable=False)

    resp = await client.get("/api/v1/reports/nis2")

    assert resp.status_code == 200
    system_ids = [s["id"] for s in resp.json()["systems"]]
    assert non_nis2["id"] not in system_ids, "Non-NIS2 system should not appear in NIS2 report"


@pytest.mark.asyncio
async def test_nis2_report_summary_counts_without_classification(client):
    """NIS2 summary should correctly count systems without nis2_classification."""
    org = await create_org(client)

    # System with nis2_applicable but no classification
    await create_system(client, org["id"], name="UnclassifiedNIS2",
        nis2_applicable=True,
        nis2_classification=None,
    )

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert summary["without_classification"] >= 1, "Should count system without classification"


@pytest.mark.asyncio
async def test_nis2_report_has_gdpr_treatment_flag(client):
    """NIS2 report should correctly indicate has_gdpr_treatment."""
    org = await create_org(client)

    system_with_gdpr = await create_system(client, org["id"], name=f"MedGDPR-{uuid4().hex[:6]}", nis2_applicable=True)
    system_without_gdpr = await create_system(client, org["id"], name=f"UtanGDPR-{uuid4().hex[:6]}", nis2_applicable=True)

    await create_gdpr_treatment(client, system_with_gdpr["id"])

    resp = await client.get("/api/v1/reports/nis2")
    assert resp.status_code == 200
    systems = {s["id"]: s for s in resp.json()["systems"]}

    assert systems[system_with_gdpr["id"]]["has_gdpr_treatment"] is True
    assert systems[system_without_gdpr["id"]]["has_gdpr_treatment"] is False


# ---------------------------------------------------------------------------
# NIS2 Report (XLSX)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nis2_report_xlsx(client):
    """GET /api/v1/reports/nis2.xlsx returns Excel file with correct content-type."""
    resp = await client.get("/api/v1/reports/nis2.xlsx")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ), f"Wrong content-type: {resp.headers.get('content-type')}"

    # Response should contain binary Excel data (not empty)
    assert len(resp.content) > 0, "XLSX response should not be empty"

    # Excel files start with PK magic bytes (ZIP format)
    assert resp.content[:2] == b"PK", "Response should be a valid ZIP/XLSX file"

    # Content-Disposition should suggest a filename
    content_disposition = resp.headers.get("content-disposition", "")
    assert "attachment" in content_disposition, "Should be sent as attachment"
    assert ".xlsx" in content_disposition, "Filename should contain .xlsx"


# ---------------------------------------------------------------------------
# Compliance Gap Report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_gap(client):
    """GET /api/v1/reports/compliance-gap returns report with expected structure."""
    resp = await client.get("/api/v1/reports/compliance-gap")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()

    assert "generated_at" in body
    assert "gaps" in body
    gaps = body["gaps"]

    assert "missing_classification" in gaps
    assert "missing_owner" in gaps
    assert "personal_data_without_gdpr" in gaps
    assert "nis2_without_risk_assessment" in gaps
    assert "expiring_contracts" in gaps

    assert isinstance(gaps["missing_classification"], list)
    assert isinstance(gaps["missing_owner"], list)
    assert isinstance(gaps["personal_data_without_gdpr"], list)
    assert isinstance(gaps["nis2_without_risk_assessment"], list)
    assert isinstance(gaps["expiring_contracts"], list)

    assert "summary" in body
    assert "total_gaps" in body["summary"]
    assert isinstance(body["summary"]["total_gaps"], int)


@pytest.mark.asyncio
async def test_compliance_gap_detects_missing_classification(client):
    """Compliance gap should include systems with no classification record."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="NoClassSystem")
    # Deliberately do NOT create a classification

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    no_class_ids = [s["id"] for s in gaps["missing_classification"]]
    assert system["id"] in no_class_ids, (
        f"System without classification should appear in missing_classification gap. "
        f"System id: {system['id']}, found: {no_class_ids}"
    )


@pytest.mark.asyncio
async def test_compliance_gap_classified_system_not_in_missing(client):
    """Systems WITH a classification should NOT appear in missing_classification."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="ClassifiedSystem")
    await create_classification(client, system["id"])

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    no_class_ids = [s["id"] for s in gaps["missing_classification"]]
    assert system["id"] not in no_class_ids, "Classified system should not appear in gap"


@pytest.mark.asyncio
async def test_compliance_gap_detects_missing_owner(client):
    """Compliance gap should include systems with no owner."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="NoOwnerSystem")
    # Deliberately do NOT create an owner

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    no_owner_ids = [s["id"] for s in gaps["missing_owner"]]
    assert system["id"] in no_owner_ids, (
        f"System without owner should appear in missing_owner gap. "
        f"System id: {system['id']}, found: {no_owner_ids}"
    )


@pytest.mark.asyncio
async def test_compliance_gap_system_with_owner_not_in_missing(client):
    """Systems WITH an owner should NOT appear in missing_owner gap."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="OwnedSystem")
    await create_owner(client, system["id"], org["id"])

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    no_owner_ids = [s["id"] for s in gaps["missing_owner"]]
    assert system["id"] not in no_owner_ids, "System with owner should not appear in gap"


@pytest.mark.asyncio
async def test_compliance_gap_personal_data_without_gdpr(client):
    """System with treats_personal_data=True but no GDPR treatment should appear in gap."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="PersonalDataNoGDPR", treats_personal_data=True)
    # No GDPR treatment created

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    personal_no_gdpr_ids = [s["id"] for s in gaps["personal_data_without_gdpr"]]
    assert system["id"] in personal_no_gdpr_ids, (
        "System with personal data but no GDPR treatment should appear in gap"
    )


@pytest.mark.asyncio
async def test_compliance_gap_personal_data_with_gdpr_not_in_gap(client):
    """System with personal data AND a GDPR treatment should NOT be in the gap."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="PersonalDataWithGDPR", treats_personal_data=True)
    await create_gdpr_treatment(client, system["id"])

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    personal_no_gdpr_ids = [s["id"] for s in gaps["personal_data_without_gdpr"]]
    assert system["id"] not in personal_no_gdpr_ids, (
        "System with personal data AND GDPR treatment should not appear in gap"
    )


@pytest.mark.asyncio
async def test_compliance_gap_expiring_contracts(client):
    """Compliance gap should include contracts expiring within 90 days."""
    org = await create_org(client)
    system = await create_system(client, org["id"], name="ExpContrSystem")

    today = date.today()
    expiring_soon = (today + timedelta(days=30)).isoformat()
    contract = await create_contract(client, system["id"], contract_end=expiring_soon)

    resp = await client.get("/api/v1/reports/compliance-gap")
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]

    expiring_ids = [c["id"] for c in gaps["expiring_contracts"]]
    assert contract["id"] in expiring_ids, "Contract expiring within 90 days should appear in gap"
