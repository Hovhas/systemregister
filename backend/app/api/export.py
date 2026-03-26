import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import System

router = APIRouter(prefix="/export", tags=["Export"])

EXPORT_COLUMNS = [
    "name",
    "description",
    "system_category",
    "criticality",
    "lifecycle_status",
    "business_area",
    "hosting_model",
    "cloud_provider",
    "nis2_applicable",
    "treats_personal_data",
    "product_name",
    "product_version",
    "deployment_date",
]


async def _fetch_systems(
    db: AsyncSession, organization_id: UUID | None
) -> list[System]:
    stmt = select(System).order_by(System.name)
    if organization_id:
        stmt = stmt.where(System.organization_id == organization_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _row_values(system: System) -> list:
    values = []
    for col in EXPORT_COLUMNS:
        val = getattr(system, col)
        # Enum → value-sträng
        if hasattr(val, "value"):
            val = val.value
        values.append(val)
    return values


@router.get("/systems.xlsx")
async def export_systems_xlsx(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Exportera system som Excel-fil (.xlsx)."""
    from openpyxl import Workbook

    systems = await _fetch_systems(db, organization_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "System"
    ws.append(EXPORT_COLUMNS)

    for system in systems:
        row = _row_values(system)
        # date → ISO-sträng för Excel-kompatibilitet
        row = [str(v) if hasattr(v, "isoformat") else v for v in row]
        ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = "systems.xlsx"
    if organization_id:
        filename = f"systems_{organization_id}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/systems.csv")
async def export_systems_csv(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Exportera system som CSV-fil."""
    systems = await _fetch_systems(db, organization_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_COLUMNS)

    for system in systems:
        row = _row_values(system)
        writer.writerow(row)

    output.seek(0)

    filename = "systems.csv"
    if organization_id:
        filename = f"systems_{organization_id}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/systems.json")
async def export_systems_json(
    organization_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Exportera system som JSON-array."""
    systems = await _fetch_systems(db, organization_id)

    rows = []
    for system in systems:
        row = {}
        for col in EXPORT_COLUMNS:
            val = getattr(system, col)
            if hasattr(val, "value"):
                val = val.value
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            row[col] = val
        rows.append(row)

    content = json.dumps(rows, ensure_ascii=False, indent=2)

    filename = "systems.json"
    if organization_id:
        filename = f"systems_{organization_id}.json"

    return StreamingResponse(
        iter([content]),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
