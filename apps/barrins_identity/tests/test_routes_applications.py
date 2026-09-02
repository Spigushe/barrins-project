"""Tests for GET /api/v1/applications — the role-aware app directory (ADR-19).

Optional auth: anonymous is allowed and gets `login_required` on
member-only apps. The endpoint never filters the caller's own app.
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.application import Application
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


async def _make_user(db_session, role: UserRole) -> User:
    user = User(
        email=f"{role.value}-apps@example.com",
        username=f"{role.value}_apps",
        hashed_password=hash_password("User#Pass1word"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def seed_apps(db_session) -> None:
    db_session.add_all(
        [
            Application(
                key="goblin_guide",
                name="Goblin Guide",
                description="Account.",
                url="https://goblin.test",
                logo_svg="<svg/>",
                needs_authentication=True,
                sort_order=0,
            ),
            Application(
                key="tamiyo_scroll",
                name="Tamiyo Scroll",
                description="Decks.",
                url="https://tamiyo.test",
                logo_svg="<svg/>",
                needs_authentication=True,
                sort_order=10,
            ),
            Application(
                key="tolaria_news",
                name="Tolaria News",
                description="Meta.",
                url="https://tolaria.test",
                logo_svg="<svg/>",
                needs_authentication=False,
                sort_order=20,
            ),
            Application(
                key="karn_jupyter",
                name="Karn Tablets",
                description="ML.",
                url="https://karn.test",
                logo_svg="<svg/>",
                needs_authentication=True,
                is_role_restricted=True,
                min_role=UserRole.ml_developer,
                sort_order=30,
            ),
            Application(
                key="hidden_app",
                name="Hidden",
                description="Off.",
                url="https://hidden.test",
                logo_svg="<svg/>",
                needs_authentication=False,
                is_active=False,
                sort_order=5,
            ),
        ]
    )
    await db_session.commit()


def _by_key(payload: list[dict]) -> dict[str, dict]:
    return {row["key"]: row for row in payload}


class TestListApplications:
    async def test_anonymous_sees_public_open_and_members_login_required(
        self, client: AsyncClient, seed_apps: None
    ):
        resp = await client.get("/api/v1/applications")
        assert resp.status_code == 200
        rows = _by_key(resp.json())

        assert rows["tolaria_news"]["access"] == "open"
        assert rows["goblin_guide"]["access"] == "login_required"
        assert rows["tamiyo_scroll"]["access"] == "login_required"
        assert rows["karn_jupyter"]["access"] == "login_required"

    async def test_inactive_app_is_omitted(self, client: AsyncClient, seed_apps: None):
        resp = await client.get("/api/v1/applications")
        assert "hidden_app" not in _by_key(resp.json())

    async def test_ordered_by_sort_order(self, client: AsyncClient, seed_apps: None):
        resp = await client.get("/api/v1/applications")
        keys = [row["key"] for row in resp.json()]
        assert keys == ["goblin_guide", "tamiyo_scroll", "tolaria_news", "karn_jupyter"]

    async def test_current_app_is_not_filtered_server_side(
        self, client: AsyncClient, seed_apps: None
    ):
        # The caller's own app is dropped by the SPA, never here.
        resp = await client.get("/api/v1/applications")
        assert "goblin_guide" in _by_key(resp.json())

    async def test_min_role_echoed_only_for_restricted(
        self, client: AsyncClient, seed_apps: None
    ):
        rows = _by_key((await client.get("/api/v1/applications")).json())
        assert rows["karn_jupyter"]["min_role"] == "ml_developer"
        assert rows["tolaria_news"]["min_role"] is None

    async def test_logo_svg_is_returned_verbatim(
        self, client: AsyncClient, seed_apps: None
    ):
        rows = _by_key((await client.get("/api/v1/applications")).json())
        assert rows["goblin_guide"]["logo_svg"] == "<svg/>"

    async def test_regular_user_opens_members_apps_but_not_role_gated(
        self, client: AsyncClient, seed_apps: None, db_session
    ):
        user = await _make_user(db_session, UserRole.user)
        resp = await client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {_access_token_for(user)}"},
        )
        rows = _by_key(resp.json())
        assert rows["goblin_guide"]["access"] == "open"
        assert rows["tamiyo_scroll"]["access"] == "open"
        assert rows["tolaria_news"]["access"] == "open"
        assert rows["karn_jupyter"]["access"] == "role_denied"

    async def test_ml_developer_opens_the_role_gated_app(
        self, client: AsyncClient, seed_apps: None, db_session
    ):
        user = await _make_user(db_session, UserRole.ml_developer)
        resp = await client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {_access_token_for(user)}"},
        )
        assert _by_key(resp.json())["karn_jupyter"]["access"] == "open"

    async def test_admin_opens_everything(
        self, client: AsyncClient, seed_apps: None, db_session
    ):
        user = await _make_user(db_session, UserRole.admin)
        resp = await client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {_access_token_for(user)}"},
        )
        assert {row["access"] for row in resp.json()} == {"open"}

    async def test_a_supplied_but_invalid_token_is_401_not_anonymous(
        self, client: AsyncClient, seed_apps: None
    ):
        resp = await client.get(
            "/api/v1/applications",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert resp.status_code == 401
