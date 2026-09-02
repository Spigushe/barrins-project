"""HttpOnly refresh-token cookie for browser SPAs (ADR-18).

Opt-in per request: the caller sends `X-Client: web` and, when
`settings.base.refresh_cookie_enabled` is true, the refresh token is set
as an `HttpOnly` cookie instead of being returned in the response body.
`/auth/refresh` then reads it from the cookie and `/auth/logout` clears
it. Callers without the header keep the body-only behavior — this is what
`barrins_api` and other non-browser consumers rely on (§4.4).
"""

from fastapi import Request, Response

from app.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import TokenPair

REFRESH_COOKIE_NAME = "refresh_token"
# Scoped so the cookie is only ever sent to the auth endpoints.
REFRESH_COOKIE_PATH = "/api/v1/auth"
_WEB_CLIENT = "web"


def wants_cookie_mode(request: Request) -> bool:
    """True when the caller opted in (`X-Client: web`) and the feature is on."""
    return (
        settings.base.refresh_cookie_enabled
        and request.headers.get("x-client", "").lower() == _WEB_CLIENT
    )


def _max_age_seconds() -> int:
    return settings.base.refresh_token_expire_days * 24 * 60 * 60


def set_refresh_cookie(response: Response, token: str) -> None:
    """Write the refresh token as an HttpOnly cookie scoped to `/auth`."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=_max_age_seconds(),
        path=REFRESH_COOKIE_PATH,
        domain=settings.base.refresh_cookie_domain,
        secure=True,
        httponly=True,
        samesite=settings.base.refresh_cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Delete the refresh cookie — same name/path/domain/attrs as when set."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=settings.base.refresh_cookie_domain,
        secure=True,
        httponly=True,
        samesite=settings.base.refresh_cookie_samesite,
    )


def issue_tokens(
    request: Request, response: Response, claims: dict[str, str | int]
) -> TokenPair:
    """Mint an access + refresh pair for `claims`.

    Cookie mode (opt-in header + feature enabled): the refresh token goes
    into an HttpOnly cookie and the returned `TokenPair` carries no
    `refresh_token` (routes use `response_model_exclude_none=True`).
    Otherwise both tokens are returned in the body, exactly as before.
    """
    access = create_access_token(claims)
    refresh = create_refresh_token(claims)
    if wants_cookie_mode(request):
        set_refresh_cookie(response, refresh)
        return TokenPair(access_token=access, refresh_token=None)
    return TokenPair(access_token=access, refresh_token=refresh)
