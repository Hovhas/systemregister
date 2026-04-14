"""CycloneDX SBOM export (FK-13)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import System, Module, module_system_link

router = APIRouter(prefix="/export", tags=["SBOM"])


@router.get("/sbom/{system_id}.cdx.json")
async def export_system_sbom(
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Export CycloneDX 1.5 SBOM for a system and its linked modules."""
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")

    # Fetch linked modules
    stmt = select(Module).join(
        module_system_link,
        Module.id == module_system_link.c.module_id,
    ).where(module_system_link.c.system_id == system_id)
    result = await db.execute(stmt)
    modules = result.scalars().all()

    # Build CycloneDX 1.5 BOM
    metadata_component = {
        "type": "application",
        "name": system.name,
        "version": system.product_version or "unknown",
    }
    if system.cpe:
        metadata_component["cpe"] = system.cpe
    if system.purl:
        metadata_component["purl"] = system.purl
    if system.license_id:
        metadata_component["licenses"] = [{"license": {"id": system.license_id}}]

    components = []
    for m in modules:
        comp = {
            "type": "library",
            "name": m.name,
            "version": m.product_version or "unknown",
        }
        if m.license_id:
            comp["licenses"] = [{"license": {"id": m.license_id}}]
        if m.cpe:
            comp["cpe"] = m.cpe
        if m.purl:
            comp["purl"] = m.purl
        if m.supplier:
            comp["supplier"] = {"name": m.supplier}
        components.append(comp)

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": metadata_component,
        },
        "components": components,
    }

    return JSONResponse(content=bom, media_type="application/json")
