from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import System


async def get_system_or_404(system_id: UUID, db: AsyncSession) -> System:
    """Hämta system eller kasta 404 om det inte finns."""
    system = await db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system
