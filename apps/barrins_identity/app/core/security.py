"""Cryptographic utilities: Argon2id hashing and RS256 JWT tokens.

The RSA private/public key pair is parsed and derived once, at module
load — not on every token decode or every JWKS request (platform.md §8,
§12).
"""

import base64
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.hazmat.primitives.asymmetric.rsa import (
    RSAPrivateKey,
    RSAPublicKey,
)
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.config import settings
from app.schemas.auth import ServiceTokenData, TokenData

# ---------------------------------------------------------------------------
# Password hashing (Argon2id via argon2-cffi)
# ---------------------------------------------------------------------------
# Cost parameters come from settings rather than argon2-cffi's library
# defaults, so they're documented and tunable per environment (platform.md §6).

_hasher = PasswordHasher(
    memory_cost=settings.base.argon2_memory_cost_kib,
    time_cost=settings.base.argon2_time_cost,
    parallelism=settings.base.argon2_parallelism,
)


def hash_password(plain: str) -> str:
    """Return the Argon2id hash of a plaintext secret.

    Used both for user passwords and service-account client secrets — same
    mechanism, same cost parameters (platform.md §7).
    """
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext secret against its Argon2id hash.

    Returns False for any invalid or malformed hash — never raises.
    Note: the argon2-cffi argument order is verify(hashed, plain).
    """
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if `hashed` was produced with weaker parameters than the
    hasher's current cost settings (e.g. after an ARGON2_* config bump)."""
    return _hasher.check_needs_rehash(hashed)


# Dummy hash precomputed at module load — used to equalize response time
# when the looked-up identifier (email / client_id) is unknown, preventing
# enumeration via timing (platform.md §8).
_DUMMY_HASH: str = _hasher.hash("dummy_value_for_timing_equalization")


def dummy_verify(plain: str) -> None:
    """Dummy call to equalize response time for an unknown identifier.

    Only swallows the expected argon2 exceptions.
    """
    try:
        _hasher.verify(_DUMMY_HASH, plain)
    except (VerificationError, InvalidHashError):
        pass


# ---------------------------------------------------------------------------
# RSA keypair — loaded once at module load (platform.md §8, §12)
# ---------------------------------------------------------------------------

_raw_key = load_pem_private_key(
    settings.base.jwt_private_key.get_secret_value().encode(), password=None
)
# Already guarded by BaseAppSettings.jwt_private_key_must_be_a_valid_rsa_key.
if not isinstance(_raw_key, RSAPrivateKey):  # pragma: no cover
    raise TypeError("JWT_PRIVATE_KEY must be an RSA private key (RS256).")

_PRIVATE_KEY: RSAPrivateKey = _raw_key
_PUBLIC_KEY: RSAPublicKey = _PRIVATE_KEY.public_key()
_KID: str = settings.base.jwt_kid
_ALGORITHM = "RS256"


def _b64url_uint(value: int) -> str:
    """Base64url-encode an integer without padding (RFC 7518 §6.3)."""
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def get_jwks() -> dict[str, Any]:
    """Return the JWKS document exposing the current public key.

    Format: RFC 7517. Built from the module-level public key — no key
    parsing happens per-request.
    """
    numbers = _PUBLIC_KEY.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": _ALGORITHM,
                "kid": _KID,
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }


# ---------------------------------------------------------------------------
# User tokens (human login)
# ---------------------------------------------------------------------------


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed user access token.

    `data` must contain `sub`, `role`, `email`, `tkv` (token_version).
    """
    to_encode = data.copy()
    to_encode["type"] = "access"
    to_encode["account_type"] = "user"
    to_encode["exp"] = datetime.now(UTC) + timedelta(
        minutes=settings.base.access_token_expire_minutes
    )
    return jwt.encode(
        to_encode, _PRIVATE_KEY, algorithm=_ALGORITHM, headers={"kid": _KID}
    )


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a user access token.

    Raises `jwt.PyJWTError` if the token is invalid, expired, or if the
    `type`/`account_type` claims don't match a user access token.
    """
    payload = jwt.decode(token, _PUBLIC_KEY, algorithms=[_ALGORITHM])
    if payload.get("type") != "access" or payload.get("account_type") != "user":
        raise jwt.InvalidTokenError("Invalid token type — expected: user access token.")
    return TokenData(
        sub=payload["sub"],
        role=payload["role"],
        email=payload["email"],
        token_version=payload["tkv"],
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a signed user refresh token (long-lived)."""
    to_encode = data.copy()
    to_encode["type"] = "refresh"
    to_encode["account_type"] = "user"
    to_encode["exp"] = datetime.now(UTC) + timedelta(
        days=settings.base.refresh_token_expire_days
    )
    return jwt.encode(
        to_encode, _PRIVATE_KEY, algorithm=_ALGORITHM, headers={"kid": _KID}
    )


def decode_refresh_token(token: str) -> TokenData:
    """Decode and validate a user refresh token.

    Raises `jwt.PyJWTError` if invalid, expired, or of the wrong type.
    """
    payload = jwt.decode(token, _PUBLIC_KEY, algorithms=[_ALGORITHM])
    if payload.get("type") != "refresh" or payload.get("account_type") != "user":
        raise jwt.InvalidTokenError(
            "Invalid token type — expected: user refresh token."
        )
    return TokenData(
        sub=payload["sub"],
        role=payload["role"],
        email=payload["email"],
        token_version=payload["tkv"],
    )


# ---------------------------------------------------------------------------
# Service-account tokens (client_credentials, machine-to-machine)
# ---------------------------------------------------------------------------


def create_service_token(data: dict[str, Any]) -> str:
    """Create a signed service-account token.

    `data` must contain `sub` (client_id), `scopes`, `tkv` (token_version).
    """
    to_encode = data.copy()
    to_encode["type"] = "service"
    to_encode["account_type"] = "service"
    to_encode["exp"] = datetime.now(UTC) + timedelta(
        minutes=settings.base.service_token_expire_minutes
    )
    return jwt.encode(
        to_encode, _PRIVATE_KEY, algorithm=_ALGORITHM, headers={"kid": _KID}
    )


def decode_service_token(token: str) -> ServiceTokenData:
    """Decode and validate a service-account token.

    Raises `jwt.PyJWTError` if invalid, expired, or of the wrong type —
    including a user token presented here (symmetric case of
    decode_access_token, tests.md §3).
    """
    payload = jwt.decode(token, _PUBLIC_KEY, algorithms=[_ALGORITHM])
    if payload.get("type") != "service" or payload.get("account_type") != "service":
        raise jwt.InvalidTokenError("Invalid token type — expected: service token.")
    return ServiceTokenData(
        sub=payload["sub"],
        scopes=payload["scopes"],
        token_version=payload["tkv"],
    )


# ---------------------------------------------------------------------------
# Service-account client_id / client_secret generation
# ---------------------------------------------------------------------------


def generate_client_id() -> str:
    """Generate a new service-account client_id (public identifier)."""
    return f"sa_{secrets.token_hex(8)}"


def generate_client_secret() -> str:
    """Generate a new service-account client_secret (shown once, plaintext)."""
    return secrets.token_urlsafe(32)
