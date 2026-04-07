from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rls import get_rls_db
from app.models import InformationAsset, System, information_asset_system_link
from app.schemas import (
    InformationAssetCreate, InformationAssetUpdate, InformationAssetResponse,
    InformationAssetLinkRequest, PaginatedResponse,
)

router = APIRouter(prefix="/information-assets", tags=["Informationsmängd"])


@router.get("/", response_model=PaginatedResponse[InformationAssetResponse])
async def list_information_assets(
    organization_id: UUID | None = Query(None),
    contains_personal_data: bool | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    stmt = select(InformationAsset)
    if organization_id:
        stmt = stmt.where(InformationAsset.organization_id == organization_id)
    if contains_personal_data is not None:
        stmt = stmt.where(InformationAsset.contains_personal_data == contains_personal_data)
    if q:
        stmt = stmt.where(InformationAsset.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(InformationAsset.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(items=result.scalars().all(), total=total, limit=limit, offset=offset)


@router.get("/{asset_id}", response_model=InformationAssetResponse)
async def get_information_asset(asset_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    asset = await db.get(InformationAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Informationsmängd hittades inte")
    return asset


@router.post("/", response_model=InformationAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_information_asset(data: InformationAssetCreate, db: AsyncSession = Depends(get_rls_db)):
    asset = InformationAsset(**data.model_dump())
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=InformationAssetResponse)
async def update_information_asset(asset_id: UUID, data: InformationAssetUpdate, db: AsyncSession = Depends(get_rls_db)):
    asset = await db.get(InformationAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Informationsmängd hittades inte")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_information_asset(asset_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    asset = await db.get(InformationAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Informationsmängd hittades inte")
    await db.delete(asset)
    await db.flush()


# --- System-koppling (N:M) ---

@router.post("/{asset_id}/systems", status_code=status.HTTP_201_CREATED)
async def link_asset_to_system(asset_id: UUID, data: InformationAssetLinkRequest, db: AsyncSession = Depends(get_rls_db)):
    asset = await db.get(InformationAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Informationsmängd hittades inte")
    system = await db.get(System, data.system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System hittades inte")
    await db.execute(
        information_asset_system_link.insert().values(information_asset_id=asset_id, system_id=data.system_id)
    )
    await db.flush()
    return {"detail": "Informationsmängd kopplad till system"}


@router.delete("/{asset_id}/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_asset_from_system(asset_id: UUID, system_id: UUID, db: AsyncSession = Depends(get_rls_db)):
    result = await db.execute(
        information_asset_system_link.delete().where(
            information_asset_system_link.c.information_asset_id == asset_id,
            information_asset_system_link.c.system_id == system_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Koppling hittades inte")
    await db.flush()
