"""ArchiMate Open Exchange-export (Paket B.2)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.services.archimate_service import build_archimate_xml

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/archimate.xml")
async def export_archimate(
    organization_id: UUID = Query(..., description="Organisation att exportera"),
    db: AsyncSession = Depends(get_rls_db),
):
    xml = await build_archimate_xml(organization_id, db)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f"attachment; filename=archimate-{organization_id}.xml"
            )
        },
    )
