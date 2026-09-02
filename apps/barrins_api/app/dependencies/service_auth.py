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
from app.core.roles import Role, role_level
from app.dependencies.auth import verify_user_bearer


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

    Comparison is constant-time (`hmac.compare_digest`).

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
    x_scripture_token: Annotated[str | None, Header()] = None,
    bearer_token: Annotated[str | None, Depends(_optional_bearer_scheme)] = None,
) -> None:
    """Allow either the scripture service secret or an admin-level user.

    For routes read by both Barrin's Scripture's own sweep (service
    secret) and a human admin (identity token) — e.g. `GET
    /internal/scripture/db-metrics`. Tries the cheap header check first;
    falls back to `verify_user_bearer` (reused, not reimplemented, per
    Constitution §4.2) so a bad/expired token still 401s and an
    authenticated-but-non-admin user still 403s exactly like
    `require_role(Role.admin)` does.
    """
    if _scripture_token_valid(x_scripture_token):
        return
    if bearer_token is not None:
        user = await verify_user_bearer(bearer_token)
        if role_level(user.role) < Role.admin.level:
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


def _mtgjson_token_valid(token: str | None) -> bool:
    expected = settings.base.mtgjson_import_token
    return (
        expected is not None
        and token is not None
        and hmac.compare_digest(token, expected.get_secret_value())
    )


async def verify_mtgjson_or_admin(
    x_mtgjson_import_token: Annotated[str | None, Header()] = None,
    bearer_token: Annotated[str | None, Depends(_optional_bearer_scheme)] = None,
) -> None:
    """Allow either the scheduled-import service secret or an admin-level user.

    Mirrors `verify_scripture_or_admin` above (Constitution §4.2 — reused,
    not reimplemented): the systemd timer driving the daily MTGJSON
    refresh (`ops/my-server/roles/mtgjson_import_scheduler`) authenticates
    via `X-MTGJSON-Import-Token`; a human admin still triggers the same
    `POST /mtgjson/import` route via the existing identity-token flow,
    unchanged.
    """
    if _mtgjson_token_valid(x_mtgjson_import_token):
        return
    if bearer_token is not None:
        user = await verify_user_bearer(bearer_token)
        if role_level(user.role) < Role.admin.level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials.",
    )


MTGJSONImportOrAdmin = Annotated[None, Depends(verify_mtgjson_or_admin)]


def _karn_token_valid(token: str | None) -> bool:
    expected = settings.base.karn_ingest_token
    return (
        expected is not None
        and token is not None
        and hmac.compare_digest(token, expected.get_secret_value())
    )


async def verify_karn_token(
    x_karn_token: Annotated[str | None, Header()] = None,
) -> None:
    """Validate the `X-Karn-Token` header against the configured secret.

    Verbatim twin of `verify_scripture_token` (Constitution §4.2 — reused
    pattern, not reimplemented): the Karn Tablets clustering job
    (`apps/karn_tablets`) is another Barrin's-ecosystem service, not a
    logged-in user, and `POST /internal/karn/ingest` has no human caller,
    so there is no admin-JWT fallback (unlike `verify_mtgjson_or_admin`).

    Raises 503 if no token is configured (misconfiguration — the route can
    never be called successfully in that state) and 401 if the header is
    missing or doesn't match.
    """
    if settings.base.karn_ingest_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Karn Tablets ingestion is not configured.",
        )
    if not _karn_token_valid(x_karn_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing service credential.",
        )


KarnToken = Annotated[None, Depends(verify_karn_token)]
