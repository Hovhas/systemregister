from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_system_or_404
from app.core.rls import get_rls_db
from app.models import Contract
from app.schemas import ContractCreate, ContractUpdate, ContractResponse

router = APIRouter(tags=["Contracts"])


@router.post(
    "/systems/{system_id}/contracts",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
# Org-context from X-Organization-Id header (or JWT when OIDC_ENABLED=true).
async def create_contract(
    system_id: UUID,
    data: ContractCreate,
    db: AsyncSession = Depends(get_rls_db),
):
    """Create a contract linked to a system."""
    await get_system_or_404(system_id, db)

    payload = data.model_dump()
    payload["system_id"] = system_id

    contract = Contract(**payload)
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


@router.get(
    "/systems/{system_id}/contracts",
    response_model=list[ContractResponse],
)
async def list_contracts(
    system_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """List all contracts for a system."""
    await get_system_or_404(system_id, db)

    stmt = (
        select(Contract)
        .where(Contract.system_id == system_id)
        .order_by(Contract.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/systems/{system_id}/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    system_id: UUID,
    contract_id: UUID,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_rls_db),
):
    """Update a contract."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.system_id != system_id:
        raise HTTPException(status_code=404, detail="Contract not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contract, key, value)

    await db.flush()
    await db.refresh(contract)
    return contract


@router.delete("/systems/{system_id}/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    system_id: UUID,
    contract_id: UUID,
    db: AsyncSession = Depends(get_rls_db),
):
    """Delete a contract."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.system_id != system_id:
        raise HTTPException(status_code=404, detail="Contract not found")
    await db.delete(contract)
    await db.flush()


@router.get("/contracts/expiring", response_model=list[ContractResponse])
async def list_expiring_contracts(
    days: int = Query(default=90, ge=1, le=3650, description="Contracts expiring within N days"),
    db: AsyncSession = Depends(get_rls_db),
):
    """List contracts expiring within N days (default: 90)."""
    cutoff = date.today() + timedelta(days=days)

    stmt = (
        select(Contract)
        .where(Contract.contract_end.is_not(None))
        .where(Contract.contract_end <= cutoff)
        .where(Contract.contract_end >= date.today())
        .order_by(Contract.contract_end)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
