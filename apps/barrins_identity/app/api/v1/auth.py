"""Human login routes: token, refresh, register, me, logout, self-registration
and email verification (platform.md §8, §14)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

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
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_password,
    verify_verification_code,
)
from app.database.session import DatabaseSession
from app.dependencies.auth import AdminUser, CurrentUser
from app.models.email_verification import EmailVerification
from app.models.user import User, UserRole
from app.schemas.auth import (
    RefreshRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupResponse,
    TokenPair,
    UserCreate,
    UserRead,
    UserSignup,
    VerifyEmailRequest,
)
from app.services.email import EmailSenderDep

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
@limiter.limit(_login_rate_limit)
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


# ---------------------------------------------------------------------------
# Self-registration & email verification (REQUIRE_EMAIL_VERIFICATION)
# ---------------------------------------------------------------------------


def _build_verify_link(email: str, code: str) -> str:
    query = urlencode({"email": email, "code": code})
    return f"{settings.base.frontend_base_url}/verify-email?{query}"


@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: UserSignup,
    session: DatabaseSession,
    email_sender: EmailSenderDep,
) -> SignupResponse:
    """Public self-registration.

    Returns HTTP 409 if the email is already registered (consistent with
    `/auth/register`).

    Default behavior (`REQUIRE_EMAIL_VERIFICATION=true`): creates an
    unverified account and sends a verification code by email — the client
    must then call `/auth/signup/verify`. Returns HTTP 502 and registers no
    account if sending the email fails, to avoid a locked account with no
    way to receive a code.

    If `REQUIRE_EMAIL_VERIFICATION=false` (temporary workaround while SMTP
    isn't configured): creates an already-verified account and logs the
    user in immediately — no email sent, no `EmailVerification` row created.
    """
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account already exists for '{payload.email}'.",
        )

    if not settings.base.require_email_verification:
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=UserRole.user,
            is_verified=True,
            display_name=payload.display_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        tokens = TokenPair(
            access_token=create_access_token(_claims(user)),
            refresh_token=create_refresh_token(_claims(user)),
        )
        return SignupResponse(
            detail="Account created.", verification_required=False, tokens=tokens
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.user,
        is_verified=False,
        display_name=payload.display_name,
    )
    session.add(user)
    await session.flush()  # populates user.id without committing

    now = datetime.now(UTC)
    code = generate_verification_code()
    verification = EmailVerification(
        user_id=user.id,
        code_hash=hash_verification_code(code, user.id),
        expires_at=now + timedelta(minutes=settings.base.verification_code_ttl_minutes),
        last_sent_at=now,
    )
    session.add(verification)

    try:
        email_sender.send_verification_code(
            to_email=user.email,
            code=code,
            verify_link=_build_verify_link(user.email, code),
        )
    except Exception as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to send the verification email. Please try again later.",
        ) from err

    await session.commit()
    return SignupResponse()


@router.post("/signup/verify", response_model=TokenPair)
async def verify_signup(
    payload: VerifyEmailRequest,
    session: DatabaseSession,
) -> TokenPair:
    """Validate the verification code and automatically log the user in.

    Returns HTTP 400 for an invalid/expired/missing code (single message,
    doesn't indicate the exact cause), HTTP 409 if the account is already
    verified, HTTP 429 beyond the maximum number of attempts.
    """
    invalid_code_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired code.",
    )

    user_result = await session.execute(select(User).where(User.email == payload.email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise invalid_code_exc
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account is already verified.",
        )

    verification_result = await session.execute(
        select(EmailVerification).where(EmailVerification.user_id == user.id)
    )
    verification = verification_result.scalar_one_or_none()
    if verification is None or verification.expires_at < datetime.now(UTC):
        raise invalid_code_exc

    if verification.attempts >= settings.base.verification_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if not verify_verification_code(payload.code, user.id, verification.code_hash):
        verification.attempts += 1
        session.add(verification)
        await session.commit()
        raise invalid_code_exc

    user.is_verified = True
    session.add(user)
    await session.delete(verification)
    await session.commit()
    await session.refresh(user)

    return TokenPair(
        access_token=create_access_token(_claims(user)),
        refresh_token=create_refresh_token(_claims(user)),
    )


@router.post(
    "/signup/resend",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: DatabaseSession,
    email_sender: EmailSenderDep,
) -> ResendVerificationResponse:
    """Resend a new verification code.

    Always responds with the same generic message (nonexistent account,
    already verified, or active cooldown) — never discloses whether an
    account exists (constitution §23.2).
    """
    generic_response = ResendVerificationResponse()

    user_result = await session.execute(select(User).where(User.email == payload.email))
    user = user_result.scalar_one_or_none()
    if user is None or user.is_verified:
        return generic_response

    verification_result = await session.execute(
        select(EmailVerification).where(EmailVerification.user_id == user.id)
    )
    verification = verification_result.scalar_one_or_none()

    now = datetime.now(UTC)
    cooldown = timedelta(seconds=settings.base.verification_resend_cooldown_seconds)
    if verification is not None and now < verification.last_sent_at + cooldown:
        return generic_response

    code = generate_verification_code()
    expires_at = now + timedelta(minutes=settings.base.verification_code_ttl_minutes)
    if verification is None:
        verification = EmailVerification(
            user_id=user.id,
            code_hash=hash_verification_code(code, user.id),
            expires_at=expires_at,
            last_sent_at=now,
        )
    else:
        verification.code_hash = hash_verification_code(code, user.id)
        verification.expires_at = expires_at
        verification.attempts = 0
        verification.last_sent_at = now
    session.add(verification)

    try:
        email_sender.send_verification_code(
            to_email=user.email,
            code=code,
            verify_link=_build_verify_link(user.email, code),
        )
    except Exception as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to send the verification email. Please try again later.",
        ) from err

    await session.commit()
    return generic_response
