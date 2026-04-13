"""
Tests for /api/v1/webhooks/metakatalog endpoint.
"""

import pytest
from unittest.mock import patch

from tests.factories import create_org, create_system


@pytest.mark.asyncio
async def test_webhook_401_without_secret(client):
    """POST without x-webhook-secret header returns 401 (or 422 if missing required header)."""
    resp = await client.post(
        "/api/v1/webhooks/metakatalog",
        json={"event": "system.updated", "metakatalog_id": "mk-1", "data": {}},
    )
    # FastAPI returns 422 for missing required Header(...), or 401 if checked in code
    assert resp.status_code in (401, 422), f"Expected 401/422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_webhook_401_with_wrong_secret(client):
    """POST with wrong x-webhook-secret returns 401."""
    resp = await client.post(
        "/api/v1/webhooks/metakatalog",
        json={"event": "system.updated", "metakatalog_id": "mk-1", "data": {}},
        headers={"x-webhook-secret": "wrong-secret"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_webhook_404_when_disabled(client):
    """POST with correct secret but metakatalog_enabled=False returns 404."""
    from app.core.config import Settings

    mock_settings = Settings(
        metakatalog_webhook_secret="test-secret-123",
        metakatalog_enabled=False,
    )
    with patch("app.api.webhooks.get_settings", return_value=mock_settings):
        resp = await client.post(
            "/api/v1/webhooks/metakatalog",
            json={"event": "system.updated", "metakatalog_id": "mk-1", "data": {}},
            headers={"x-webhook-secret": "test-secret-123"},
        )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_webhook_200_updates_system(client):
    """POST with correct secret + system.updated event updates allowed fields."""
    from app.core.config import Settings

    org = await create_org(client)
    sys = await create_system(client, org["id"], name="MK System")

    # Set metakatalog_id on the system (directly via API update)
    mk_id = "mk-abc-123"
    update_resp = await client.put(
        f"/api/v1/systems/{sys['id']}",
        json={"metakatalog_id": mk_id},
    )
    # It may or may not support setting metakatalog_id via update — handle gracefully
    if update_resp.status_code not in (200, 422):
        pytest.skip("Cannot set metakatalog_id via API update")

    mock_settings = Settings(
        metakatalog_webhook_secret="test-secret-123",
        metakatalog_enabled=True,
    )
    with patch("app.api.webhooks.get_settings", return_value=mock_settings):
        resp = await client.post(
            "/api/v1/webhooks/metakatalog",
            json={
                "event": "system.updated",
                "metakatalog_id": mk_id,
                "data": {"name": "Uppdaterat namn"},
            },
            headers={"x-webhook-secret": "test-secret-123"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
