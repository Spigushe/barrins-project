"""Shared pytest fixtures for the Tamiyo Scroll domain tests."""

import pytest

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
