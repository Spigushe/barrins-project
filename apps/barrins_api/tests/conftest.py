"""Pytest configuration and shared fixtures.

Fixtures
--------
app
    The FastAPI application instance.
client
    An async httpx.AsyncClient wired to the test app (no real server).
db_session
    An AsyncSession bound to an in-transaction savepoint that is rolled
    back after each test — keeps tests isolated without recreating tables.

Environment
-----------
Tests expect a reachable PostgreSQL database.  Override the connection
string via the ``TEST_DATABASE_URL`` environment variable (defaults to
the value in .env.ini with the database name suffixed by ``_test``).
"""

import os
from collections.abc import AsyncGenerator, Generator
from importlib import import_module

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncConnection

from app.config import settings
from app.database import Base
from app.database.session import get_db
from app.main import app
from tests.helpers import ensure_test_db_exists

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------
# CI set TEST_DATABASE_URL explicitly (e.g. postgres_test).
# Local dev falls back to the app DB URL + "_test" suffix.
_TEST_DB_URL: str = os.environ.get("TEST_DATABASE_URL") or (
    str(settings.base.database_url).rstrip("/") + "_test"
)
# Sync URL for psycopg2-based engine (used to create tables once per session).
_TEST_DB_SYNC_URL: str = _TEST_DB_URL.replace("+asyncpg", "")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _stable_test_settings(monkeypatch: pytest.MonkeyPatch):
    """Forces reproducible test defaults for the auth routes.

    Tests must control their own application configuration and must not
    depend on the repo's `.env` file to behave correctly.
    """
    monkeypatch.setattr(settings.base, "require_email_verification", True)
    monkeypatch.setattr(settings.base, "smtp_host", None)
    monkeypatch.setattr(settings.base, "frontend_base_url", "http://localhost:5173")


# ---------------------------------------------------------------------------
# Engine & tables (session-scoped — created once per test run, SYNC)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine]:
    """Creates the tables once per session via psycopg2 (sync).

    A synchronous engine is used to avoid any asyncio event-loop conflict
    between session-scoped fixtures and function-scoped tests.
    """
    import_module("app.models")

    ensure_test_db_exists(_TEST_DB_SYNC_URL)
    sync_engine = create_engine(_TEST_DB_SYNC_URL, echo=False)
    Base.metadata.create_all(sync_engine, checkfirst=True)
    yield sync_engine
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test transactional connection — rolled back after each test
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def db_connection(test_engine: Engine) -> AsyncGenerator[AsyncConnection]:
    """Async connection with an open transaction — fully rolled back after the test.

    All operations in the test (seeders via db_session + HTTP requests via
    client) share this single connection and see the same data without
    needing to commit.
    """
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(
    db_connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession]:
    """Async session for seeding and assertion operations in tests."""
    async with async_sessionmaker(
        bind=db_connection, expire_on_commit=False
    )() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP client — per-request DB session to avoid asyncpg concurrent-use errors
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def client(db_connection: AsyncConnection) -> AsyncGenerator[AsyncClient]:
    """Async HTTP client — each request gets its own session.

    Reusing the same Session instance across requests causes asyncpg
    conflicts when BaseHTTPMiddleware runs the handler in an asyncio
    subtask. Creating a new Session object per request avoids these
    conflicts while sharing the same connection (and therefore the same
    uncommitted transaction as the data seeded via db_session).
    """
    Session = async_sessionmaker(bind=db_connection, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
