"""Tests for GET/PUT /api/v1/users/me/settings/{app_key} (platform.md §17).

Negative cases follow tests.md §11.
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def _access_token_for(user: User) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "email": user.email,
            "tkv": user.token_version,
        }
    )


@pytest.fixture()
async def regular_user(db_session) -> User:
    user = User(
        email="user@test.com",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.user,
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def other_user(db_session) -> User:
    user = User(
        email="other@test.com",
        hashed_password=hash_password("Other#Pass1word"),
        role=UserRole.user,
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestGetAppSettings:
    async def test_never_written_returns_empty_dict(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.get(
            "/api/v1/users/me/settings/tamiyo_scroll",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {}

    async def test_unknown_app_key_returns_404(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.get(
            "/api/v1/users/me/settings/not_a_real_app",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me/settings/tamiyo_scroll")
        assert resp.status_code == 401

    async def test_get_never_creates_a_row(
        self, client: AsyncClient, db_session, regular_user: User
    ):
        from sqlalchemy import select

        from app.models.app_settings import AppSettings

        token = _access_token_for(regular_user)
        await client.get(
            "/api/v1/users/me/settings/tamiyo_scroll",
            headers={"Authorization": f"Bearer {token}"},
        )

        result = await db_session.execute(
            select(AppSettings).where(AppSettings.user_id == regular_user.id)
        )
        assert result.scalar_one_or_none() is None


class TestPutAppSettings:
    async def test_creates_row_on_first_write(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"data_shared": False, "active_personal_deck_id": None},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "data_shared": False,
            "active_personal_deck_id": None,
        }

    async def test_second_write_fully_replaces_first(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        headers = {"Authorization": f"Bearer {token}"}
        await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"data_shared": True, "extra_field": "gone-after-replace"},
            headers=headers,
        )

        resp = await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"data_shared": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {"data_shared": False}

        get_resp = await client.get(
            "/api/v1/users/me/settings/tamiyo_scroll", headers=headers
        )
        assert get_resp.json()["data"] == {"data_shared": False}

    async def test_unknown_app_key_returns_404(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.put(
            "/api/v1/users/me/settings/not_a_real_app",
            json={"x": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_oversized_payload_returns_413(
        self,
        client: AsyncClient,
        regular_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ):
        from app.config import settings

        monkeypatch.setattr(settings.base, "max_app_settings_bytes", 32)

        token = _access_token_for(regular_user)
        resp = await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"padding": "x" * 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413

    async def test_non_object_body_returns_422(
        self, client: AsyncClient, regular_user: User
    ):
        token = _access_token_for(regular_user)
        resp = await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            content=b"[1, 2, 3]",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll", json={"x": 1}
        )
        assert resp.status_code == 401

    async def test_user_isolation(
        self, client: AsyncClient, regular_user: User, other_user: User
    ):
        token_a = _access_token_for(regular_user)
        token_b = _access_token_for(other_user)

        await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"owner": "regular_user"},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        resp_b = await client.get(
            "/api/v1/users/me/settings/tamiyo_scroll",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.json()["data"] == {}

        await client.put(
            "/api/v1/users/me/settings/tamiyo_scroll",
            json={"owner": "other_user"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        resp_a = await client.get(
            "/api/v1/users/me/settings/tamiyo_scroll",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.json()["data"] == {"owner": "regular_user"}
