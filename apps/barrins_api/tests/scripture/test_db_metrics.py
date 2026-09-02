"""Tests for `GET /internal/scripture/db-metrics`.

Covers the dual auth gate (`verify_scripture_or_admin`) and the reported
table set.
"""

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from app.config import settings
from tests.identity_auth import FakeUser as User
from tests.identity_auth import auth_headers as _auth_headers

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


@pytest.fixture()
def admin_user() -> User:
    return User(
        email="admin@scripture.example.com", role="admin", username="scripture-admin"
    )


@pytest.fixture()
def regular_user() -> User:
    return User(
        email="user@scripture.example.com", role="user", username="scripture-user"
    )


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
        assert all(entry["row_count"] >= 0 for entry in body["tables"])
