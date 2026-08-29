"""JWKS fetch + cache and a FastAPI verification dependency for Barrin's
Identity consumers.

Every backend that trusts tokens issued by `apps/barrins_identity` imports
this one package rather than copying the logic (ADR-17). It never calls
back to the identity service per request: it fetches the JWKS document
once, caches the public key(s) by `kid`, and verifies each token locally
against the cached key (integration.md §3).

The token format is owned by `apps/barrins_identity/app/core/security.py`:

    user access  : sub, role, email, tkv, type="access",  account_type="user",    exp
    user refresh : same shape,                             type="refresh"
    service      : sub, scopes, tkv,      type="service",  account_type="service", exp

A stateless verifier does **not** re-check `tkv` (the principal's
`token_version`) — only the identity service does, at `/auth/refresh`,
`/auth/logout` and inside its own dependencies. A consumer that needs
revocation to bite faster than the access-token TTL must call the identity
service itself.

NB: no `from __future__ import annotations` here — `make_verify_dependency`
builds a FastAPI dependency whose `Annotated[..., Depends(bearer)]` refers
to a closure-local (`bearer`); stringized annotations can't resolve it.
"""

import base64
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPublicKey,
    RSAPublicNumbers,
)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_ALGORITHM = "RS256"
AccountType = Literal["user", "service"]

__all__ = [
    "IdentityClientError",
    "InsufficientScope",
    "InvalidToken",
    "JWKSCache",
    "JWKSError",
    "VerifiedPrincipal",
    "make_verify_dependency",
    "verify_token",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class IdentityClientError(Exception):
    """Base class for every error raised by this package."""


class JWKSError(IdentityClientError):
    """The JWKS document could not be fetched or parsed."""


class InvalidToken(IdentityClientError):
    """The token is missing, malformed, expired, signed by an unknown key,
    or of the wrong `type` / `account_type`."""


class InsufficientScope(IdentityClientError):
    """The token is valid but lacks the scope the route requires."""

    def __init__(self, required_scope: str) -> None:
        super().__init__(f"Missing required scope: {required_scope!r}.")
        self.required_scope = required_scope


# ---------------------------------------------------------------------------
# Verified principal
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class VerifiedPrincipal:
    """The outcome of a successful token verification.

    `role` is set only for user tokens; `scopes` only for service tokens.
    `token_version` is surfaced for callers that choose to do their own
    stricter revocation check against the identity service — it is not
    validated here.
    """

    subject: str
    account_type: AccountType
    token_type: str
    token_version: int
    role: str | None = None
    email: str | None = None
    scopes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# JWKS cache
# ---------------------------------------------------------------------------
def _b64url_uint(value: str) -> int:
    """Decode a base64url-encoded unsigned integer (RFC 7518 §2)."""
    padding = "=" * (-len(value) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(value + padding), "big")


def _jwks_to_keys(document: dict[str, Any]) -> dict[str, RSAPublicKey]:
    """Turn an RFC 7517 JWKS document into a {kid: RSAPublicKey} mapping."""
    keys: dict[str, RSAPublicKey] = {}
    for entry in document.get("keys", []):
        if entry.get("kty") != "RSA":
            continue
        try:
            kid = entry["kid"]
            public_key = RSAPublicNumbers(
                e=_b64url_uint(entry["e"]), n=_b64url_uint(entry["n"])
            ).public_key()
        except (KeyError, ValueError, TypeError) as exc:
            raise JWKSError(f"Malformed JWKS entry: {exc}") from exc
        keys[kid] = public_key
    if not keys:
        raise JWKSError("JWKS document contained no usable RSA keys.")
    return keys


@dataclass
class JWKSCache:
    """Fetches and caches Barrin's Identity's public signing key(s).

    One instance per consumer process (create it at startup, reuse it for
    the lifetime of the app). Safe to share across coroutines on one event
    loop; not designed for use from multiple threads.
    """

    service_url: str
    cache_ttl_seconds: float = 3600.0
    http_client: httpx.AsyncClient | None = None
    _keys: dict[str, RSAPublicKey] = field(default_factory=dict, init=False, repr=False)
    _fetched_at: float | None = field(default=None, init=False, repr=False)

    @property
    def _jwks_url(self) -> str:
        return f"{self.service_url.rstrip('/')}/.well-known/jwks.json"

    def _is_stale(self) -> bool:
        return (
            self._fetched_at is None
            or (time.monotonic() - self._fetched_at) >= self.cache_ttl_seconds
        )

    async def _fetch(self) -> None:
        client = self.http_client or httpx.AsyncClient()
        try:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            document = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise JWKSError(
                f"Could not fetch JWKS from {self._jwks_url}: {exc}"
            ) from exc
        finally:
            if self.http_client is None:
                await client.aclose()
        self._keys = _jwks_to_keys(document)
        self._fetched_at = time.monotonic()

    async def get_key(self, kid: str) -> RSAPublicKey:
        """Return the public key for `kid`, refreshing the cache if needed.

        Refreshes on a stale cache, and once more on a cache miss (a key
        rotation publishes the new `kid` before the private key switches,
        so an unknown `kid` usually just means "refetch").
        """
        if self._is_stale():
            await self._fetch()
        if kid not in self._keys:
            await self._fetch()
        try:
            return self._keys[kid]
        except KeyError as exc:
            raise InvalidToken(f"Unknown signing key id: {kid!r}.") from exc


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
_DEFAULT_TOKEN_TYPE: dict[AccountType, str] = {"user": "access", "service": "service"}


async def verify_token(
    token: str,
    cache: JWKSCache,
    *,
    expected_account_type: AccountType,
    required_scope: str | None = None,
    expected_token_type: str | None = None,
) -> VerifiedPrincipal:
    """Verify a Barrin's Identity token locally against the cached JWKS.

    Raises:
        InvalidToken: missing/malformed/expired token, unknown signing
            key, or a `type` / `account_type` mismatch.
        InsufficientScope: valid token whose `scopes` omit `required_scope`.
        JWKSError: the JWKS document itself could not be fetched/parsed.
    """
    if expected_token_type is None:
        expected_token_type = _DEFAULT_TOKEN_TYPE[expected_account_type]

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidToken(f"Unreadable token header: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        raise InvalidToken("Token header is missing the 'kid' claim.")

    public_key = await cache.get_key(kid)

    try:
        payload: dict[str, Any] = jwt.decode(token, public_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc

    if payload.get("account_type") != expected_account_type:
        raise InvalidToken(
            f"Wrong account_type: expected {expected_account_type!r}, "
            f"got {payload.get('account_type')!r}."
        )
    if payload.get("type") != expected_token_type:
        raise InvalidToken(
            f"Wrong token type: expected {expected_token_type!r}, "
            f"got {payload.get('type')!r}."
        )

    try:
        subject = str(payload["sub"])
        token_version = int(payload["tkv"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidToken(f"Token is missing a required claim: {exc}") from exc

    scopes = tuple(payload.get("scopes", ()))
    if required_scope is not None and required_scope not in scopes:
        raise InsufficientScope(required_scope)

    return VerifiedPrincipal(
        subject=subject,
        account_type=expected_account_type,
        token_type=expected_token_type,
        token_version=token_version,
        role=payload.get("role"),
        email=payload.get("email"),
        scopes=scopes,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def make_verify_dependency(
    cache: JWKSCache,
    *,
    expected_account_type: AccountType,
    required_scope: str | None = None,
    expected_token_type: str | None = None,
) -> Callable[..., Awaitable[VerifiedPrincipal]]:
    """Build a FastAPI dependency that verifies the bearer token and
    returns a :class:`VerifiedPrincipal`.

    `401` (with ``WWW-Authenticate: Bearer``) for a missing/invalid token
    or a `type` / `account_type` mismatch; `403` when a `required_scope`
    is not present. Pass the dependency *by value*, never referenced by a
    string name (platform.md §12).
    """
    # auto_error=False so a missing/blank header yields None here and this
    # function returns a uniform 401 — HTTPBearer's own auto-error is a 403.
    bearer = HTTPBearer(auto_error=False)

    async def _verify(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(bearer)
        ] = None,
    ) -> VerifiedPrincipal:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            return await verify_token(
                credentials.credentials,
                cache,
                expected_account_type=expected_account_type,
                required_scope=required_scope,
                expected_token_type=expected_token_type,
            )
        except InsufficientScope as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        except IdentityClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    return _verify
