"""
Test configuration and fixtures.

Uses a real PostgreSQL test database (systemregister_test) since the models
use PostgreSQL-specific types (UUID, JSONB) that are not compatible with SQLite.

Requirements:
    PostgreSQL running on localhost:5432
    Database: systemregister_test
    User: systemregister / devpassword (or set TEST_DATABASE_URL env var)

Setup (one-time):
    psql -U <superuser> -c "CREATE DATABASE systemregister_test;"
    psql -U <superuser> -c "CREATE USER systemregister WITH PASSWORD 'devpassword';"
    psql -U <superuser> -c "GRANT ALL PRIVILEGES ON DATABASE systemregister_test TO systemregister;"
    psql -U <superuser> -d systemregister_test -c "CREATE EXTENSION IF NOT EXISTS uuid-ossp;"
    psql -U <superuser> -d systemregister_test -c "GRANT ALL ON SCHEMA public TO systemregister;"
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastapi import Header
from app.core.database import Base, get_db
from app.core.rls import get_rls_db
from app.core.audit import register_audit_listeners
from app.main import app as fastapi_app
# Import all models so Base.metadata is populated
import app.models.models  # noqa: F401

# Register audit listeners (lifespan may not run in test mode)
register_audit_listeners()

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://systemregister:devpassword@db:5432/systemregister_test",
)


def _derive_sync_url(async_url: str) -> str:
    """Convert asyncpg URL to sync psycopg2 URL for alembic."""
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


def _run_alembic_upgrade(sync_url: str) -> None:
    """Run alembic upgrade head against the given database (synchronous).

    This is the single source of truth for schema + RLS policies —
    no more duplicated SQL between conftest and migration files.
    """
    import os
    from alembic.config import Config
    from alembic import command

    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")


def _run_alembic_downgrade(sync_url: str) -> None:
    """Run alembic downgrade base against the given database (synchronous)."""
    import os
    from alembic.config import Config
    from alembic import command

    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.downgrade(alembic_cfg, "base")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for the test database (session-scoped).

    Uses alembic upgrade head as the single source of truth for schema
    and RLS policies — eliminates drift between conftest and migrations.

    Uses NullPool to prevent connection state (RLS context, SET LOCAL)
    from leaking between tests via pooled connections.
    """
    from sqlalchemy.pool import NullPool

    sync_url = _derive_sync_url(TEST_DATABASE_URL)

    # Run all migrations (schema + RLS + indexes) via alembic
    _run_alembic_upgrade(sync_url)

    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False,
        poolclass=NullPool,
    )

    # Create the non-superuser role for RLS enforcement in tests
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'systemregister_app') THEN
                    CREATE ROLE systemregister_app WITH LOGIN PASSWORD 'devpassword'
                        NOBYPASSRLS NOSUPERUSER;
                END IF;
            END
            $$;
        """))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO systemregister_app"))
        await conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO systemregister_app"))
        await conn.execute(text("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO systemregister_app"))
        await conn.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO systemregister_app"))

    yield engine

    # Teardown: downgrade all migrations (drops tables, policies, functions)
    _run_alembic_downgrade(sync_url)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Provide a transactional database session that rolls back after each test.
    This keeps tests isolated without recreating tables.

    Session isolation strategy:
    - NullPool (see test_engine) ensures no connection reuse across tests.
    - RLS context (ROLE + app.current_org_id) is reset BOTH at session start
      and in the finally block to guard against leaks even if a test errors out
      mid-flight.
    - The transaction is always rolled back so no test data persists.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    # Reset RLS context at the START of each test to prevent leaks from
    # any previous test that may have set ROLE or app.current_org_id.
    try:
        await connection.execute(text("RESET ROLE"))
        await connection.execute(text("RESET SESSION AUTHORIZATION"))
        await connection.execute(
            text("SELECT set_config('app.current_org_id', '', true)")
        )
    except Exception:
        pass

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        # Reset RLS context to prevent leaks between tests
        try:
            await connection.execute(text("RESET ROLE"))
            await connection.execute(
                text("SELECT set_config('app.current_org_id', '', true)")
            )
        except Exception:
            pass
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    Provide an AsyncClient with the test database session injected via dependency override.
    Commit is replaced by flush so data is visible within the session without committing.
    """
    async def override_get_db():
        try:
            yield db_session
            await db_session.flush()      # Primär data + triggar audit
            await db_session.flush()      # Sparar audit-entries
        except Exception:
            await db_session.rollback()
            raise

    async def override_get_rls_db(
        x_organization_id: str | None = Header(default=None),
    ):
        # Byt till icke-superuser så RLS policies enforças
        if x_organization_id:
            try:
                import uuid as _uuid
                _uuid.UUID(x_organization_id)  # Validera UUID-format
            except ValueError:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=f"Ogiltigt UUID i X-Organization-Id: {x_organization_id!r}",
                )
            await db_session.execute(text("SET LOCAL ROLE systemregister_app"))
            await db_session.execute(
                text("SELECT set_org_context(CAST(:org_id AS uuid))"),
                {"org_id": x_organization_id},
            )
        try:
            yield db_session
            await db_session.flush()      # Primär data + triggar audit
            await db_session.flush()      # Sparar audit-entries
        except Exception:
            await db_session.rollback()
            raise
        finally:
            # Återställ till superuser
            if x_organization_id:
                await db_session.execute(text("RESET ROLE"))

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_rls_db] = override_get_rls_db

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
