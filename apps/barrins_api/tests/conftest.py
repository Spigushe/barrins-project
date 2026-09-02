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
from app.services.scripture.card_resolver import invalidate_name_cache
from tests.helpers import ensure_test_db_exists
from tests.identity_auth import FakeUser, install_test_jwks

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
def _identity_jwks() -> None:
    """Point the app's `JWKSCache` at the test signing key (ADR-20).

    Every test authenticates with an RS256 token minted by
    `tests.identity_auth`; this loads the matching public key so
    `identity_client` verifies it locally without any network call.
    """
    install_test_jwks()


# ---------------------------------------------------------------------------
# Identity users (no DB — barrins_api has no `users` table post-ADR-20)
# ---------------------------------------------------------------------------
@pytest.fixture()
def regular_user() -> FakeUser:
    """A plain `user`-role identity caller."""
    return FakeUser(email="regular@example.test", role="user", username="regular")


# `plain_user` is the same thing under the name some suites already use.
@pytest.fixture()
def plain_user() -> FakeUser:
    return FakeUser(email="plain@example.test", role="user", username="plain")


@pytest.fixture()
def admin_user() -> FakeUser:
    return FakeUser(email="admin@example.test", role="admin", username="admin")


@pytest.fixture()
def owner_user() -> FakeUser:
    """Main user — owner of the data created in the Tamiyo Scroll tests.

    No `display_name` — a fresh identity account has none until the user
    sets one; the directory then labels this user by `username`.
    """
    return FakeUser(
        email="owner@tamiyo-scroll.example.com", role="user", username="owner"
    )


@pytest.fixture()
def other_user() -> FakeUser:
    """Second user — for sharing / cross-owner scenarios."""
    return FakeUser(
        email="other@tamiyo-scroll.example.com", role="user", username="other"
    )


@pytest.fixture()
def third_user() -> FakeUser:
    """Third user — for scenarios needing two distinct sharers at once."""
    return FakeUser(
        email="third@tamiyo-scroll.example.com", role="user", username="third"
    )


@pytest.fixture(autouse=True)
def _reset_card_name_cache():
    """Resets `card_resolver`'s process-local name cache before each test.

    That cache (see its module docstring) is a plain module-level global,
    not scoped to a request or a DB transaction — once any test builds it
    against an empty/partial `cards` table, it silently stays "built" and
    stale for every later test sharing this process, however unrelated
    (a card added by a later test's own fixtures would never be found).
    Rebuilding it fresh per test keeps tests order-independent.
    """
    invalidate_name_cache()


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


# ---------------------------------------------------------------------------
# MTGJSON import-progress tracker — redirected onto the test connection
# ---------------------------------------------------------------------------
@pytest.fixture()
def mtgjson_tracker_uses_test_db(
    monkeypatch: pytest.MonkeyPatch, db_connection: AsyncConnection
) -> None:
    """Points `_ImportRunTracker` at this test's connection, not the real DB.

    `app/services/mtgjson/importer.py`'s `_ImportRunTracker` deliberately
    writes through its own session, independent of the `db_session`/
    `client` request session, via `app.database.connection.AsyncSessionLocal`
    -- that's bound to the real per-environment database (e.g. dev), not
    `_TEST_DB_URL`. Without this, any test that imports MTGJSON data would
    silently write real, uncommitted-forever rows to the live dev database
    instead of the isolated, rolled-back test one. Used by every test
    module that calls `import_all_printings` (`test_mtgjson.py`,
    `test_mtgjson_import_status.py`), via `pytestmark`.
    """
    monkeypatch.setattr(
        "app.services.mtgjson.importer.AsyncSessionLocal",
        async_sessionmaker(bind=db_connection, expire_on_commit=False),
    )
