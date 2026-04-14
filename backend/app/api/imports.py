from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import Organization
from app.services.import_service import ImportService

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/systems")
async def import_systems(
    organization_id: UUID = Query(..., description="Organisation att importera till"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_rls_db),
):
    """Importera system från Excel, CSV eller JSON."""
    org = await db.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation {organization_id} finns inte")

    try:
        fmt = ImportService.detect_format(file.filename or "", file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

    content = await file.read()

    try:
        rows = ImportService.parse_rows(content, fmt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    imported, errors = await ImportService.import_systems(db, rows, organization_id)
    return {"imported": imported, "errors": errors}


@router.post("/classifications")
async def import_classifications(
    organization_id: UUID | None = Query(None, description="Begränsa systemuppslagning till organisation"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_rls_db),
):
    """Importera klassificeringar från Excel, CSV eller JSON."""
    try:
        fmt = ImportService.detect_format(file.filename or "", file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

    content = await file.read()

    try:
        rows = ImportService.parse_rows(content, fmt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    imported, errors = await ImportService.import_classifications(db, rows, organization_id)
    return {"imported": imported, "errors": errors}


@router.post("/owners")
async def import_owners(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_rls_db),
):
    """Importera systemägare från Excel, CSV eller JSON."""
    try:
        fmt = ImportService.detect_format(file.filename or "", file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

    content = await file.read()

    try:
        rows = ImportService.parse_rows(content, fmt)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    imported, errors = await ImportService.import_owners(db, rows)
    return {"imported": imported, "errors": errors}
