"""Shared pytest fixtures for the Tamiyo Scroll domain tests.

Since the identity cutover (ADR-20) these tests no longer insert `users`
rows: `owner_user` / `other_user` / `third_user` come from the top-level
`conftest.py` as `FakeUser` values, `auth_headers` mints an RS256 identity
token, and team-roster / sharing display labels are served by a
`FakeIdentityDirectory` overriding the real `get_identity_directory`.
"""

import pytest

from app.services.identity_directory import get_identity_directory
from tests.identity_auth import FakeIdentityDirectory, FakeUser, auth_headers

__all__ = ["BASE", "FakeUser", "auth_headers"]

BASE = "/bff/tamiyo-scroll"


@pytest.fixture(autouse=True)
def identity_directory(request: pytest.FixtureRequest) -> FakeIdentityDirectory:
    """Serve display labels from `_USER_REGISTRY` instead of calling identity.

    A test that needs a specific label (e.g. a sharer with a display name)
    can request this fixture and populate `identity_directory._extra`.
    """
    fake = FakeIdentityDirectory()
    from app.main import app

    app.dependency_overrides[get_identity_directory] = lambda: fake
    request.addfinalizer(
        lambda: app.dependency_overrides.pop(get_identity_directory, None)
    )
    return fake
