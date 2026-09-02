"""Tests for POST /api/v1/users/lookup — batch user-label directory (ADR-20).

Service-token only, scope `identity:users:read`. Returns
`{id, username, display_name}` for active accounts; unknown and
deactivated ids are omitted; email / role / status are never returned.
Consumed by `barrins_api` post-cutover for team-roster / sharing labels.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_service_token, hash_password
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole

LOOKUP_URL = "/api/v1/users/lookup"
READ_SCOPE = "identity:users:read"


def _service_token(account: ServiceAccount) -> str:
    return create_service_token(
        {
            "sub": account.client_id,
            "scopes": account.scopes,
            "tkv": account.token_version,
        }
    )


def _headers(account: ServiceAccount) -> dict[str, str]:
    return {"Authorization": f"Bearer {_service_token(account)}"}


@pytest.fixture()
async def reader_account(db_session) -> ServiceAccount:
    account = ServiceAccount(
        client_id="sa_lookup_reader",
        hashed_client_secret=hash_password("secret-value"),
        scopes=[READ_SCOPE],
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture()
async def scopeless_account(db_session) -> ServiceAccount:
    account = ServiceAccount(
        client_id="sa_no_scope",
        hashed_client_secret=hash_password("secret-value"),
        scopes=["tolaria:read"],
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture()
async def seeded_users(db_session) -> dict[str, User]:
    active_named = User(
        email="named@lookup.test",
        username="named-user",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.user,
        display_name="Named User",
        is_active=True,
        is_verified=True,
    )
    active_no_name = User(
        email="plain@lookup.test",
        username="plain-user",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    deactivated = User(
        email="gone@lookup.test",
        username="gone-user",
        hashed_password=hash_password("User#Pass1word"),
        role=UserRole.user,
        is_active=False,
        is_verified=True,
    )
    db_session.add_all([active_named, active_no_name, deactivated])
    await db_session.commit()
    for u in (active_named, active_no_name, deactivated):
        await db_session.refresh(u)
    return {
        "named": active_named,
        "no_name": active_no_name,
        "deactivated": deactivated,
    }


class TestAuth:
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(LOOKUP_URL, json={"ids": [str(uuid.uuid4())]})
        assert resp.status_code == 401

    async def test_user_token_rejected(self, client: AsyncClient, db_session):
        from app.core.security import create_access_token

        user = User(
            email="u@lookup.test",
            username="u-lookup",
            hashed_password=hash_password("User#Pass1word"),
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role.value,
                "email": user.email,
                "tkv": user.token_version,
            }
        )
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(user.id)]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    async def test_service_token_without_scope_returns_403(
        self, client: AsyncClient, scopeless_account: ServiceAccount
    ):
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(uuid.uuid4())]},
            headers=_headers(scopeless_account),
        )
        assert resp.status_code == 403


class TestLookup:
    async def test_returns_label_attributes_for_active_users(
        self,
        client: AsyncClient,
        reader_account: ServiceAccount,
        seeded_users: dict[str, User],
    ):
        named, no_name = seeded_users["named"], seeded_users["no_name"]
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(named.id), str(no_name.id)]},
            headers=_headers(reader_account),
        )
        assert resp.status_code == 200
        by_id = {row["id"]: row for row in resp.json()}
        assert by_id[str(named.id)] == {
            "id": str(named.id),
            "username": "named-user",
            "display_name": "Named User",
        }
        assert by_id[str(no_name.id)]["display_name"] is None
        # No email / role / status ever leaks.
        assert "email" not in by_id[str(named.id)]
        assert "role" not in by_id[str(named.id)]

    async def test_unknown_ids_are_omitted(
        self,
        client: AsyncClient,
        reader_account: ServiceAccount,
        seeded_users: dict[str, User],
    ):
        known = seeded_users["named"]
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(known.id), str(uuid.uuid4()), str(uuid.uuid4())]},
            headers=_headers(reader_account),
        )
        assert resp.status_code == 200
        assert [row["id"] for row in resp.json()] == [str(known.id)]

    async def test_deactivated_users_are_omitted(
        self,
        client: AsyncClient,
        reader_account: ServiceAccount,
        seeded_users: dict[str, User],
    ):
        gone = seeded_users["deactivated"]
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(gone.id)]},
            headers=_headers(reader_account),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_empty_ids_list_returns_422(
        self, client: AsyncClient, reader_account: ServiceAccount
    ):
        resp = await client.post(
            LOOKUP_URL, json={"ids": []}, headers=_headers(reader_account)
        )
        assert resp.status_code == 422

    async def test_over_the_cap_returns_422(
        self, client: AsyncClient, reader_account: ServiceAccount
    ):
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(uuid.uuid4()) for _ in range(201)]},
            headers=_headers(reader_account),
        )
        assert resp.status_code == 422

    async def test_duplicate_ids_are_collapsed(
        self,
        client: AsyncClient,
        reader_account: ServiceAccount,
        seeded_users: dict[str, User],
    ):
        known = seeded_users["named"]
        resp = await client.post(
            LOOKUP_URL,
            json={"ids": [str(known.id), str(known.id), str(known.id)]},
            headers=_headers(reader_account),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
