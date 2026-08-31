"""FastAPI dependencies for JWT authentication and authorization."""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from app.core.security import decode_access_token, decode_service_token
from app.database.session import DatabaseSession
from app.models.service_account import ServiceAccount
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
# Same scheme, but a missing Authorization header is not an error — the
# endpoint decides what "anonymous" means (used by GET /applications).
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token", auto_error=False
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DatabaseSession,
) -> User:
    """Validate the JWT and return the corresponding active user.

    Raises HTTP 401 if:
    - the token is missing, malformed, expired, or of the wrong type
      (including a service-account token — account_type claim, tests.md §3);
    - the user no longer exists in the database;
    - the account is inactive;
    - the token_version doesn't match (token revoked — logout).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_access_token(token)
    except jwt.PyJWTError as err:
        raise credentials_exc from err

    result = await session.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc

    if user.token_version != token_data.token_version:
        raise credentials_exc

    return user


async def get_optional_current_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    session: DatabaseSession,
) -> User | None:
    """Return the current user, or None when no Authorization header is sent.

    A header that *is* present but invalid (malformed / expired / revoked /
    unknown user) still raises 401 — same as `get_current_user` — so the
    client's silent-refresh path can kick in. Only a wholly absent
    credential is treated as anonymous.
    """
    if token is None:
        return None
    return await get_current_user(token=token, session=session)


def require_role(min_role: UserRole) -> Callable[..., Awaitable[User]]:
    """Dependency factory: requires the user to have a level >= min_role.

    Roles are hierarchical (user < moderator < ml_developer < admin).
    """

    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role.level < min_role.level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return current_user

    return _check


async def get_current_service_account(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DatabaseSession,
) -> ServiceAccount:
    """Validate a service-account token and return the active service account.

    Symmetric to get_current_user: rejects a user token via the
    account_type claim (tests.md §3).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_service_token(token)
    except jwt.PyJWTError as err:
        raise credentials_exc from err

    result = await session.execute(
        select(ServiceAccount).where(ServiceAccount.client_id == token_data.sub)
    )
    account = result.scalar_one_or_none()
    if account is None or not account.is_active:
        raise credentials_exc

    if account.token_version != token_data.token_version:
        raise credentials_exc

    return account


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]
ModeratorUser = Annotated[User, Depends(require_role(UserRole.moderator))]
MLDevUser = Annotated[User, Depends(require_role(UserRole.ml_developer))]
AdminUser = Annotated[User, Depends(require_role(UserRole.admin))]
CurrentServiceAccount = Annotated[ServiceAccount, Depends(get_current_service_account)]
