"""Service-to-service authentication for internal, backend-only routes.

Sibling to `app/dependencies/auth.py`'s user-facing JWT auth: an internal
route like `POST /internal/scripture/ingest` (T3) is called by another
Barrin's-ecosystem service (Barrin's Scripture's sweep), not a logged-in
user, so it's gated by a static shared secret instead of a JWT.
"""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import settings


async def verify_scripture_token(
    x_scripture_token: Annotated[str | None, Header()] = None,
) -> None:
    """Validate the `X-Scripture-Token` header against the configured secret.

    Comparison is constant-time (`hmac.compare_digest`), matching the style
    already used for email verification codes
    (`app/core/security.py::verify_verification_code`).

    Raises 503 if no token is configured (misconfiguration, not an auth
    failure — the route can never be called successfully in that state) and
    401 if the header is missing or doesn't match.
    """
    expected = settings.base.scripture_ingest_token
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scripture ingestion is not configured.",
        )
    if x_scripture_token is None or not hmac.compare_digest(
        x_scripture_token, expected.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service credential.",
        )


ScriptureToken = Annotated[None, Depends(verify_scripture_token)]
