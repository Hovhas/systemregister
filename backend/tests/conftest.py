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
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.database import Base, get_db
from app.main import app as fastapi_app
# Import all models so Base.metadata is populated
import app.models.models  # noqa: F401

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://systemregister:devpassword@db:5432/systemregister_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for the test database (session-scoped)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
            await db_session.flush()
        except Exception:
            await db_session.rollback()
            raise

    fastapi_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
