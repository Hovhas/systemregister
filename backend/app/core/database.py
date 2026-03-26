from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=20,
    max_overflow=10,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """
    Bas-dependency: returnerar en db-session utan RLS-context.

    Används av:
      - Interna tjänster och tester som inte behöver org-isolering
      - get_rls_db (app/core/rls.py) som sedan sätter RLS-context
      - get_superadmin_db för DigIT-adminvyer

    För org-isolerade endpoints: använd Depends(get_rls_db) istället.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
