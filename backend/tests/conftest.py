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


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for the test database (session-scoped).

    Uses NullPool to prevent connection state (RLS context, SET LOCAL)
    from leaking between tests via pooled connections. Each test gets
    a fresh connection, eliminating the session-isolation failures that
    occur when running `pytest tests/` (all files).
    """
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Skapa icke-superuser roll + ge grants (krävs för att RLS ska enforças)
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

    # RLS-funktioner och policies (från alembic/versions/0001_enable_rls_multi_org.py)
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION set_org_context(p_org_id UUID)
            RETURNS void
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            BEGIN
                PERFORM set_config('app.current_org_id', p_org_id::text, true);
            END;
            $$;
        """))

        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION current_org_id()
            RETURNS UUID
            LANGUAGE plpgsql
            STABLE
            AS $$
            DECLARE
                v_setting text;
            BEGIN
                v_setting := current_setting('app.current_org_id', true);
                IF v_setting IS NULL OR v_setting = '' THEN
                    RETURN NULL;
                END IF;
                RETURN v_setting::UUID;
            EXCEPTION WHEN others THEN
                RETURN NULL;
            END;
            $$;
        """))

        for table in [
            "systems",
            "system_owners",
            "system_classifications",
            "system_integrations",
            "gdpr_treatments",
            "contracts",
        ]:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

        # Drop existing policies first (idempotent setup)
        for table in [
            "systems", "system_owners", "system_classifications",
            "system_integrations", "gdpr_treatments", "contracts",
        ]:
            await conn.execute(text(f"DROP POLICY IF EXISTS org_isolation ON {table};"))

        # Policies med NULL-bypass: utan org-context ser man allt (bypass-mode)
        await conn.execute(text("""
            CREATE POLICY org_isolation ON systems
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (current_org_id() IS NULL OR organization_id = current_org_id());
        """))

        await conn.execute(text("""
            CREATE POLICY org_isolation ON system_owners
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (current_org_id() IS NULL OR organization_id = current_org_id());
        """))

        await conn.execute(text("""
            CREATE POLICY org_isolation ON system_classifications
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (
                current_org_id() IS NULL OR EXISTS (
                    SELECT 1 FROM systems s
                    WHERE s.id = system_classifications.system_id
                      AND s.organization_id = current_org_id()
                )
            );
        """))

        await conn.execute(text("""
            CREATE POLICY org_isolation ON system_integrations
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (
                current_org_id() IS NULL OR EXISTS (
                    SELECT 1 FROM systems s
                    WHERE s.organization_id = current_org_id()
                      AND (
                          s.id = system_integrations.source_system_id
                       OR s.id = system_integrations.target_system_id
                      )
                )
            );
        """))

        await conn.execute(text("""
            CREATE POLICY org_isolation ON gdpr_treatments
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (
                current_org_id() IS NULL OR EXISTS (
                    SELECT 1 FROM systems s
                    WHERE s.id = gdpr_treatments.system_id
                      AND s.organization_id = current_org_id()
                )
            );
        """))

        await conn.execute(text("""
            CREATE POLICY org_isolation ON contracts
            AS PERMISSIVE FOR ALL TO PUBLIC
            USING (
                current_org_id() IS NULL OR EXISTS (
                    SELECT 1 FROM systems s
                    WHERE s.id = contracts.system_id
                      AND s.organization_id = current_org_id()
                )
            );
        """))

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    Provide a transactional database session that rolls back after each test.
    This keeps tests isolated without recreating tables.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

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
