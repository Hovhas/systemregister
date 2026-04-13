"""
Health check endpoint för Docker/Kubernetes healthcheck och load balancers.

OBS: Exponeras i root (inte under /api/v1) — ska vara lätt nåbar för
infrastruktur-verktyg utan API-prefix.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Liveness + readiness check."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": "error", "detail": str(e)[:200]}
