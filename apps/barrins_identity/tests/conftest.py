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
Tests expect a reachable PostgreSQL database. Override the connection
string via the ``TEST_DATABASE_URL`` environment variable (defaults to
``DATABASE_URL`` with the database name suffixed by ``_test``).

JWT_PRIVATE_KEY is generated fresh for the test session (ephemeral RSA
keypair) if not already set in the environment — never a committed key
(platform.md §13). This MUST happen before any `app.*` module is
imported, since app.config.settings is a module-level singleton that
reads the environment once, at import time.
"""

import os

from tests.helpers import ensure_test_db_exists, generate_ephemeral_rsa_private_key_pem

# barrins-identity owns its own, dedicated database (platform.md §5) — never
# shared with barrins_api. Force DATABASE_URL to a local test value rather
# than deferring to a pre-existing environment variable: a DATABASE_URL set
# for a *different* app (e.g. barrins_api, pointing at a real host) must
# never leak into this app's test run.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL_BASE",
    "postgresql+asyncpg://user:pass@localhost:5432/barrins_identity",
)
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:5173"]')
os.environ.setdefault("JWT_PRIVATE_KEY", generate_ephemeral_rsa_private_key_pem())
os.environ.setdefault("JWT_KID", "test-kid")
os.environ.setdefault("LOG_TO_FILE", "false")

from collections.abc import AsyncGenerator, Generator
from importlib import import_module

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.engine import AsyncConnection

from app.config import settings
from app.core.rate_limit import limiter
from app.database import Base
from app.database.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------
_TEST_DB_URL: str = os.environ.get("TEST_DATABASE_URL") or (
    str(settings.base.database_url).rstrip("/") + "_test"
)
_TEST_DB_SYNC_URL: str = _TEST_DB_URL.replace("+asyncpg", "")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clears slowapi's in-memory counters between tests.

    Without this, unrelated tests hitting POST /auth/token would share the
    same rate-limit window (same client address under ASGITransport) and
    start failing with 429 once the cumulative count crosses the limit.
    """
    limiter.reset()


@pytest.fixture(autouse=True)
def _stable_test_settings(monkeypatch: pytest.MonkeyPatch):
    """Forces reproducible test defaults for the signup/verification routes.

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
    """Creates the tables once per session via psycopg2 (sync)."""
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
    """Async connection with an open transaction — fully rolled back after the test."""
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
    """Async HTTP client — each request gets its own session."""
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
