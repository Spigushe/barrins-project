"""Service-to-service authentication for internal, backend-only routes.

Sibling to `app/dependencies/auth.py`'s user-facing JWT auth: the daily
MTGJSON-refresh systemd timer calls `POST /mtgjson/import` without a
logged-in user, so it's gated by a static shared secret alongside the
existing admin-JWT path, instead of requiring a human session.
"""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.database.session import DatabaseSession
from app.dependencies.auth import get_current_user
from app.models.user import UserRole

# auto_error=False: a missing Authorization header must fall through to
# the X-MTGJSON-Import-Token check below, not immediately 401.
_optional_bearer_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token", auto_error=False
)


def _mtgjson_token_valid(token: str | None) -> bool:
    expected = settings.base.mtgjson_import_token
    return (
        expected is not None
        and token is not None
        and hmac.compare_digest(token, expected.get_secret_value())
    )


async def verify_mtgjson_or_admin(
    session: DatabaseSession,
    x_mtgjson_import_token: Annotated[str | None, Header()] = None,
    bearer_token: Annotated[str | None, Depends(_optional_bearer_scheme)] = None,
) -> None:
    """Allow either the scheduled-import service secret or an admin-level user.

    The systemd timer driving the daily MTGJSON refresh
    (`ops/my-server/roles/mtgjson_import_scheduler`) authenticates via
    `X-MTGJSON-Import-Token`; a human admin still triggers the same
    `POST /mtgjson/import` route via the existing JWT flow, unchanged.
    """
    if _mtgjson_token_valid(x_mtgjson_import_token):
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


MTGJSONImportOrAdmin = Annotated[None, Depends(verify_mtgjson_or_admin)]
