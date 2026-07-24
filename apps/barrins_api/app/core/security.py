"""Cryptographic utilities: Argon2id hashing and HS256 JWT tokens."""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt

from app.config import settings
from app.schemas.auth import TokenData

# ---------------------------------------------------------------------------
# Password hashing (Argon2id via argon2-cffi)
# ---------------------------------------------------------------------------

# Argon2id with the RFC 9106 LOW_MEMORY defaults (argon2-cffi >= 21.2.0):
# memory_cost=65536 KiB (64 MiB), time_cost=3, parallelism=4.
_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Return the Argon2id hash of the plaintext password."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its Argon2id hash.

    Returns False for any invalid or malformed hash — never raises.
    Note: the argon2-cffi argument order is verify(hashed, plain) — the
    reverse of the old passlib convention.
    """
    try:
        return _hasher.verify(hashed, plain)
    except VerificationError, InvalidHashError:
        # VerifyMismatchError inherits from VerificationError — covered implicitly.
        return False


# Dummy hash precomputed at module startup.
# Used in POST /auth/token to equalize response time when the email is
# unknown (prevents account enumeration via timing).
_DUMMY_HASH: str = _hasher.hash("dummy_value_for_timing_equalization")


def dummy_verify(plain: str) -> None:
    """Dummy call to equalize response time for an unknown user.

    Only swallows the expected argon2 exceptions.
    System exceptions (MemoryError, KeyboardInterrupt...) propagate normally.
    """
    try:
        _hasher.verify(_DUMMY_HASH, plain)
    except VerificationError, InvalidHashError:
        pass


# ---------------------------------------------------------------------------
# Tokens JWT HS256 (python-jose)
# ---------------------------------------------------------------------------


def create_access_token(data: dict[Any, Any]) -> str:
    """Create a signed access token JWT.

    `data` must contain the `"tkv"` key (the user's token_version).
    The `type: "access"` claim prevents a refresh token from being used
    in its place.
    """
    to_encode = data.copy()
    to_encode["type"] = "access"
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.base.access_token_expire_minutes
    )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.base.secret_key,
        algorithm=settings.base.algorithm,
    )


def decode_access_token(token: str) -> TokenData:
    """Decode and validate an access token.

    Raises `JWTError` if the token is invalid, expired, or if the `type`
    claim is not "access".
    """
    payload = jwt.decode(
        token,
        settings.base.secret_key,
        algorithms=[settings.base.algorithm],
    )
    if payload.get("type") != "access":
        raise JWTError("Invalid token type — expected: access")
    return TokenData(
        sub=payload["sub"],
        role=payload["role"],
        email=payload["email"],
        token_version=payload["tkv"],
    )


def create_refresh_token(data: dict[Any, Any]) -> str:
    """Create a signed refresh token JWT (long-lived).

    `data` must contain `"tkv"` (token_version).
    The `type: "refresh"` claim prevents it from being used as an access token.
    """
    to_encode = data.copy()
    to_encode["type"] = "refresh"
    expire = datetime.now(UTC) + timedelta(days=settings.base.refresh_token_expire_days)
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.base.secret_key,
        algorithm=settings.base.algorithm,
    )


def decode_refresh_token(token: str) -> TokenData:
    """Decode and validate a refresh token.

    Raises `JWTError` if the token is invalid, expired, or if the `type`
    claim is not "refresh".
    """
    payload = jwt.decode(
        token,
        settings.base.secret_key,
        algorithms=[settings.base.algorithm],
    )
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type — expected: refresh")
    return TokenData(
        sub=payload["sub"],
        role=payload["role"],
        email=payload["email"],
        token_version=payload["tkv"],
    )


# ---------------------------------------------------------------------------
# Email verification code (self-registration)
# ---------------------------------------------------------------------------
# A 6-digit OTP doesn't need Argon2: the protection comes from the throttle
# (attempts/cooldown, cf. app/api/v1/routers/auth.py), not the hash cost —
# see docs/signup_email_verification/00_plan_general.md, Option B/C.


def generate_verification_code() -> str:
    """Generate a 6-digit verification code (CSPRNG, zero-padded)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str, user_id: uuid.UUID) -> str:
    """Hash a verification code, bound to the user.

    The binding to `user_id` prevents a hash from being reused across accounts.
    """
    return hashlib.sha256(f"{code}:{user_id}".encode()).hexdigest()


def verify_verification_code(code: str, user_id: uuid.UUID, code_hash: str) -> bool:
    """Compare a plaintext code to its hash in constant time."""
    return hmac.compare_digest(hash_verification_code(code, user_id), code_hash)
