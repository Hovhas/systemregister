"""2C8-export-endpoints (Paket B.3).

Modulnamn: `twoseight_export.py` — moduler får inte börja med siffra.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.services.twoseight_service import (
    build_full_package_zip, build_objects_xlsx, build_relationships_xlsx,
)

router = APIRouter(prefix="/export/2c8", tags=["Export"])


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/objects.xlsx")
async def objects_xlsx(
    organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_rls_db),
):
    payload = await build_objects_xlsx(organization_id, db)
    return Response(
        content=payload,
        media_type=_XLSX,
        headers={
            "Content-Disposition": (
                f"attachment; filename=2c8-objects-{organization_id}.xlsx"
            )
        },
    )


@router.get("/relationships.xlsx")
async def relationships_xlsx(
    organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_rls_db),
):
    payload = await build_relationships_xlsx(organization_id, db)
    return Response(
        content=payload,
        media_type=_XLSX,
        headers={
            "Content-Disposition": (
                f"attachment; filename=2c8-relationships-{organization_id}.xlsx"
            )
        },
    )


@router.get("/full-package.zip")
async def full_package_zip(
    organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_rls_db),
):
    payload = await build_full_package_zip(organization_id, db)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=2c8-package-{organization_id}.zip"
            )
        },
    )
