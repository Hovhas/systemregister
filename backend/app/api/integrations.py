from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_or_404
from app.core.rls import get_rls_db
from app.models import SystemIntegration
from app.models.enums import IntegrationType
from app.schemas import IntegrationCreate, IntegrationUpdate, IntegrationResponse

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# Secondary router for system-scoped integration endpoints
system_router = APIRouter(tags=["Integrations"])


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
async def create_integration(
    data: IntegrationCreate,
    db: AsyncSession = Depends(get_rls_db),
):
    """Create a new integration between two systems."""
    # Verify both systems exist
    await get_system_or_404(data.source_system_id, db)
    await get_system_or_404(data.target_system_id, db)

    if data.source_system_id == data.target_system_id:
        raise HTTPException(
            status_code=422,
            detail="source_system_id och target_system_id kan inte vara samma system"
        )

    integration = SystemIntegration(**data.model_dump())
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    return integration


@router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    system_id: UUID | None = Query(None, description="Filter by source or target system"),
    integration_type: IntegrationType | None = Query(None),
    db: AsyncSession = Depends(get_rls_db),
):
    """List all integrations, optionally filtered by system or type."""
    stmt = select(SystemIntegration)

    if system_id:
        stmt = stmt.where(
            or_(
                SystemIntegration.source_system_id == system_id,
                SystemIntegration.target_system_id == system_id,
            )
        )
    if integration_type:
        stmt = stmt.where(SystemIntegration.integration_type == integration_type)

    stmt = stmt.order_by(SystemIntegration.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Get a single integration by ID."""
    integration = await db.get(SystemIntegration, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.patch("/{integration_id}", response_model=IntegrationResponse)
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
async def update_integration(
    integration_id: UUID,
    data: IntegrationUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    """Update an integration."""
    integration = await db.get(SystemIntegration, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(integration, key, value)

    await db.flush()
    await db.refresh(integration)
    return integration


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
async def delete_integration(
    integration_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Delete an integration."""
    integration = await db.get(SystemIntegration, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await db.delete(integration)
    await db.flush()


@system_router.get(
    "/systems/{system_id}/integrations",
    response_model=list[IntegrationResponse],
)
async def list_system_integrations(
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """List all integrations for a system (both inbound and outbound)."""
    await get_system_or_404(system_id, db)

    stmt = (
        select(SystemIntegration)
        .where(
            or_(
                SystemIntegration.source_system_id == system_id,
                SystemIntegration.target_system_id == system_id,
            )
        )
        .order_by(SystemIntegration.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
