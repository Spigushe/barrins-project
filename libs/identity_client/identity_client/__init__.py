"""Shared JWKS verification client for Barrin's Identity consumers.

See `identity_client.client` for the implementation and
`docs/content/back/barrins_identity/integration.md` §3 for the contract.
"""

from identity_client.client import (
    IdentityClientError,
    InsufficientScope,
    InvalidToken,
    JWKSCache,
    JWKSError,
    VerifiedPrincipal,
    make_verify_dependency,
    verify_token,
)

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
