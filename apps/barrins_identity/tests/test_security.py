"""Tests for app/core/security.py — Argon2id hashing and RS256 JWT tokens."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_service_token,
    decode_access_token,
    decode_refresh_token,
    decode_service_token,
    dummy_verify,
    generate_client_id,
    generate_client_secret,
    generate_verification_code,
    get_jwks,
    hash_password,
    hash_verification_code,
    needs_rehash,
    verify_password,
    verify_verification_code,
)

# ===========================================================================
# Password hashing
# ===========================================================================


class TestHashPassword:
    def test_hash_is_not_plain(self):
        h = hash_password("MyPassword#1")
        assert h != "MyPassword#1"

    def test_two_hashes_differ(self):
        assert hash_password("Same#Pass1") != hash_password("Same#Pass1")


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("Correct#Pass1")
        assert verify_password("Correct#Pass1", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("Correct#Pass1")
        assert verify_password("WrongPass#1", h) is False

    def test_invalid_hash_returns_false(self):
        assert verify_password("any_password", "not_a_valid_hash") is False

    def test_empty_string_hash_returns_false(self):
        assert verify_password("any_password", "") is False


class TestNeedsRehash:
    def test_fresh_hash_does_not_need_rehash(self):
        h = hash_password("Correct#Pass1")
        assert needs_rehash(h) is False

    def test_malformed_hash_needs_rehash(self):
        # argon2-cffi treats a foreign/garbage hash as needing a rehash
        # rather than raising.
        assert needs_rehash("$argon2id$v=19$m=8,t=1,p=1$c2FsdA$aGFzaA") is True


class TestDummyVerify:
    def test_does_not_raise_on_wrong_password(self):
        dummy_verify("wrong_password")

    def test_does_not_raise_on_empty_string(self):
        dummy_verify("")


# ===========================================================================
# JWT — user tokens
# ===========================================================================


def _user_claims() -> dict[str, str | int]:
    return {
        "sub": str(uuid.uuid4()),
        "role": "user",
        "email": "u@example.com",
        "tkv": 0,
    }


class TestCreateDecodeAccessToken:
    def test_roundtrip(self):
        token = create_access_token(_user_claims())
        data = decode_access_token(token)
        assert data.sub is not None
        assert data.role == "user"
        assert data.token_version == 0

    def test_header_contains_kid_and_alg(self):
        token = create_access_token(_user_claims())
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256"
        assert header["kid"] == "test-kid"

    def test_decode_refresh_token_as_access_raises(self):
        refresh = create_refresh_token(_user_claims())
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(refresh)

    def test_decode_service_token_as_access_raises(self):
        service = create_service_token(
            {"sub": "sa_abc", "scopes": ["x:read"], "tkv": 0}
        )
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(service)

    def test_decode_expired_token_raises(self):
        claims = _user_claims()
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        claims["type"] = "access"
        claims["account_type"] = "user"
        from app.core import security as sec

        token = jwt.encode(
            claims, sec._PRIVATE_KEY, algorithm="RS256", headers={"kid": sec._KID}
        )
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(token)

    def test_decode_bad_token_raises(self):
        with pytest.raises(jwt.PyJWTError):
            decode_access_token("not.a.token")


class TestCreateDecodeRefreshToken:
    def test_roundtrip(self):
        claims = _user_claims()
        claims["role"] = "admin"
        claims["tkv"] = 2
        token = create_refresh_token(claims)
        data = decode_refresh_token(token)
        assert data.role == "admin"
        assert data.token_version == 2

    def test_decode_access_token_as_refresh_raises(self):
        access = create_access_token(_user_claims())
        with pytest.raises(jwt.PyJWTError):
            decode_refresh_token(access)


# ===========================================================================
# JWT — service tokens
# ===========================================================================


class TestCreateDecodeServiceToken:
    def _claims(self) -> dict[str, object]:
        return {"sub": "sa_deadbeef", "scopes": ["tolaria:read"], "tkv": 0}

    def test_roundtrip(self):
        token = create_service_token(self._claims())
        data = decode_service_token(token)
        assert data.sub == "sa_deadbeef"
        assert data.scopes == ["tolaria:read"]
        assert data.token_version == 0

    def test_decode_user_access_token_as_service_raises(self):
        user_token = create_access_token(_user_claims())
        with pytest.raises(jwt.PyJWTError):
            decode_service_token(user_token)

    def test_decode_user_refresh_token_as_service_raises(self):
        user_token = create_refresh_token(_user_claims())
        with pytest.raises(jwt.PyJWTError):
            decode_service_token(user_token)


# ===========================================================================
# Client id / secret generation
# ===========================================================================


class TestGenerateServiceAccountCredentials:
    def test_client_id_has_expected_prefix(self):
        assert generate_client_id().startswith("sa_")

    def test_client_ids_are_unique(self):
        assert generate_client_id() != generate_client_id()

    def test_client_secrets_are_unique(self):
        assert generate_client_secret() != generate_client_secret()


# ===========================================================================
# JWKS
# ===========================================================================


class TestGetJwks:
    def test_returns_single_key(self):
        jwks = get_jwks()
        assert len(jwks["keys"]) == 1

    def test_key_fields(self):
        key = get_jwks()["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == "test-kid"
        assert isinstance(key["n"], str)
        assert isinstance(key["e"], str)


# ===========================================================================
# Email verification code
# ===========================================================================


class TestVerificationCode:
    def test_generate_returns_six_digits(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_is_zero_padded(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("app.core.security.secrets.randbelow", lambda _n: 42)
        assert generate_verification_code() == "000042"

    def test_hash_roundtrip_succeeds(self):
        user_id = uuid.uuid4()
        code = "123456"
        stored = hash_verification_code(code, user_id)
        assert verify_verification_code(code, user_id, stored)

    def test_hash_differs_per_user(self):
        code = "123456"
        assert hash_verification_code(code, uuid.uuid4()) != hash_verification_code(
            code, uuid.uuid4()
        )

    def test_verify_rejects_wrong_code(self):
        user_id = uuid.uuid4()
        stored = hash_verification_code("123456", user_id)
        assert verify_verification_code("654321", user_id, stored) is False

    def test_verify_rejects_wrong_user(self):
        code = "123456"
        stored = hash_verification_code(code, uuid.uuid4())
        assert verify_verification_code(code, uuid.uuid4(), stored) is False
