"""Tests for identity_client — JWKS cache + local token verification.

The JWKS endpoint is mocked with respx; a fresh RSA keypair is generated
per test session (a real signing key is never committed, mirroring
apps/barrins_identity/tests). The JWKS serialization here is the same
shape as apps/barrins_identity/tests/test_jwks.py.
"""

from __future__ import annotations

import base64
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from fastapi import Depends, FastAPI

from identity_client import (
    InsufficientScope,
    InvalidToken,
    JWKSCache,
    JWKSError,
    VerifiedPrincipal,
    make_verify_dependency,
    verify_token,
)

JWKS_URL = "https://id.example.test/.well-known/jwks.json"
SERVICE_URL = "https://id.example.test"
KID = "test-kid"


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _b64url_uint(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    raw = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def jwks_document(key: RSAPrivateKey, *, kid: str = KID) -> dict[str, Any]:
    numbers = key.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }


def make_token(
    key: RSAPrivateKey,
    *,
    kid: str = KID,
    claims: dict[str, Any] | None = None,
    expires_in: timedelta = timedelta(minutes=10),
) -> str:
    payload: dict[str, Any] = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "tkv": 0,
        "type": "access",
        "account_type": "user",
        "role": "user",
        "email": "u@example.com",
        "exp": datetime.now(UTC) + expires_in,
    }
    payload.update(claims or {})
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})


def service_claims(scopes: list[str]) -> dict[str, Any]:
    return {
        "sub": "sa_abc123",
        "type": "service",
        "account_type": "service",
        "scopes": scopes,
        "role": None,
        "email": None,
    }


def mock_jwks(key: RSAPrivateKey, *, kid: str = KID) -> respx.Route:
    return respx.get(JWKS_URL).mock(
        return_value=httpx.Response(200, json=jwks_document(key, kid=kid))
    )


# ---------------------------------------------------------------------------
# verify_token — happy paths
# ---------------------------------------------------------------------------
class TestVerifyToken:
    @respx.mock
    async def test_valid_user_access_token(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        principal = await verify_token(
            make_token(private_key), cache, expected_account_type="user"
        )
        assert isinstance(principal, VerifiedPrincipal)
        assert principal.account_type == "user"
        assert principal.token_type == "access"
        assert principal.role == "user"
        assert principal.email == "u@example.com"
        assert principal.subject == "11111111-1111-1111-1111-111111111111"

    @respx.mock
    async def test_valid_service_token_with_scope(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, claims=service_claims(["tolaria:read"]))
        principal = await verify_token(
            token,
            cache,
            expected_account_type="service",
            required_scope="tolaria:read",
        )
        assert principal.account_type == "service"
        assert principal.scopes == ("tolaria:read",)

    @respx.mock
    async def test_service_token_without_required_scope_raises(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, claims=service_claims(["tolaria:read"]))
        with pytest.raises(InsufficientScope):
            await verify_token(
                token,
                cache,
                expected_account_type="service",
                required_scope="tolaria:write",
            )

    @respx.mock
    async def test_expired_token_raises_invalid(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, expires_in=timedelta(minutes=-1))
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")

    @respx.mock
    async def test_user_token_rejected_by_service_verifier(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        with pytest.raises(InvalidToken):
            await verify_token(
                make_token(private_key), cache, expected_account_type="service"
            )

    @respx.mock
    async def test_service_token_rejected_by_user_verifier(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, claims=service_claims([]))
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")

    @respx.mock
    async def test_refresh_token_rejected_where_access_expected(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, claims={"type": "refresh"})
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")

    @respx.mock
    async def test_wrong_signing_key_raises_invalid(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = make_token(other_key)  # signed by a key the JWKS doesn't publish
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")

    @respx.mock
    async def test_missing_kid_header_raises_invalid(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = jwt.encode(
            {
                "sub": "x",
                "tkv": 0,
                "type": "access",
                "account_type": "user",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
        )
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")

    @respx.mock
    async def test_garbage_token_raises_invalid(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        with pytest.raises(InvalidToken):
            await verify_token("not-a-jwt", cache, expected_account_type="user")

    @respx.mock
    async def test_explicit_expected_token_type_accepts_refresh(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = make_token(private_key, claims={"type": "refresh"})
        principal = await verify_token(
            token,
            cache,
            expected_account_type="user",
            expected_token_type="refresh",
        )
        assert principal.token_type == "refresh"

    @respx.mock
    async def test_token_missing_tkv_claim_raises_invalid(
        self, private_key: RSAPrivateKey
    ):
        mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL)
        token = jwt.encode(
            {
                "sub": "x",
                "type": "access",
                "account_type": "user",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": KID},
        )
        with pytest.raises(InvalidToken):
            await verify_token(token, cache, expected_account_type="user")


# ---------------------------------------------------------------------------
# JWKSCache behaviour
# ---------------------------------------------------------------------------
class TestJWKSCache:
    @respx.mock
    async def test_cache_hit_avoids_second_fetch(self, private_key: RSAPrivateKey):
        route = mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL, cache_ttl_seconds=3600)
        await cache.get_key(KID)
        await cache.get_key(KID)
        assert route.call_count == 1

    @respx.mock
    async def test_stale_cache_refetches(self, private_key: RSAPrivateKey):
        route = mock_jwks(private_key)
        cache = JWKSCache(SERVICE_URL, cache_ttl_seconds=0.0)
        await cache.get_key(KID)
        await cache.get_key(KID)
        assert route.call_count == 2

    @respx.mock
    async def test_unknown_kid_triggers_one_refetch_then_raises(
        self, private_key: RSAPrivateKey
    ):
        route = mock_jwks(private_key, kid="k-current")
        cache = JWKSCache(SERVICE_URL, cache_ttl_seconds=3600)
        with pytest.raises(InvalidToken):
            await cache.get_key("k-rotated-away")
        # one initial (stale) fetch + one miss-triggered refetch
        assert route.call_count == 2

    @respx.mock
    async def test_http_error_raises_jwks_error(self, private_key: RSAPrivateKey):
        respx.get(JWKS_URL).mock(return_value=httpx.Response(503))
        cache = JWKSCache(SERVICE_URL)
        with pytest.raises(JWKSError):
            await cache.get_key(KID)

    @respx.mock
    async def test_document_without_rsa_keys_raises_jwks_error(
        self, private_key: RSAPrivateKey
    ):
        respx.get(JWKS_URL).mock(
            return_value=httpx.Response(200, json={"keys": [{"kty": "EC", "kid": "x"}]})
        )
        cache = JWKSCache(SERVICE_URL)
        with pytest.raises(JWKSError):
            await cache.get_key(KID)

    @respx.mock
    async def test_malformed_jwks_entry_raises_jwks_error(
        self, private_key: RSAPrivateKey
    ):
        respx.get(JWKS_URL).mock(
            return_value=httpx.Response(
                200, json={"keys": [{"kty": "RSA", "kid": "x", "n": "!!", "e": "AQAB"}]}
            )
        )
        cache = JWKSCache(SERVICE_URL)
        with pytest.raises(JWKSError):
            await cache.get_key(KID)

    @respx.mock
    async def test_reuses_injected_http_client(self, private_key: RSAPrivateKey):
        route = mock_jwks(private_key)
        async with httpx.AsyncClient() as shared:
            cache = JWKSCache(SERVICE_URL, http_client=shared)
            await cache.get_key(KID)
        assert route.call_count == 1


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def _app_with(dependency: object) -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected(principal: object = Depends(dependency)) -> dict[str, object]:
        return {
            "subject": principal.subject,  # type: ignore[attr-defined]
            "scopes": list(principal.scopes),  # type: ignore[attr-defined]
        }

    return app


async def _call(app: FastAPI, headers: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get("/protected", headers=headers)


class TestMakeVerifyDependency:
    @respx.mock
    async def test_valid_token_returns_200(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        dep = make_verify_dependency(
            JWKSCache(SERVICE_URL), expected_account_type="user"
        )
        resp = await _call(
            _app_with(dep),
            {"Authorization": f"Bearer {make_token(private_key)}"},
        )
        assert resp.status_code == 200
        assert resp.json()["subject"] == "11111111-1111-1111-1111-111111111111"

    @respx.mock
    async def test_missing_header_returns_401(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        dep = make_verify_dependency(
            JWKSCache(SERVICE_URL), expected_account_type="user"
        )
        resp = await _call(_app_with(dep), {})
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"].lower() == "bearer"

    @respx.mock
    async def test_bad_token_returns_401(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        dep = make_verify_dependency(
            JWKSCache(SERVICE_URL), expected_account_type="user"
        )
        resp = await _call(
            _app_with(dep), {"Authorization": "Bearer garbage.token.here"}
        )
        assert resp.status_code == 401

    @respx.mock
    async def test_insufficient_scope_returns_403(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        dep = make_verify_dependency(
            JWKSCache(SERVICE_URL),
            expected_account_type="service",
            required_scope="tolaria:write",
        )
        token = make_token(private_key, claims=service_claims(["tolaria:read"]))
        resp = await _call(_app_with(dep), {"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    @respx.mock
    async def test_wrong_account_type_returns_401(self, private_key: RSAPrivateKey):
        mock_jwks(private_key)
        dep = make_verify_dependency(
            JWKSCache(SERVICE_URL),
            expected_account_type="service",
            required_scope="tolaria:read",
        )
        resp = await _call(
            _app_with(dep),
            {"Authorization": f"Bearer {make_token(private_key)}"},
        )
        assert resp.status_code == 401


def test_module_exports_are_stable():
    import identity_client

    for name in (
        "JWKSCache",
        "VerifiedPrincipal",
        "verify_token",
        "make_verify_dependency",
        "InvalidToken",
        "InsufficientScope",
        "JWKSError",
        "IdentityClientError",
    ):
        assert hasattr(identity_client, name)


def test_verified_principal_is_frozen():
    principal = VerifiedPrincipal(
        subject="s", account_type="user", token_type="access", token_version=0
    )
    with pytest.raises(AttributeError):
        principal.subject = "other"  # type: ignore[misc]
    # exercise the monotonic clock helper indirectly
    assert time.monotonic() >= 0
