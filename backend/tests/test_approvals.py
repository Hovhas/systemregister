"""
Tests for /api/v1/approvals/ endpoints.
"""

import pytest

from tests.factories import create_org, create_approval


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_create_approval(client):
    """POST /api/v1/approvals/ creates with default status=väntande."""
    org = await create_org(client)

    payload = {
        "organization_id": org["id"],
        "approval_type": "systemregistrering",
        "title": "Nytt system begärt",
        "description": "Vi vill registrera Procapita",
        "requested_by": "anna.andersson@kommun.se",
    }
    resp = await client.post("/api/v1/approvals/", json=payload)

    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    body = resp.json()
    assert body["title"] == "Nytt system begärt"
    assert body["organization_id"] == org["id"]
    assert body["status"] == "väntande"
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_get_approval(client):
    """GET /api/v1/approvals/{id} returns correct data."""
    org = await create_org(client)
    approval = await create_approval(client, org["id"], title="Testärende GET")

    resp = await client.get(f"/api/v1/approvals/{approval['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == approval["id"]
    assert body["title"] == "Testärende GET"
    assert body["status"] == "väntande"


@pytest.mark.asyncio
async def test_list_approvals(client):
    """GET /api/v1/approvals/ returns paginated list."""
    org = await create_org(client)
    await create_approval(client, org["id"], title="Ärende 1")
    await create_approval(client, org["id"], title="Ärende 2")

    resp = await client.get("/api/v1/approvals/")

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


@pytest.mark.asyncio
async def test_list_filter_by_status(client):
    """GET /api/v1/approvals/?status=väntande filters correctly."""
    org = await create_org(client)
    await create_approval(client, org["id"], title="Väntande ärende")

    resp = await client.get(
        "/api/v1/approvals/", params={"status": "väntande"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["status"] == "väntande"


@pytest.mark.asyncio
async def test_pending_count(client):
    """GET /api/v1/approvals/pending/count returns {"pending": N}."""
    org = await create_org(client)
    await create_approval(client, org["id"], title="Pending 1")
    await create_approval(client, org["id"], title="Pending 2")

    resp = await client.get("/api/v1/approvals/pending/count")

    assert resp.status_code == 200
    body = resp.json()
    assert "pending" in body
    assert body["pending"] >= 2


@pytest.mark.asyncio
async def test_approve(client):
    """POST /api/v1/approvals/{id}/review with status=godkänd approves."""
    org = await create_org(client)
    approval = await create_approval(client, org["id"])

    resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/review",
        json={
            "status": "godkänd",
            "reviewed_by": "chef@kommun.se",
            "review_comment": "Ser bra ut",
        },
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["status"] == "godkänd"
    assert body["reviewed_by"] == "chef@kommun.se"
    assert body["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_reject(client):
    """POST /api/v1/approvals/{id}/review with status=avvisad rejects."""
    org = await create_org(client)
    approval = await create_approval(client, org["id"])

    resp = await client.post(
        f"/api/v1/approvals/{approval['id']}/review",
        json={
            "status": "avvisad",
            "reviewed_by": "chef@kommun.se",
            "review_comment": "Behöver mer info",
        },
    )

    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    body = resp.json()
    assert body["status"] == "avvisad"
    assert body["reviewed_by"] == "chef@kommun.se"


@pytest.mark.asyncio
async def test_double_review_blocked(client):
    """Reviewing an already-reviewed approval returns 409."""
    org = await create_org(client)
    approval = await create_approval(client, org["id"])

    # First review — approve
    first = await client.post(
        f"/api/v1/approvals/{approval['id']}/review",
        json={"status": "godkänd", "reviewed_by": "chef@kommun.se"},
    )
    assert first.status_code == 200

    # Second review — should be blocked
    second = await client.post(
        f"/api/v1/approvals/{approval['id']}/review",
        json={"status": "avvisad", "reviewed_by": "annan@kommun.se"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_delete_approval(client):
    """DELETE /api/v1/approvals/{id} returns 204."""
    org = await create_org(client)
    approval = await create_approval(client, org["id"])

    resp = await client.delete(f"/api/v1/approvals/{approval['id']}")
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/approvals/{approval['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_approval_not_found(client):
    """GET /api/v1/approvals/{nonexistent} returns 404."""
    resp = await client.get(f"/api/v1/approvals/{FAKE_UUID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_nonexistent(client):
    """POST /api/v1/approvals/{nonexistent}/review returns 404."""
    resp = await client.post(
        f"/api/v1/approvals/{FAKE_UUID}/review",
        json={"status": "godkänd", "reviewed_by": "chef@kommun.se"},
    )
    assert resp.status_code == 404
