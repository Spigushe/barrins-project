"""Tests for app/dependencies/auth.py — direct dependency calls.

No route in barrins-identity itself is protected by
get_current_service_account (service tokens are consumed by other apps,
platform.md §5) — so its symmetric rejection of a user token (tests.md §3)
is exercised here directly rather than through an HTTP route.
"""

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, create_service_token, hash_password
from app.dependencies.auth import get_current_service_account, get_current_user
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole


@pytest.fixture()
async def regular_user(db_session) -> User:
    user = User(
        email="dep-user@test.com",
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
async def service_account(db_session) -> ServiceAccount:
    account = ServiceAccount(
        client_id="sa_dependency_test",
        hashed_client_secret=hash_password("secret"),
        scopes=["tolaria:read"],
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self, db_session, regular_user: User):
        token = create_access_token(
            {
                "sub": str(regular_user.id),
                "role": regular_user.role.value,
                "email": regular_user.email,
                "tkv": regular_user.token_version,
            }
        )
        user = await get_current_user(token, db_session)
        assert user.id == regular_user.id

    async def test_service_token_rejected(self, db_session, service_account):
        token = create_service_token(
            {
                "sub": service_account.client_id,
                "scopes": service_account.scopes,
                "tkv": service_account.token_version,
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_inactive_user_rejected(self, db_session, regular_user: User):
        regular_user.is_active = False
        db_session.add(regular_user)
        await db_session.commit()

        token = create_access_token(
            {
                "sub": str(regular_user.id),
                "role": regular_user.role.value,
                "email": regular_user.email,
                "tkv": regular_user.token_version,
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_revoked_token_version_rejected(self, db_session, regular_user: User):
        token = create_access_token(
            {
                "sub": str(regular_user.id),
                "role": regular_user.role.value,
                "email": regular_user.email,
                "tkv": regular_user.token_version,
            }
        )
        regular_user.token_version += 1
        db_session.add(regular_user)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentServiceAccount:
    async def test_valid_token_returns_account(
        self, db_session, service_account: ServiceAccount
    ):
        token = create_service_token(
            {
                "sub": service_account.client_id,
                "scopes": service_account.scopes,
                "tkv": service_account.token_version,
            }
        )
        account = await get_current_service_account(token, db_session)
        assert account.client_id == service_account.client_id

    async def test_user_token_rejected(self, db_session, regular_user: User):
        """Symmetric case of the service-token-as-user rejection (tests.md §3)."""
        token = create_access_token(
            {
                "sub": str(regular_user.id),
                "role": regular_user.role.value,
                "email": regular_user.email,
                "tkv": regular_user.token_version,
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_service_account(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_unknown_client_id_rejected(self, db_session):
        token = create_service_token({"sub": "sa_ghost", "scopes": [], "tkv": 0})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_service_account(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_inactive_account_rejected(
        self, db_session, service_account: ServiceAccount
    ):
        token = create_service_token(
            {
                "sub": service_account.client_id,
                "scopes": service_account.scopes,
                "tkv": service_account.token_version,
            }
        )
        service_account.is_active = False
        db_session.add(service_account)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_service_account(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_revoked_token_version_rejected(
        self, db_session, service_account: ServiceAccount
    ):
        token = create_service_token(
            {
                "sub": service_account.client_id,
                "scopes": service_account.scopes,
                "tkv": service_account.token_version,
            }
        )
        service_account.token_version += 1
        db_session.add(service_account)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_service_account(token, db_session)
        assert exc_info.value.status_code == 401

    async def test_invalid_token_rejected(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_service_account("not.a.token", db_session)
        assert exc_info.value.status_code == 401
