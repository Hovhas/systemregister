"""
Row-Level Security (RLS) context-hantering.

Sätter app.current_org_id per databas-transaktion så att PostgreSQL:s
RLS-policies filtrerar rader baserat på aktuell organisation.

Flöde:
  1. Request anländer med X-Organization-Id-header (eller JWT-claim senare)
  2. get_rls_db dependency hämtar org_id ur headern
  3. set_rls_context() kör SET LOCAL — värdet gäller bara denna transaktion
  4. PostgreSQL-policies appliceras automatiskt på alla queries

Testkörning utan RLS:
  Sätt BYPASS_RLS=true i miljövariabler (development only).
  get_db (utan RLS) fungerar som vanligt för tester som inte sätter context.
"""

import uuid
import logging

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def set_rls_context(db: AsyncSession, org_id: uuid.UUID) -> None:
    """
    Sätter app.current_org_id för aktuell transaktion.

    Använder SET LOCAL vilket nollställs automatiskt när
    transaktionen avslutas — ingen risk för context-läckage
    mellan requests i connection-pool.
    """
    await db.execute(
        text("SELECT set_org_context(:org_id)"),
        {"org_id": str(org_id)},
    )
    logger.debug("RLS context satt: org_id=%s", org_id)


async def clear_rls_context(db: AsyncSession) -> None:
    """
    Nollställer org-context explicit.
    Normalt onödigt (SET LOCAL nollställs vid transaktionslut)
    men användbart vid testning.
    """
    await db.execute(
        text("SELECT set_config('app.current_org_id', '', true)")
    )


async def get_rls_db(
    db: AsyncSession = Depends(get_db),
    x_organization_id: str | None = Header(default=None),
) -> AsyncSession:
    """
    FastAPI Dependency: hämtar db-session med RLS-context satt.

    Placeholder tills JWT-auth är på plats: läser org_id ur
    X-Organization-Id-headern.

    Returnerar sessionen med aktiv RLS-context.

    Användning i router:
        @router.get("/systems")
        async def list_systems(db: AsyncSession = Depends(get_rls_db)):
            ...

    TODO: Byt till JWT-claims när auth är implementerat.
          Se issue #XX — auth-modul.
    """
    if settings.environment != "development" and x_organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-Id-header krävs",
        )

    if x_organization_id is not None:
        try:
            org_id = uuid.UUID(x_organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ogiltigt UUID i X-Organization-Id: {x_organization_id!r}",
            )

        await set_rls_context(db, org_id)

    return db


async def get_superadmin_db(
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """
    FastAPI Dependency: db-session utan RLS-context (superadmin-vy).

    Avsedd för endpoints som DigIT-personal (systemregister_admin-rollen)
    använder för att se data över alla organisationer.

    OBS: Skydda dessa endpoints med auth-middleware som verifierar
         att användaren faktiskt har admin-behörighet.
    """
    return db
