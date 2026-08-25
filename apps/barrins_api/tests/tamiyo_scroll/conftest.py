"""Shared pytest fixtures for the Tamiyo Scroll domain tests."""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

BASE = "/bff/tamiyo-scroll"


def _claims(user: User) -> dict[str, str | int]:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
        "tkv": user.token_version,
    }


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(_claims(user))
    return {"Authorization": f"Bearer {token}"}


async def create_active_personal_deck(
    client: AsyncClient,
    user: User,
    name: str = "My Deck",
    *,
    game: str = "magic",
    category: str = "midrange",
) -> dict:
    """Creates a personal deck and selects it as the caller's active deck
    (F10: `GET /meta-decks` needs an active deck to resolve any scope) —
    mirrors what `PersonalDeckSelector.createAndSelect` does on the
    frontend, since the backend itself never auto-selects on create.
    """
    headers = auth_headers(user)
    resp = await client.post(
        f"{BASE}/personal-decks",
        json={"name": name, "game": game, "category": category},
        headers=headers,
    )
    assert resp.status_code == 201
    deck = resp.json()
    settings_resp = await client.patch(
        f"{BASE}/me/settings",
        json={"active_personal_deck_id": deck["id"]},
        headers=headers,
    )
    assert settings_resp.status_code == 200
    return deck


@pytest.fixture()
async def owner_user(db_session) -> User:
    """Main user — owner of the data created in the tests."""
    user = User(
        email="owner@tamiyo-scroll.example.com",
        hashed_password=hash_password("Owner#Pass1word"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def other_user(db_session) -> User:
    """Second user — for sharing / cross-owner scenarios."""
    user = User(
        email="other@tamiyo-scroll.example.com",
        hashed_password=hash_password("Other#Pass1word"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def third_user(db_session) -> User:
    """Third user — for scenarios needing two distinct sharers at once."""
    user = User(
        email="third@tamiyo-scroll.example.com",
        hashed_password=hash_password("Third#Pass1word"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
