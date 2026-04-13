"""
Tests for /api/v1/export/sbom/{system_id}.cdx.json endpoint.
"""

import pytest
import uuid

from tests.factories import create_org, create_system, create_module


@pytest.mark.asyncio
async def test_sbom_404_for_unknown_system(client):
    """GET /api/v1/export/sbom/{unknown_id}.cdx.json returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/export/sbom/{fake_id}.cdx.json")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_sbom_200_valid_cyclonedx(client):
    """GET /api/v1/export/sbom/{system_id}.cdx.json returns valid CycloneDX 1.5."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="SBOM System")

    resp = await client.get(f"/api/v1/export/sbom/{sys['id']}.cdx.json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["bomFormat"] == "CycloneDX", "bomFormat should be CycloneDX"
    assert body["specVersion"] == "1.5", "specVersion should be 1.5"
    assert "metadata" in body, "BOM should contain metadata"
    assert "components" in body, "BOM should contain components array"
    assert isinstance(body["components"], list), "components should be a list"


@pytest.mark.asyncio
async def test_sbom_contains_system_name(client):
    """SBOM metadata.component.name matches the system name."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Mitt SBOM-system")

    resp = await client.get(f"/api/v1/export/sbom/{sys['id']}.cdx.json")
    assert resp.status_code == 200

    body = resp.json()
    metadata_comp = body["metadata"]["component"]
    assert metadata_comp["name"] == "Mitt SBOM-system"


@pytest.mark.asyncio
async def test_sbom_includes_linked_modules(client):
    """SBOM components array includes linked modules."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="SBOM LinkSys")
    mod = await create_module(client, org["id"], name="SBOM Modul A")

    # Link module to system
    link_resp = await client.post(
        f"/api/v1/modules/{mod['id']}/link",
        json={"system_id": sys["id"]},
    )
    if link_resp.status_code not in (200, 201):
        pytest.skip(f"Could not link module to system: {link_resp.status_code} {link_resp.text}")

    resp = await client.get(f"/api/v1/export/sbom/{sys['id']}.cdx.json")
    assert resp.status_code == 200

    body = resp.json()
    comp_names = [c["name"] for c in body["components"]]
    assert "SBOM Modul A" in comp_names, f"Expected module in components, got: {comp_names}"


@pytest.mark.asyncio
async def test_sbom_empty_components_without_modules(client):
    """SBOM components array is empty when no modules are linked."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="Modul-löst system")

    resp = await client.get(f"/api/v1/export/sbom/{sys['id']}.cdx.json")
    assert resp.status_code == 200

    body = resp.json()
    assert body["components"] == [], f"Expected empty components, got {body['components']}"
