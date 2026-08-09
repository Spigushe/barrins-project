"""Tests for `GET /internal/scripture/db-metrics`.

Covers the dual auth gate (`verify_scripture_or_admin`) and the reported
table set.
"""

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

_TOKEN = "test-scripture-token"  # noqa: S105
_URL = "/internal/scripture/db-metrics"

_BS_TABLE_NAMES = {
    "bs_tournaments",
    "bs_decks",
    "bs_deck_cards",
    "bs_rounds",
    "bs_round_matches",
    "bs_standings",
}


@pytest.fixture(autouse=True)
def _configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.base, "scripture_ingest_token", SecretStr(_TOKEN))


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email,
            "tkv": user.token_version,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def admin_user(db_session) -> User:
    user = User(
        email="admin@scripture.example.com",
        hashed_password=hash_password("Admin#Pass1word"),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def regular_user(db_session) -> User:
    user = User(
        email="user@scripture.example.com",
        hashed_password=hash_password("User#Pass1word"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestDbMetricsAuth:
    async def test_scripture_token_is_allowed(self, client: AsyncClient):
        resp = await client.get(_URL, headers={"X-Scripture-Token": _TOKEN})
        assert resp.status_code == 200

    async def test_admin_is_allowed(self, client: AsyncClient, admin_user: User):
        resp = await client.get(_URL, headers=_auth_headers(admin_user))
        assert resp.status_code == 200

    async def test_regular_user_gets_403(self, client: AsyncClient, regular_user: User):
        resp = await client.get(_URL, headers=_auth_headers(regular_user))
        assert resp.status_code == 403

    async def test_missing_credentials_gets_401(self, client: AsyncClient):
        resp = await client.get(_URL)
        assert resp.status_code == 401

    async def test_wrong_token_gets_401(self, client: AsyncClient):
        resp = await client.get(_URL, headers={"X-Scripture-Token": "wrong"})
        assert resp.status_code == 401


class TestDbMetricsResponse:
    async def test_reports_every_bs_table(self, client: AsyncClient):
        resp = await client.get(_URL, headers={"X-Scripture-Token": _TOKEN})
        assert resp.status_code == 200

        body = resp.json()
        table_names = {entry["table_name"] for entry in body["tables"]}
        assert table_names == _BS_TABLE_NAMES
        assert all(entry["size_bytes"] >= 0 for entry in body["tables"])
