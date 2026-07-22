"""Tests for GET /.well-known/jwks.json — format and key consistency."""

import base64

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from httpx import AsyncClient

from app.core.security import _PUBLIC_KEY, create_access_token


def _b64url_decode_uint(value: str) -> int:
    padding = "=" * (-len(value) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(value + padding), "big")


class TestJwksEndpoint:
    async def test_returns_200_and_expected_shape(self, client: AsyncClient):
        resp = await client.get("/.well-known/jwks.json")
        assert resp.status_code == 200
        body = resp.json()
        assert "keys" in body
        assert len(body["keys"]) == 1
        key = body["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == "test-kid"

    async def test_public_key_matches_signing_key(self, client: AsyncClient):
        """The JWKS-published key must be able to verify a token signed by
        the same process (platform.md §8 — public key derived once)."""
        resp = await client.get("/.well-known/jwks.json")
        key = resp.json()["keys"][0]

        n = _b64url_decode_uint(key["n"])
        e = _b64url_decode_uint(key["e"])
        published_public_key = RSAPublicNumbers(e, n).public_key()

        expected_numbers = _PUBLIC_KEY.public_numbers()
        assert published_public_key.public_numbers() == expected_numbers

        token = create_access_token(
            {
                "sub": "x",
                "role": "user",
                "email": "x@example.com",
                "tkv": 0,
            }
        )
        payload = jwt.decode(
            token,
            published_public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )
        assert payload["sub"] == "x"
