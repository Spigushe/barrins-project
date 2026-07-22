"""Tests for /api/v1/service-accounts and /api/v1/service-token.

Negative cases follow tests.md §3.
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.service_account import ServiceAccount
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
async def admin_user(db_session) -> User:
    user = User(
        email="admin2@test.com",
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
        email="user2@test.com",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.user,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def service_account(db_session) -> tuple[ServiceAccount, str]:
    plaintext_secret = "super-secret-value"
    account = ServiceAccount(
        client_id="sa_fixture",
        hashed_client_secret=hash_password(plaintext_secret),
        scopes=["tolaria:read"],
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account, plaintext_secret


# ---------------------------------------------------------------------------
# POST /service-accounts
# ---------------------------------------------------------------------------


class TestCreateServiceAccount:
    async def test_admin_creates_account(self, client: AsyncClient, admin_user: User):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/service-accounts",
            json={"description": "Tolaria News", "scopes": ["tolaria:read"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["client_id"].startswith("sa_")
        assert "client_secret" in body
        assert body["scopes"] == ["tolaria:read"]

    async def test_non_admin_returns_403(self, client: AsyncClient, regular_user: User):
        token = _access_token_for(regular_user)
        resp = await client.post(
            "/api/v1/service-accounts",
            json={"scopes": ["tolaria:read"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/service-accounts", json={"scopes": ["tolaria:read"]}
        )
        assert resp.status_code == 401

    async def test_empty_scopes_returns_422(
        self, client: AsyncClient, admin_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/service-accounts",
            json={"scopes": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /service-accounts
# ---------------------------------------------------------------------------


class TestListServiceAccounts:
    async def test_admin_lists_accounts(
        self, client: AsyncClient, admin_user: User, service_account
    ):
        token = _access_token_for(admin_user)
        resp = await client.get(
            "/api/v1/service-accounts", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert any(a["client_id"] == "sa_fixture" for a in body)
        assert all("client_secret" not in a for a in body)

    async def test_non_admin_returns_403(self, client: AsyncClient, regular_user: User):
        token = _access_token_for(regular_user)
        resp = await client.get(
            "/api/v1/service-accounts", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /service-accounts/{client_id}/revoke
# ---------------------------------------------------------------------------


class TestRevokeServiceAccount:
    async def test_admin_revokes_account(
        self, client: AsyncClient, db_session, admin_user: User, service_account
    ):
        account, _secret = service_account
        token = _access_token_for(admin_user)
        resp = await client.post(
            f"/api/v1/service-accounts/{account.client_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204
        await db_session.refresh(account)
        assert account.is_active is False
        assert account.token_version == 1

    async def test_unknown_client_id_returns_404(
        self, client: AsyncClient, admin_user: User
    ):
        token = _access_token_for(admin_user)
        resp = await client.post(
            "/api/v1/service-accounts/sa_does_not_exist/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_non_admin_returns_403(
        self, client: AsyncClient, regular_user: User, service_account
    ):
        account, _secret = service_account
        token = _access_token_for(regular_user)
        resp = await client.post(
            f"/api/v1/service-accounts/{account.client_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /service-token
# ---------------------------------------------------------------------------


class TestIssueServiceToken:
    async def test_valid_credentials_return_token(
        self, client: AsyncClient, service_account
    ):
        account, secret = service_account
        resp = await client.post(
            "/api/v1/service-token",
            json={"client_id": account.client_id, "client_secret": secret},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 15 * 60

    async def test_unknown_client_id_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/service-token",
            json={"client_id": "sa_does_not_exist", "client_secret": "whatever"},
        )
        assert resp.status_code == 401

    async def test_wrong_secret_returns_401(self, client: AsyncClient, service_account):
        account, _secret = service_account
        resp = await client.post(
            "/api/v1/service-token",
            json={"client_id": account.client_id, "client_secret": "wrong-secret"},
        )
        assert resp.status_code == 401

    async def test_unknown_and_wrong_secret_same_message(
        self, client: AsyncClient, service_account
    ):
        account, _secret = service_account
        unknown = (
            await client.post(
                "/api/v1/service-token",
                json={"client_id": "sa_does_not_exist", "client_secret": "whatever"},
            )
        ).json()["error"]["message"]
        wrong = (
            await client.post(
                "/api/v1/service-token",
                json={"client_id": account.client_id, "client_secret": "wrong-secret"},
            )
        ).json()["error"]["message"]
        assert unknown == wrong

    async def test_revoked_account_returns_401(
        self, client: AsyncClient, db_session, service_account
    ):
        account, secret = service_account
        account.is_active = False
        db_session.add(account)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/service-token",
            json={"client_id": account.client_id, "client_secret": secret},
        )
        assert resp.status_code == 401

    async def test_extra_field_returns_422(self, client: AsyncClient, service_account):
        account, secret = service_account
        resp = await client.post(
            "/api/v1/service-token",
            json={
                "client_id": account.client_id,
                "client_secret": secret,
                "injected": "evil",
            },
        )
        assert resp.status_code == 422
