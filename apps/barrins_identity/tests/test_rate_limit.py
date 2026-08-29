"""Tests for the POST /auth/token rate limit (tests.md §2, LOGIN_RATE_LIMIT)."""

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.fixture(autouse=True)
def _low_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """Forces a low, deterministic limit so the test doesn't need 5+ calls
    (or depend on the production default)."""
    monkeypatch.setattr(settings.base, "login_rate_limit", "2/minute")


class TestLoginRateLimit:
    async def test_exceeding_limit_returns_429(self, client: AsyncClient):
        payload = {"username": "nobody@example.com", "password": "Whatever#1pass"}

        first = await client.post("/api/v1/auth/token", data=payload)
        second = await client.post("/api/v1/auth/token", data=payload)
        third = await client.post("/api/v1/auth/token", data=payload)

        assert first.status_code == 401  # under the limit, normal auth failure
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
