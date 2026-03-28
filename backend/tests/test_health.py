"""
Tests for /health endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """GET /health returns 200."""
    resp = await client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_health_returns_json(client):
    """GET /health returns JSON body."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict), "health endpoint should return a JSON object"


@pytest.mark.asyncio
async def test_health_has_status_field(client):
    """GET /health response contains a status field."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body, "health response must include status field"


@pytest.mark.asyncio
async def test_health_status_is_ok(client):
    """GET /health returns status=ok when service is up."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") in ("ok", "healthy", "up"), (
        f"Expected status to be ok/healthy/up, got: {body.get('status')}"
    )


@pytest.mark.asyncio
async def test_health_content_type_json(client):
    """GET /health sets Content-Type to application/json."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "application/json" in content_type, (
        f"Expected application/json content-type, got: {content_type}"
    )
