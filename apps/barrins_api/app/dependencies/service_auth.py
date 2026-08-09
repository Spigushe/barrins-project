"""Service-to-service authentication for internal, backend-only routes.

Sibling to `app/dependencies/auth.py`'s user-facing JWT auth: an internal
route like `POST /internal/scripture/ingest` (T3) is called by another
Barrin's-ecosystem service (Barrin's Scripture's sweep), not a logged-in
user, so it's gated by a static shared secret instead of a JWT.
"""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.database.session import DatabaseSession
from app.dependencies.auth import get_current_user
from app.models.user import UserRole


def _scripture_token_valid(token: str | None) -> bool:
    expected = settings.base.scripture_ingest_token
    return (
        expected is not None
        and token is not None
        and hmac.compare_digest(token, expected.get_secret_value())
    )


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
    if settings.base.scripture_ingest_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scripture ingestion is not configured.",
        )
    if not _scripture_token_valid(x_scripture_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service credential.",
        )


ScriptureToken = Annotated[None, Depends(verify_scripture_token)]

# auto_error=False: unlike `app.dependencies.auth.oauth2_scheme`, a missing
# Authorization header here must fall through to the X-Scripture-Token
# check below, not immediately 401.
_optional_bearer_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token", auto_error=False
)


async def verify_scripture_or_admin(
    session: DatabaseSession,
    x_scripture_token: Annotated[str | None, Header()] = None,
    bearer_token: Annotated[str | None, Depends(_optional_bearer_scheme)] = None,
) -> None:
    """Allow either the scripture service secret or an admin-level user.

    For routes read by both Barrin's Scripture's own sweep (service
    secret) and a human admin (JWT) — e.g. `GET
    /internal/scripture/db-metrics`. Tries the cheap header check first;
    falls back to `get_current_user` (reused, not reimplemented, per
    Constitution §4.2) so a bad/expired JWT still 401s and an
    authenticated-but-non-admin user still 403s exactly like
    `require_role(UserRole.admin)` does.
    """
    if _scripture_token_valid(x_scripture_token):
        return
    if bearer_token is not None:
        user = await get_current_user(bearer_token, session)
        if user.role.level < UserRole.admin.level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials.",
    )


ScriptureOrAdmin = Annotated[None, Depends(verify_scripture_or_admin)]
