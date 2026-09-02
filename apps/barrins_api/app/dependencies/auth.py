"""FastAPI dependencies for identity-token authentication and authorization.

Since the identity cutover (ADR-20) `barrins_api` does not manage users: it
verifies the bearer access token issued by `apps/barrins_identity` locally
against that service's JWKS (`libs/identity_client`, ADR-17) and trusts the
`sub` / `role` claims. There is no database lookup and no local `users`
table.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from identity_client import (
    IdentityClientError,
    JWKSCache,
    VerifiedPrincipal,
    make_verify_dependency,
    verify_token,
)

from app.config import settings
from app.core.roles import Role, role_level

# One JWKS cache for the process lifetime (fetches + caches the identity
# service's public signing keys; never calls back per request).
_jwks_cache = JWKSCache(
    settings.base.identity_service_url,
    cache_ttl_seconds=settings.base.identity_jwks_cache_ttl_seconds,
)

_verify_user_token = make_verify_dependency(_jwks_cache, expected_account_type="user")


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The caller behind a verified identity user token.

    Only the fields `barrins_api` routes actually use — `id` (the identity
    user UUID, used as the owner key on domain rows) and `role` (for
    `require_role`). `email` is informational, never used for authorization.
    """

    id: uuid.UUID
    role: str
    email: str | None = None


_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _principal_to_user(principal: VerifiedPrincipal) -> AuthenticatedUser:
    try:
        user_id = uuid.UUID(principal.subject)
    except ValueError as err:
        raise _CREDENTIALS_EXC from err
    return AuthenticatedUser(
        id=user_id,
        role=principal.role or Role.user.value,
        email=principal.email,
    )


async def get_current_user(
    principal: Annotated[VerifiedPrincipal, Depends(_verify_user_token)],
) -> AuthenticatedUser:
    """Return the authenticated caller from a verified identity token.

    `identity_client` has already raised `401` for a missing / malformed /
    expired token or a `type` / `account_type` mismatch. The only extra
    check here is that `sub` is a UUID.
    """
    return _principal_to_user(principal)


async def verify_user_bearer(token: str) -> AuthenticatedUser:
    """Verify a raw bearer-token string — for non-`Depends` callers.

    Used by `app/dependencies/service_auth.py`, where the identity token is
    one of several accepted credentials and can't be a route dependency.
    Raises `401` for any invalid token.
    """
    try:
        principal = await verify_token(token, _jwks_cache, expected_account_type="user")
    except IdentityClientError as err:
        raise _CREDENTIALS_EXC from err
    return _principal_to_user(principal)


def require_role(min_role: Role) -> Callable[..., Awaitable[AuthenticatedUser]]:
    """Dependency factory: requires the caller's role level >= `min_role`.

    Roles are hierarchical (user < moderator < ml_developer < admin), so an
    admin satisfies `require_role(Role.ml_developer)`.

    Example:
        @router.delete("/{id}", dependencies=[Depends(require_role(Role.admin))])
    """

    async def _check(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if role_level(current_user.role) < min_role.level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants.",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
ModeratorUser = Annotated[AuthenticatedUser, Depends(require_role(Role.moderator))]
MLDevUser = Annotated[AuthenticatedUser, Depends(require_role(Role.ml_developer))]
AdminUser = Annotated[AuthenticatedUser, Depends(require_role(Role.admin))]
