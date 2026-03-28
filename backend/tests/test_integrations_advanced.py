"""
Avancerade integrationstester — Kategori 6.

Testar beroenden, grafer, filtrering, cross-org-integrations,
felhantering vid kaskad-borttagning och sällsynta kombinationer.
"""

import pytest

from tests.factories import (
    create_org,
    create_system,
    create_integration,
)


# ---------------------------------------------------------------------------
# Grundläggande integrationstyper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", [
    "api", "filöverföring", "databasreplikering", "event", "manuell"
])
async def test_create_integration_all_types(client, itype):
    """Alla integrationstyper kan skapas."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"Src {itype}")
    tgt = await create_system(client, org["id"], name=f"Tgt {itype}")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": itype,
    })
    assert resp.status_code == 201
    assert resp.json()["integration_type"] == itype


@pytest.mark.asyncio
async def test_create_integration_with_all_fields(client):
    """Integration med alla fält sparas korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Källa Fullständig")
    tgt = await create_system(client, org["id"], name="Mål Fullständig")

    payload = {
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "api",
        "data_types": "personuppgifter, adresser",
        "frequency": "realtid",
        "description": "REST API-integration för personuppgiftsöverföring",
        "criticality": "hög",
        "is_external": False,
    }
    resp = await client.post("/api/v1/integrations/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["data_types"] == "personuppgifter, adresser"
    assert body["frequency"] == "realtid"
    assert body["criticality"] == "hög"
    assert body["is_external"] is False


@pytest.mark.asyncio
async def test_create_external_integration(client):
    """Extern integration (is_external=True) med external_party sparas korrekt."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="Intern Källa")
    tgt = await create_system(client, org["id"], name="Externt Mål")

    payload = {
        "source_system_id": src["id"],
        "target_system_id": tgt["id"],
        "integration_type": "filöverföring",
        "is_external": True,
        "external_party": "Skatteverket",
    }
    resp = await client.post("/api/v1/integrations/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_external"] is True
    assert body["external_party"] == "Skatteverket"


@pytest.mark.asyncio
async def test_integration_criticality_all_levels(client):
    """Integration kan ha alla kritikalitetsnivåer."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="CritSrc")
    tgt = await create_system(client, org["id"], name="CritTgt")

    for crit in ["låg", "medel", "hög", "kritisk"]:
        integ = await create_integration(client, src["id"], tgt["id"], criticality=crit)
        assert integ["criticality"] == crit


# ---------------------------------------------------------------------------
# Beroendegraf: intransitiva och cirkulära beroenden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_chain_a_b_c(client):
    """A→B→C: System B är beroende av A och C är beroende av B."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="ChainA")
    sys_b = await create_system(client, org["id"], name="ChainB")
    sys_c = await create_system(client, org["id"], name="ChainC")

    integ_ab = await create_integration(client, sys_a["id"], sys_b["id"])
    integ_bc = await create_integration(client, sys_b["id"], sys_c["id"])

    # B:s integrationer: 1 in + 1 out = 2
    resp = await client.get(f"/api/v1/systems/{sys_b['id']}/integrations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_integration_self_loop_rejected(client):
    """Integrering med sig själv som källa och mål bör avvisas."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="LoopSys")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys["id"],
        "target_system_id": sys["id"],
        "integration_type": "api",
    })
    # Beroende på implementation: 400, 422 eller 409
    # Acceptabelt: det skall INTE vara 201
    assert resp.status_code != 201, (
        f"Integration med sig själv borde inte accepteras, fick {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_multiple_integrations_same_pair(client):
    """Flera integrationer mellan samma par (olika typ) skall tillåtas."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="MultiSrc")
    tgt = await create_system(client, org["id"], name="MultiTgt")

    # Två integrationer: api + filöverföring
    integ1 = await create_integration(client, src["id"], tgt["id"],
                                       integration_type="api")
    integ2 = await create_integration(client, src["id"], tgt["id"],
                                       integration_type="filöverföring")

    assert integ1["id"] != integ2["id"]

    resp = await client.get(f"/api/v1/systems/{src['id']}/integrations")
    ids = [i["id"] for i in resp.json()]
    assert integ1["id"] in ids
    assert integ2["id"] in ids


@pytest.mark.asyncio
async def test_integration_hub_many_sources(client):
    """Hub-mönster: många system pekar mot en central hub."""
    org = await create_org(client)
    hub = await create_system(client, org["id"], name="IntegrationsHub")

    sources = []
    for i in range(5):
        src = await create_system(client, org["id"], name=f"Spoke{i}")
        sources.append(src)
        await create_integration(client, src["id"], hub["id"])

    resp = await client.get(f"/api/v1/systems/{hub['id']}/integrations")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


# ---------------------------------------------------------------------------
# Cross-org integrationer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_cross_org_allowed(client):
    """Integration kan skapas mellan system i olika organisationer."""
    org_a = await create_org(client, name="CrossOrgA", org_type="kommun")
    org_b = await create_org(client, name="CrossOrgB", org_type="bolag")

    sys_a = await create_system(client, org_a["id"], name="CrossSrcA")
    sys_b = await create_system(client, org_b["id"], name="CrossTgtB")

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": sys_a["id"],
        "target_system_id": sys_b["id"],
        "integration_type": "api",
        "is_external": True,
        "external_party": "Bolag B",
    })
    # Cross-org integration bör tillåtas (det är ett vanligt scenario)
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_system_id"] == sys_a["id"]
    assert body["target_system_id"] == sys_b["id"]


@pytest.mark.asyncio
async def test_integration_nonexistent_target_returns_404(client):
    """POST med okänd target_system_id ger 404."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="SrcExist")
    fake = "00000000-0000-0000-0000-000000000000"

    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": src["id"],
        "target_system_id": fake,
        "integration_type": "api",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_integration_both_nonexistent_returns_error(client):
    """POST med okänd source och target ger fel."""
    fake = "00000000-0000-0000-0000-000000000000"
    resp = await client.post("/api/v1/integrations/", json={
        "source_system_id": fake,
        "target_system_id": fake,
        "integration_type": "api",
    })
    assert resp.status_code in (404, 422), (
        f"Okänd source och target borde ge 404/422, fick {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Filtrering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", ["api", "filöverföring", "databasreplikering", "event", "manuell"])
async def test_filter_integrations_all_types(client, itype):
    """Filtrering på integration_type fungerar för alla typer."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name=f"FiltSrc {itype}")
    tgt = await create_system(client, org["id"], name=f"FiltTgt {itype}")

    created = await create_integration(client, src["id"], tgt["id"], integration_type=itype)

    resp = await client.get("/api/v1/integrations/", params={"integration_type": itype})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert created["id"] in ids
    for item in resp.json():
        assert item["integration_type"] == itype


@pytest.mark.asyncio
async def test_filter_integrations_by_system_as_source(client):
    """Filtrering via system_id returnerar integrations där systemet är källa."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="FilterSrcA")
    sys_b = await create_system(client, org["id"], name="FilterTgtB")
    sys_c = await create_system(client, org["id"], name="FilterUnrelC")

    integ_ab = await create_integration(client, sys_a["id"], sys_b["id"])

    resp = await client.get("/api/v1/integrations/", params={"system_id": sys_a["id"]})
    ids = [i["id"] for i in resp.json()]
    assert integ_ab["id"] in ids


@pytest.mark.asyncio
async def test_filter_integrations_empty_result(client):
    """Filtrering som inte matchar returnerar tom lista."""
    resp = await client.get("/api/v1/integrations/", params={"system_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Kaskad-borttagning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_source_system_removes_integrations(client):
    """Ta bort source system tar kaskad-bort integrationer."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="CascadeDeleteSrc")
    tgt = await create_system(client, org["id"], name="CascadeDeleteTgt")

    integ = await create_integration(client, src["id"], tgt["id"])

    # Ta bort källsystem
    del_resp = await client.delete(f"/api/v1/systems/{src['id']}")
    assert del_resp.status_code == 204

    # Integreringen skall vara borta
    get_resp = await client.get(f"/api/v1/integrations/{integ['id']}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_target_system_removes_integrations(client):
    """Ta bort target system tar kaskad-bort integrationer."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="CascSrc2")
    tgt = await create_system(client, org["id"], name="CascTgt2")

    integ = await create_integration(client, src["id"], tgt["id"])

    del_resp = await client.delete(f"/api/v1/systems/{tgt['id']}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/integrations/{integ['id']}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Patch / update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_integration_update_criticality(client):
    """PATCH integration kan uppdatera criticality."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="PatchSrc")
    tgt = await create_system(client, org["id"], name="PatchTgt")
    integ = await create_integration(client, src["id"], tgt["id"])

    resp = await client.patch(f"/api/v1/integrations/{integ['id']}", json={
        "criticality": "kritisk",
    })
    assert resp.status_code == 200
    assert resp.json()["criticality"] == "kritisk"


@pytest.mark.asyncio
async def test_patch_integration_make_external(client):
    """PATCH kan konvertera en intern integration till extern."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="ExtPatchSrc")
    tgt = await create_system(client, org["id"], name="ExtPatchTgt")
    integ = await create_integration(client, src["id"], tgt["id"], is_external=False)

    resp = await client.patch(f"/api/v1/integrations/{integ['id']}", json={
        "is_external": True,
        "external_party": "Tredje Part AB",
    })
    assert resp.status_code == 200
    assert resp.json()["is_external"] is True
    assert resp.json()["external_party"] == "Tredje Part AB"


@pytest.mark.asyncio
async def test_patch_integration_invalid_type_returns_422(client):
    """PATCH med ogiltig integration_type ger 422."""
    org = await create_org(client)
    src = await create_system(client, org["id"], name="InvalidPatchSrc")
    tgt = await create_system(client, org["id"], name="InvalidPatchTgt")
    integ = await create_integration(client, src["id"], tgt["id"])

    resp = await client.patch(f"/api/v1/integrations/{integ['id']}", json={
        "integration_type": "ogiltig_typ",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# System integrations endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_integrations_empty(client):
    """GET /systems/{id}/integrations på system utan integrationer returnerar tom lista."""
    org = await create_org(client)
    sys = await create_system(client, org["id"], name="IsolatedSys")

    resp = await client.get(f"/api/v1/systems/{sys['id']}/integrations")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_system_integrations_bidirectional_counted(client):
    """GET /systems/{id}/integrations returnerar BÅDE utgående och inkommande."""
    org = await create_org(client)
    hub = await create_system(client, org["id"], name="BidirHub")
    spoke_a = await create_system(client, org["id"], name="BidirSpokeA")
    spoke_b = await create_system(client, org["id"], name="BidirSpokeB")

    # Hub är källa för A och mål för B
    await create_integration(client, hub["id"], spoke_a["id"])
    await create_integration(client, spoke_b["id"], hub["id"])

    resp = await client.get(f"/api/v1/systems/{hub['id']}/integrations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_integrations_list_all(client):
    """GET /integrations/ utan filter returnerar alla integrationer."""
    org = await create_org(client)
    sys_a = await create_system(client, org["id"], name="AllListA")
    sys_b = await create_system(client, org["id"], name="AllListB")
    sys_c = await create_system(client, org["id"], name="AllListC")

    i1 = await create_integration(client, sys_a["id"], sys_b["id"])
    i2 = await create_integration(client, sys_b["id"], sys_c["id"])
    i3 = await create_integration(client, sys_c["id"], sys_a["id"])

    resp = await client.get("/api/v1/integrations/")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert i1["id"] in ids
    assert i2["id"] in ids
    assert i3["id"] in ids


@pytest.mark.asyncio
async def test_integration_missing_required_fields_returns_422(client):
    """POST integration utan source_system_id ger 422."""
    org = await create_org(client)
    tgt = await create_system(client, org["id"], name="NoSrcTgt")

    resp = await client.post("/api/v1/integrations/", json={
        "target_system_id": tgt["id"],
        "integration_type": "api",
    })
    assert resp.status_code == 422
