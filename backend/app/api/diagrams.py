"""API för Mermaid-diagramgenerering (Paket B)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.services.diagram_service import (
    build_capability_map, build_context_diagram, build_process_flow,
    build_system_landscape, build_value_stream_diagram,
)

router = APIRouter(prefix="/diagrams", tags=["Diagram"])


@router.get("/context/{system_id}.mmd", response_class=PlainTextResponse)
async def system_context(
    system_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    try:
        text = await build_context_diagram(system_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.get("/capability-map.mmd", response_class=PlainTextResponse)
async def capability_map(
    organization_id: UUID = Query(..., description="Organisation att rita karta för"),
    max_systems_per_capability: int = Query(5, ge=0, le=50),
    db: AsyncSession = Depends(get_rls_db),
):
    text = await build_capability_map(
        organization_id, db,
        max_systems_per_capability=max_systems_per_capability,
    )
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.get("/process-flow/{process_id}.mmd", response_class=PlainTextResponse)
async def process_flow(
    process_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    try:
        text = await build_process_flow(process_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.get("/value-stream/{value_stream_id}.mmd", response_class=PlainTextResponse)
async def value_stream_diagram(
    value_stream_id: UUID, db: AsyncSession = Depends(get_rls_db),
):
    try:
        text = await build_value_stream_diagram(value_stream_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.get("/system-landscape.mmd", response_class=PlainTextResponse)
async def system_landscape(
    organization_id: UUID = Query(..., description="Organisation att rita landskap för"),
    db: AsyncSession = Depends(get_rls_db),
):
    text = await build_system_landscape(organization_id, db)
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")
