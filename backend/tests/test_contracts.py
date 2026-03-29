"""
Tests for /api/v1/systems/{id}/contracts, /api/v1/contracts/{id},
and /api/v1/contracts/expiring endpoints.
"""

import pytest
from datetime import date, timedelta

from tests.factories import create_org, create_system, create_contract


# ---------------------------------------------------------------------------
# Constants used in direct POST calls within tests
# ---------------------------------------------------------------------------

CONTRACT_BASE = {
    "supplier_name": "CGI Sverige AB",
    "supplier_org_number": "556975-4537",
    "contract_id_external": "KON-2022-0042",
    "auto_renewal": False,
    "notice_period_months": 6,
    "sla_description": "99.5% drifttid under kontorstid",
    "license_model": "per_användare",
    "annual_license_cost": 450000,
    "annual_operations_cost": 120000,
    "procurement_type": "ramavtal",
    "support_level": "8x5 telefonsupport",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contract(client):
    """POST /api/v1/systems/{id}/contracts returns 201 with correct fields."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    # Add dates explicitly for a complete contract
    payload = {
        **CONTRACT_BASE,
        "contract_start": "2022-01-01",
        "contract_end": "2025-12-31",
    }
    resp = await client.post(f"/api/v1/systems/{system_id}/contracts", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()

    assert body["system_id"] == system_id
    assert body["supplier_name"] == CONTRACT_BASE["supplier_name"]
    assert body["supplier_org_number"] == CONTRACT_BASE["supplier_org_number"]
    assert body["contract_id_external"] == CONTRACT_BASE["contract_id_external"]
    assert body["contract_start"] == "2022-01-01"
    assert body["contract_end"] == "2025-12-31"
    assert body["auto_renewal"] is False
    assert body["notice_period_months"] == CONTRACT_BASE["notice_period_months"]
    assert body["annual_license_cost"] == CONTRACT_BASE["annual_license_cost"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_contract_minimal(client):
    """POST contract with only required field (supplier_name) should succeed."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(
        f"/api/v1/systems/{system['id']}/contracts",
        json={"supplier_name": "Leverantören AB"},
    )

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["supplier_name"] == "Leverantören AB"
    assert body["contract_end"] is None
    assert body["auto_renewal"] is False


@pytest.mark.asyncio
async def test_list_contracts(client):
    """GET /api/v1/systems/{id}/contracts returns list of contracts."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    await create_contract(client, system_id, supplier_name="Leverantör A")
    await create_contract(client, system_id, supplier_name="Leverantör B")

    resp = await client.get(f"/api/v1/systems/{system_id}/contracts")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2, f"Expected at least 2 contracts, got {len(body)}"
    names = [c["supplier_name"] for c in body]
    assert "Leverantör A" in names
    assert "Leverantör B" in names


@pytest.mark.asyncio
async def test_list_contracts_empty(client):
    """GET /api/v1/systems/{id}/contracts on new system returns empty list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.get(f"/api/v1/systems/{system['id']}/contracts")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_contract(client):
    """PATCH /api/v1/contracts/{id} updates fields without touching others."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    contract = await create_contract(client, system["id"], **CONTRACT_BASE)
    contract_id = contract["id"]

    patch = {
        "supplier_name": "CGI Sverige AB (ny avdelning)",
        "annual_license_cost": 500000,
        "auto_renewal": True,
    }
    resp = await client.patch(f"/api/v1/contracts/{contract_id}", json=patch)

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["supplier_name"] == "CGI Sverige AB (ny avdelning)"
    assert body["annual_license_cost"] == 500000
    assert body["auto_renewal"] is True
    # Unpatched fields should remain
    assert body["notice_period_months"] == CONTRACT_BASE["notice_period_months"]
    assert body["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_update_contract_not_found(client):
    """PATCH /api/v1/contracts/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/api/v1/contracts/{fake_id}", json={"supplier_name": "Ghost"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_contract(client):
    """DELETE /api/v1/contracts/{id} removes contract and returns 204."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    contract = await create_contract(client, system["id"])
    contract_id = contract["id"]

    delete_resp = await client.delete(f"/api/v1/contracts/{contract_id}")
    assert delete_resp.status_code == 204, f"Expected 204: {delete_resp.text}"

    # Verify it's gone from the system's list
    list_resp = await client.get(f"/api/v1/systems/{system['id']}/contracts")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert contract_id not in ids, "Deleted contract should not appear in list"


@pytest.mark.asyncio
async def test_delete_contract_not_found(client):
    """DELETE /api/v1/contracts/{id} with non-existent id returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/contracts/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_contract_invalid_system(client):
    """POST /api/v1/systems/{id}/contracts with non-existent system returns 404."""
    fake_system_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/systems/{fake_system_id}/contracts",
        json=CONTRACT_BASE,
    )

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_expiring_contracts(client):
    """GET /api/v1/contracts/expiring?days=90 returns contracts expiring within window."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    today = date.today()
    expiring_soon = (today + timedelta(days=30)).isoformat()
    expiring_later = (today + timedelta(days=180)).isoformat()
    already_expired = (today - timedelta(days=1)).isoformat()

    contract_soon = await create_contract(
        client, system_id,
        supplier_name="Expires Soon Inc", contract_end=expiring_soon,
    )
    await create_contract(
        client, system_id,
        supplier_name="Expires Later Inc", contract_end=expiring_later,
    )
    await create_contract(
        client, system_id,
        supplier_name="Already Expired Inc", contract_end=already_expired,
    )

    resp = await client.get("/api/v1/contracts/expiring?days=90")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert isinstance(body, list)

    ids = [c["id"] for c in body]
    assert contract_soon["id"] in ids, "Contract expiring within 90 days should be included"

    # Contracts expiring after cutoff should NOT be included
    names = [c["supplier_name"] for c in body]
    assert "Expires Later Inc" not in names, "Contract expiring after 90 days should be excluded"
    assert "Already Expired Inc" not in names, "Already-expired contract should be excluded"


@pytest.mark.asyncio
async def test_expiring_contracts_default_days(client):
    """GET /api/v1/contracts/expiring without days param defaults to 90."""
    resp = await client.get("/api/v1/contracts/expiring")

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_expiring_contracts_custom_days(client):
    """GET /api/v1/contracts/expiring?days=N respects the N parameter."""
    org = await create_org(client)
    system = await create_system(client, org["id"])
    system_id = system["id"]

    today = date.today()
    expiring_60_days = (today + timedelta(days=60)).isoformat()

    contract = await create_contract(
        client, system_id,
        supplier_name="Sixty Days AB", contract_end=expiring_60_days,
    )

    # Should appear with days=90
    resp90 = await client.get("/api/v1/contracts/expiring?days=90")
    assert resp90.status_code == 200
    ids_90 = [c["id"] for c in resp90.json()]
    assert contract["id"] in ids_90, "Contract should appear in 90-day window"

    # Should NOT appear with days=30
    resp30 = await client.get("/api/v1/contracts/expiring?days=30")
    assert resp30.status_code == 200
    ids_30 = [c["id"] for c in resp30.json()]
    assert contract["id"] not in ids_30, "Contract should not appear in 30-day window"


@pytest.mark.asyncio
async def test_expiring_contracts_invalid_days(client):
    """GET /api/v1/contracts/expiring?days=0 returns 422 (validation)."""
    resp = await client.get("/api/v1/contracts/expiring?days=0")
    assert resp.status_code == 422, f"Expected 422 for days=0, got {resp.status_code}"


@pytest.mark.asyncio
async def test_contracts_scoped_to_system(client):
    """Contracts added to system A should not appear in system B's list."""
    org = await create_org(client)
    system_a = await create_system(client, org["id"], name="System A")
    system_b = await create_system(client, org["id"], name="System B")

    await create_contract(client, system_a["id"])

    resp = await client.get(f"/api/v1/systems/{system_b['id']}/contracts")
    assert resp.status_code == 200
    assert resp.json() == [], "System B should have no contracts"


# ---------------------------------------------------------------------------
# Extended tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expiring_contracts_today_boundary(client):
    """GET /api/v1/contracts/expiring?days=1 includes contracts expiring today."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    today = date.today()
    contract = await create_contract(
        client, system["id"],
        supplier_name="Today Expiry AB", contract_end=today.isoformat(),
    )

    resp = await client.get("/api/v1/contracts/expiring?days=1")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    # Contract ending today should be included in 1-day window
    assert contract["id"] in ids, "Contract expiring today should appear in 1-day window"


@pytest.mark.asyncio
async def test_expiring_contracts_no_end_date_excluded(client):
    """Contracts without contract_end date should not appear in expiring list."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    contract_no_end = await create_contract(
        client, system["id"],
        supplier_name="No End Date AB",
    )
    assert contract_no_end["contract_end"] is None

    resp = await client.get("/api/v1/contracts/expiring?days=365")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract_no_end["id"] not in ids, (
        "Contract with no end date should not appear in expiring list"
    )


@pytest.mark.asyncio
async def test_expiring_contracts_large_days_window(client):
    """GET /api/v1/contracts/expiring?days=3650 returns contracts in 10-year window."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    far_future = (date.today() + timedelta(days=3000)).isoformat()
    contract = await create_contract(
        client, system["id"],
        supplier_name="Far Future AB", contract_end=far_future,
    )

    resp = await client.get("/api/v1/contracts/expiring?days=3650")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert contract["id"] in ids, "Contract within 10-year window should be included"


@pytest.mark.asyncio
async def test_contract_auto_renewal_true(client):
    """POST contract with auto_renewal=True stores and retrieves correctly."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Auto Renewal AB",
        "auto_renewal": True,
        "notice_period_months": 12,
    })
    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["auto_renewal"] is True
    assert body["notice_period_months"] == 12


@pytest.mark.asyncio
async def test_contract_notice_period_zero_boundary(client):
    """POST contract with notice_period_months=0 — check if accepted or rejected."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Zero Notice AB",
        "notice_period_months": 0,
    })
    # 0 may be valid or invalid — just not 500
    assert resp.status_code in (201, 422), (
        f"notice_period_months=0 should return 201 or 422, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_expiring_contracts_response_includes_system_id(client):
    """Contracts in expiring list include system_id for context."""
    org = await create_org(client)
    system = await create_system(client, org["id"])

    expiring = (date.today() + timedelta(days=15)).isoformat()
    contract = await create_contract(
        client, system["id"],
        supplier_name="Response Fields AB", contract_end=expiring,
    )

    resp = await client.get("/api/v1/contracts/expiring?days=30")
    assert resp.status_code == 200
    matching = [c for c in resp.json() if c["id"] == contract["id"]]
    assert len(matching) == 1
    assert "system_id" in matching[0], "Expiring contract response must include system_id"
    assert matching[0]["system_id"] == system["id"]


@pytest.mark.asyncio
async def test_contract_end_before_start_rejected_or_accepted(client):
    """POST contract med contract_end före contract_start skall ge 422.

    ContractCreate-schemat har en model_validator som validerar
    att contract_end >= contract_start.
    """
    org = await create_org(client)
    system = await create_system(client, org["id"])

    resp = await client.post(f"/api/v1/systems/{system['id']}/contracts", json={
        "supplier_name": "Ogiltigt Avtal AB",
        "contract_start": "2025-12-31",
        "contract_end": "2024-01-01",  # slut före start
    })
    assert resp.status_code == 422, (
        f"contract_end före contract_start borde ge 422, fick {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "detail" in body, "Svaret borde innehålla 'detail' med valideringsfel"
