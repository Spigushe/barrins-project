"""JWKS endpoint (platform.md §8) — public key discovery for consumers."""

from typing import Any

from fastapi import APIRouter

from app.core.security import get_jwks

router = APIRouter()


@router.get("/.well-known/jwks.json")
async def jwks() -> dict[str, Any]:
    """Return the current RSA public key(s) as a JWKS document (RFC 7517).

    Built from the module-level public key, derived once at process
    startup — no key parsing happens per request.
    """
    return get_jwks()
