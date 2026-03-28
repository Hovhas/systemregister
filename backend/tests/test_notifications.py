"""
Tests for /api/v1/notifications/ endpoint.

Kategori 11: Notifikationer (~35 testfall)

Known bug: Notifications endpoint lacks pagination — returns ALL items
without limit/offset support. Regression tests document this behavior.
"""

import pytest
from datetime import date, timedelta
from tests.factories import (
    create_org, create_system, create_classification,
    create_owner, create_contract, create_gdpr_treatment,
)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notifications_returns_200(client):
    """GET /api/v1/notifications/ returns 200."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_notifications_response_structure(client):
    """Notifications response has required keys: total, by_severity, notifications."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body, "Missing key: total"
    assert "by_severity" in body, "Missing key: by_severity"
    assert "items" in body, "Missing key: notifications"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert isinstance(body["by_severity"], dict)


@pytest.mark.asyncio
async def test_notifications_empty_db_returns_zero(client):
    """Empty DB should produce zero notifications."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_notifications_total_matches_list_length(client):
    """total field should match the actual length of notifications list."""
    org = await create_org(client)
    await create_system(client, org["id"])  # missing classification + owner

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["items"]), (
        f"total={body['total']} but len(notifications)={len(body['notifications'])}"
    )


# ---------------------------------------------------------------------------
# Expiring contracts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_expiring_contract_within_90_days(client):
    """Contract expiring within 90 days generates expiring_contract notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=30)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "expiring_contract" in types, "Should generate expiring_contract notification"


@pytest.mark.asyncio
async def test_notification_expiring_contract_critical_within_30_days(client):
    """Contract expiring within 30 days should have severity=critical."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=15)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert any(n["severity"] == "critical" for n in expiring), (
        "Contract < 30 days should be critical severity"
    )


@pytest.mark.asyncio
async def test_notification_expiring_contract_warning_31_to_90_days(client):
    """Contract expiring between 31-90 days should have severity=warning."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=60)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert any(n["severity"] == "warning" for n in expiring), (
        "Contract 31-90 days should be warning severity"
    )


@pytest.mark.asyncio
async def test_notification_no_expiring_contract_beyond_90_days(client):
    """Contract expiring > 90 days away should NOT generate notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=120)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert len(expiring) == 0, "Contract > 90 days away should not trigger notification"


@pytest.mark.asyncio
async def test_notification_no_expiring_for_past_contract(client):
    """Already expired contracts should NOT generate expiring_contract notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expired = (date.today() - timedelta(days=5)).isoformat()
    await create_contract(client, sys["id"], contract_end=expired)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert len(expiring) == 0, "Past contracts should not generate expiring_contract"


@pytest.mark.asyncio
async def test_notification_expiring_contract_includes_system_id(client):
    """expiring_contract notification should include system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    expiry = (date.today() + timedelta(days=10)).isoformat()
    await create_contract(client, sys["id"], contract_end=expiry)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    expiring = [n for n in resp.json()["items"] if n["type"] == "expiring_contract"]
    assert len(expiring) > 0
    assert "system_id" in expiring[0], "expiring_contract notification must include system_id"
    assert expiring[0]["system_id"] == sys["id"]


# ---------------------------------------------------------------------------
# Missing classification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_missing_classification(client):
    """System without classification generates missing_classification notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_classification" in types


@pytest.mark.asyncio
async def test_notification_no_missing_classification_when_classified(client):
    """System with classification should NOT generate missing_classification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_classification(client, sys["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"]
               if n["type"] == "missing_classification" and n["system_id"] == sys["id"]]
    assert len(missing) == 0, "Classified system should not appear in missing_classification"


@pytest.mark.asyncio
async def test_notification_missing_classification_has_system_id(client):
    """missing_classification notification must include system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"]
               if n["type"] == "missing_classification"]
    assert len(missing) > 0
    assert all("system_id" in n for n in missing)


# ---------------------------------------------------------------------------
# Missing owner
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_missing_owner(client):
    """System without owner generates missing_owner notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_owner" in types


@pytest.mark.asyncio
async def test_notification_no_missing_owner_when_owner_exists(client):
    """System with owner should NOT generate missing_owner notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])
    await create_owner(client, sys["id"], org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"]
               if n["type"] == "missing_owner" and n["system_id"] == sys["id"]]
    assert len(missing) == 0, "System with owner should not trigger missing_owner"


@pytest.mark.asyncio
async def test_notification_missing_owner_has_system_id(client):
    """missing_owner notification should include system_id."""
    org = await create_org(client)
    sys = await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"] if n["type"] == "missing_owner"]
    assert len(missing) > 0
    assert all("system_id" in n for n in missing)


# ---------------------------------------------------------------------------
# Missing GDPR treatment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_missing_gdpr_treatment(client):
    """System with treats_personal_data=True but no GDPR treatment triggers notification."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    types = [n["type"] for n in resp.json()["items"]]
    assert "missing_gdpr_treatment" in types


@pytest.mark.asyncio
async def test_notification_no_missing_gdpr_when_treatment_exists(client):
    """System with GDPR treatment should NOT trigger missing_gdpr_treatment."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], treats_personal_data=True)
    await create_gdpr_treatment(client, sys["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    missing = [n for n in resp.json()["items"]
               if n["type"] == "missing_gdpr_treatment" and n["system_id"] == sys["id"]]
    assert len(missing) == 0


@pytest.mark.asyncio
async def test_notification_missing_gdpr_severity_is_critical(client):
    """missing_gdpr_treatment notification should have severity=critical."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    gdpr_notifs = [n for n in resp.json()["items"]
                   if n["type"] == "missing_gdpr_treatment"]
    assert len(gdpr_notifs) > 0
    assert all(n["severity"] == "critical" for n in gdpr_notifs), (
        "Missing GDPR treatment should always be critical"
    )


# ---------------------------------------------------------------------------
# Notification severity distribution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_by_severity_counts_match(client):
    """by_severity counts should match actual notification counts."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    by_severity = body["by_severity"]
    notifications = body["items"]

    # Re-count from the list
    computed: dict = {}
    for n in notifications:
        sev = n["severity"]
        computed[sev] = computed.get(sev, 0) + 1

    assert by_severity == computed, (
        f"by_severity {by_severity} does not match computed {computed}"
    )


# ---------------------------------------------------------------------------
# Notification field content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notification_entries_have_type_severity_title(client):
    """All notifications must have type, severity, title fields."""
    org = await create_org(client)
    await create_system(client, org["id"])

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    for n in resp.json()["items"]:
        assert "type" in n, "Notification missing 'type'"
        assert "severity" in n, "Notification missing 'severity'"
        assert "title" in n, "Notification missing 'title'"


@pytest.mark.asyncio
async def test_notification_severity_values_are_valid(client):
    """All notification severities should be one of: info, warning, critical."""
    org = await create_org(client)
    await create_system(client, org["id"], treats_personal_data=True)

    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    valid_severities = {"info", "warning", "critical"}
    for n in resp.json()["items"]:
        assert n["severity"] in valid_severities, (
            f"Invalid severity: {n['severity']}"
        )


# ---------------------------------------------------------------------------
# Regression: no pagination (known bug)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notifications_has_pagination(client):
    """Notifications endpoint stöder pagination med limit/offset."""
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    body = resp.json()
    assert "limit" in body, "Pagination: limit saknas i respons"
    assert "offset" in body, "Pagination: offset saknas i respons"
    assert "items" in body, "Pagination: items saknas i respons"
    assert "total" in body, "Pagination: total saknas i respons"
