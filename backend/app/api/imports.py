import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import System
from app.schemas import SystemCreate

router = APIRouter(prefix="/import", tags=["Import"])

SUPPORTED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/csv",
    "application/json",
    "text/plain",  # Vissa klienter skickar CSV som text/plain
}


def _detect_format(filename: str, content_type: str | None) -> str:
    """Detektera filformat utifrån filnamn och content-type."""
    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return "excel"
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".json"):
        return "json"
    # Fallback på content-type
    ct = (content_type or "").lower()
    if "spreadsheet" in ct or "excel" in ct:
        return "excel"
    if "csv" in ct:
        return "csv"
    if "json" in ct:
        return "json"
    raise HTTPException(
        status_code=415,
        detail="Filformat stöds ej. Använd .xlsx, .csv eller .json.",
    )


def _rows_from_excel(content: bytes) -> list[dict]:
    from openpyxl import load_workbook

    wb = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    result = []
    for row in rows[1:]:
        result.append(dict(zip(headers, row)))
    return result


def _rows_from_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # Hanterar BOM
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _rows_from_json(content: bytes) -> list[dict]:
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, list):
        raise HTTPException(
            status_code=422, detail="JSON måste vara en array av objekt."
        )
    return data


def _coerce_row(row: dict, organization_id: UUID) -> dict:
    """Normalisera radvärden och injicera organization_id."""
    result = {}
    for key, val in row.items():
        # Tomma strängar → None
        if val == "" or val is None:
            result[key] = None
        else:
            result[key] = val

    result["organization_id"] = organization_id

    # bool-fält: hantera "true"/"false"/"1"/"0" från Excel/CSV
    bool_fields = [
        "nis2_applicable",
        "treats_personal_data",
        "treats_sensitive_data",
        "third_country_transfer",
        "has_elevated_protection",
        "security_protection",
        "dr_plan_exists",
    ]
    for field in bool_fields:
        val = result.get(field)
        if isinstance(val, str):
            result[field] = val.strip().lower() in ("true", "1", "yes", "ja")
        elif val is None:
            result[field] = False

    return result


async def _system_exists(
    db: AsyncSession, name: str, organization_id: UUID
) -> bool:
    stmt = select(System).where(
        System.name == name,
        System.organization_id == organization_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


@router.post("/systems")
async def import_systems(
    organization_id: UUID = Query(..., description="Organisation att importera till"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Importera system från Excel, CSV eller JSON.

    - Skippar rader där name+organization_id redan finns (ingen upsert).
    - Returnerar antal importerade + lista med valideringsfel per rad.
    """
    fmt = _detect_format(file.filename or "", file.content_type)
    content = await file.read()

    if fmt == "excel":
        rows = _rows_from_excel(content)
    elif fmt == "csv":
        rows = _rows_from_csv(content)
    else:
        rows = _rows_from_json(content)

    imported = 0
    errors = []

    for index, raw_row in enumerate(rows, start=2):  # rad 2 = första datarad (1 = rubrik)
        try:
            coerced = _coerce_row(raw_row, organization_id)
            data = SystemCreate.model_validate(coerced)
        except ValidationError as exc:
            errors.append({
                "row": index,
                "error": exc.errors(include_url=False),
            })
            continue
        except Exception as exc:
            errors.append({"row": index, "error": str(exc)})
            continue

        # Skippa om systemet redan finns
        exists = await _system_exists(db, data.name, organization_id)
        if exists:
            errors.append({
                "row": index,
                "error": f"System '{data.name}' finns redan i organisationen (skippad).",
            })
            continue

        system = System(**data.model_dump())
        db.add(system)
        imported += 1

    if imported > 0:
        await db.flush()

    return {"imported": imported, "errors": errors}
