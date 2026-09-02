"""Shared test helpers for identity-token authentication (ADR-20).

`barrins_api` no longer issues or stores users: it verifies `barrins_identity`
RS256 access tokens against that service's JWKS (`libs/identity_client`).
Tests therefore mint their own RS256 tokens with a throwaway keypair and
point the app's module-level `JWKSCache` at the matching public key — no
network, no `users` table, no `app.core.security`.

Usage::

    from tests.identity_auth import FakeUser, auth_headers

    async def test_something(client, regular_user: FakeUser):
        resp = await client.get(url, headers=auth_headers(regular_user))
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_KID = "test-kid"

# Every FakeUser registers itself here so a fake IdentityDirectory can
# resolve display labels for ids that only appear as `owner_id` / `user_id`
# on domain rows (team rosters, sharing banners) without per-test wiring.
_USER_REGISTRY: dict[uuid.UUID, FakeUser] = {}

# One throwaway signing key for the whole test process. 2048-bit keygen is
# a few tens of ms — cheap enough to do once at import and avoids threading
# a session fixture through every helper call.
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


@dataclass(frozen=True, slots=True)
class FakeUser:
    """A stand-in for an identity user — only what tests read off it.

    `id` is the token `sub`; `role` drives `require_role`; `username` /
    `display_name` are what an `IdentityDirectory` fake would return for
    this id (team rosters / sharing labels).
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = "user@example.test"
    role: str = "user"
    username: str = "user"
    display_name: str | None = None
    token_version: int = 0

    def __post_init__(self) -> None:
        _USER_REGISTRY[self.id] = self


def make_token(
    user: FakeUser | None = None,
    *,
    role: str = "user",
    sub: str | None = None,
    email: str | None = None,
    token_version: int = 0,
    account_type: str = "user",
    token_type: str = "access",  # noqa: S107 — JWT claim value, not a secret
    kid: str = TEST_KID,
    expires_in: timedelta = timedelta(minutes=10),
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Mint an RS256 token in `barrins_identity`'s claim shape."""
    if user is not None:
        sub = str(user.id)
        role = user.role
        email = user.email
        token_version = user.token_version
    payload: dict[str, Any] = {
        "sub": sub or str(uuid.uuid4()),
        "role": role,
        "email": email or "user@example.test",
        "tkv": token_version,
        "type": token_type,
        "account_type": account_type,
        "exp": datetime.now(UTC) + expires_in,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256", headers={"kid": kid})


def auth_headers(
    user: FakeUser | None = None, *, role: str = "user", **token_kwargs: Any
) -> dict[str, str]:
    """`Authorization: Bearer <token>` for `user` (or a fresh user of `role`)."""
    return {"Authorization": f"Bearer {make_token(user, role=role, **token_kwargs)}"}


def install_test_jwks() -> None:
    """Load the test public key into the app's process-wide `JWKSCache`.

    Idempotent; call it from an autouse fixture so every test sees a
    non-stale cache holding exactly `TEST_KID`.
    """
    from app.dependencies import auth as _auth

    cache = _auth._jwks_cache
    cache._keys = {TEST_KID: _PUBLIC_KEY}
    cache._fetched_at = time.monotonic()
    cache.cache_ttl_seconds = 10_000.0


class FakeIdentityDirectory:
    """In-process stand-in for `app.services.identity_directory.IdentityDirectory`.

    Resolves any id that belongs to a `FakeUser` created in the test run
    (via `_USER_REGISTRY`); unknown ids are simply omitted, exactly like
    the real batch endpoint. No network, no service token.
    """

    enabled = True

    def __init__(self, *, extra: dict[uuid.UUID, Any] | None = None) -> None:
        self._extra = extra or {}

    def _ref(self, user_id: uuid.UUID) -> Any | None:
        from app.services.identity_directory import UserRef

        if user_id in self._extra:
            return self._extra[user_id]
        user = _USER_REGISTRY.get(user_id)
        if user is None:
            return None
        return UserRef(username=user.username, display_name=user.display_name)

    async def lookup(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Any]:
        out: dict[uuid.UUID, Any] = {}
        for user_id in set(ids):
            ref = self._ref(user_id)
            if ref is not None:
                out[user_id] = ref
        return out

    async def label(self, user_id: uuid.UUID, *, fallback: str = "a kind user") -> str:
        ref = self._ref(user_id)
        return ref.label if ref is not None else fallback
