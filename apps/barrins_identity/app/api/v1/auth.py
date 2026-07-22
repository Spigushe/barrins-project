"""Human login routes: token, refresh, register, me, logout (platform.md §8)."""

from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    dummy_verify,
    hash_password,
    verify_password,
)
from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser, CurrentUser
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair, UserCreate, UserRead

router = APIRouter()


def _claims(user: User) -> dict[str, str | int]:
    return {
        "sub": str(user.id),
        "role": user.role.value,
        "email": user.email,
        "tkv": user.token_version,
    }


def _login_rate_limit() -> str:
    """Read lazily so tests can monkeypatch settings.base.login_rate_limit."""
    return settings.base.login_rate_limit


@router.post("/token", response_model=TokenPair)
@limiter.limit(_login_rate_limit)  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType]
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DatabaseSession,
) -> TokenPair:
    """Authenticate a user and return a pair of RS256 JWT tokens.

    The `username` field of the OAuth2 form contains the email address.
    Rate-limited per IP (settings.base.login_rate_limit).

    All failure branches (unknown email, wrong password, inactive account)
    return the same 401 with the same message, verify_password checked
    before is_active, so a disabled account can't be distinguished from a
    wrong password by timing or status code (platform.md §8).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None:
        dummy_verify(form_data.password)
        raise credentials_exc

    password_ok = verify_password(form_data.password, user.hashed_password)
    if not password_ok:
        raise credentials_exc
    if not user.is_active:
        raise credentials_exc

    claims = _claims(user)
    return TokenPair(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token(claims),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    session: DatabaseSession,
    _: AdminUser,
) -> UserRead:
    """Create a new user account. Accessible to administrators only.

    Returns HTTP 409 if the email is already registered.
    """
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account already exists for '{payload.email}'.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_verified=payload.is_verified,
        display_name=payload.display_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    payload: RefreshRequest,
    session: DatabaseSession,
) -> TokenPair:
    """Exchange a valid refresh token for a new access + refresh pair.

    Mandatory rotation. Returns HTTP 401 if the token is expired,
    malformed, of the wrong type, or revoked.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_refresh_token(payload.refresh_token)
    except jwt.PyJWTError as err:
        raise credentials_exc from err

    result = await session.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    if user.token_version != token_data.token_version:
        raise credentials_exc

    claims = _claims(user)
    return TokenPair(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token(claims),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: CurrentUser,
    session: DatabaseSession,
) -> None:
    """Instantly revoke all of the user's tokens (increments token_version)."""
    user.token_version += 1
    session.add(user)
    await session.commit()
