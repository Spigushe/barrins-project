"""Account-resource management routes: profile settings, email change,
account deletion, per-app settings (platform.md §15-§17).

Split from `app/api/v1/auth.py`: `/auth/*` stays scoped to
authentication/session lifecycle (token issuance, refresh, logout,
"who am I" via `GET /auth/me`); `/users/*` owns account-resource
mutation. Both operate on the same `User` row via `CurrentUser`.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Body, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.core.security import (
    generate_verification_code,
    hash_verification_code,
    verify_password,
    verify_verification_code,
)
from app.database.session import DatabaseSession
from app.dependencies.auth import CurrentUser
from app.models.app_settings import AppKey, AppSettings
from app.models.email_change_request import EmailChangeRequest
from app.models.user import User
from app.schemas.app_settings import AppSettingsRead
from app.schemas.auth import UserRead
from app.schemas.users import (
    AccountDeleteRequest,
    AccountSettingsUpdate,
    EmailChangeResendResponse,
    EmailChangeVerifyRequest,
)
from app.services.email import EmailSenderDep

router = APIRouter()


def _build_email_change_link(email: str, code: str) -> str:
    query = urlencode({"email": email, "code": code})
    return f"{settings.base.frontend_base_url}/confirm-email-change?{query}"


# ---------------------------------------------------------------------------
# Global account settings (platform.md §16)
# ---------------------------------------------------------------------------


@router.patch("/me", response_model=UserRead)
async def update_account_settings(
    payload: AccountSettingsUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
    email_sender: EmailSenderDep,
) -> UserRead:
    """Update the caller's `display_name` and/or `email`.

    `display_name` is applied immediately — it carries no security
    meaning. A new `email` is applied immediately only when
    `REQUIRE_EMAIL_VERIFICATION=false`; otherwise the old address stays
    authoritative and a confirmation code is emailed to the new one
    (platform.md §16.2) — the response still reflects the old email.
    """
    if "display_name" in payload.model_fields_set:
        current_user.display_name = payload.display_name

    if "email" in payload.model_fields_set and payload.email is not None:
        new_email = payload.email
        if new_email != current_user.email:
            existing = await session.execute(
                select(User).where(User.email == new_email, User.id != current_user.id)
            )
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An account already exists for '{new_email}'.",
                )

            if not settings.base.require_email_verification:
                current_user.email = new_email
            else:
                request_result = await session.execute(
                    select(EmailChangeRequest).where(
                        EmailChangeRequest.user_id == current_user.id
                    )
                )
                change_request = request_result.scalar_one_or_none()

                now = datetime.now(UTC)
                code = generate_verification_code()
                expires_at = now + timedelta(
                    minutes=settings.base.verification_code_ttl_minutes
                )
                if change_request is None:
                    change_request = EmailChangeRequest(
                        user_id=current_user.id,
                        new_email=new_email,
                        code_hash=hash_verification_code(code, current_user.id),
                        expires_at=expires_at,
                        last_sent_at=now,
                    )
                else:
                    change_request.new_email = new_email
                    change_request.code_hash = hash_verification_code(
                        code, current_user.id
                    )
                    change_request.expires_at = expires_at
                    change_request.attempts = 0
                    change_request.last_sent_at = now
                session.add(change_request)

                try:
                    email_sender.send_email_change_code(
                        to_email=new_email,
                        code=code,
                        verify_link=_build_email_change_link(new_email, code),
                    )
                except Exception as err:
                    await session.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            "Unable to send the confirmation email. "
                            "Please try again later."
                        ),
                    ) from err

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/me/email-change/verify", response_model=UserRead)
async def verify_email_change(
    payload: EmailChangeVerifyRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> UserRead:
    """Confirm a pending email change with its code.

    Returns HTTP 404 if there's no pending change, HTTP 400 for an
    invalid/expired code, HTTP 429 beyond the max attempts, HTTP 409 if
    the address was claimed by someone else in the interim — in which
    case the pending request is also deleted (platform.md §16.3).
    """
    request_result = await session.execute(
        select(EmailChangeRequest).where(EmailChangeRequest.user_id == current_user.id)
    )
    change_request = request_result.scalar_one_or_none()
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending email change.",
        )

    invalid_code_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired code.",
    )
    if change_request.expires_at < datetime.now(UTC):
        raise invalid_code_exc

    if change_request.attempts >= settings.base.verification_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if not verify_verification_code(
        payload.code, current_user.id, change_request.code_hash
    ):
        change_request.attempts += 1
        session.add(change_request)
        await session.commit()
        raise invalid_code_exc

    existing = await session.execute(
        select(User).where(
            User.email == change_request.new_email, User.id != current_user.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        await session.delete(change_request)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account already exists for '{change_request.new_email}'.",
        )

    current_user.email = change_request.new_email
    session.add(current_user)
    await session.delete(change_request)
    await session.commit()
    await session.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post(
    "/me/email-change/resend",
    response_model=EmailChangeResendResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_email_change_code(
    session: DatabaseSession,
    current_user: CurrentUser,
    email_sender: EmailSenderDep,
) -> EmailChangeResendResponse:
    """Resend the code for a pending email change.

    Not anti-enumeration sensitive (the caller is already authenticated
    as the account with the pending change) — HTTP 404 if there's no
    pending change.
    """
    request_result = await session.execute(
        select(EmailChangeRequest).where(EmailChangeRequest.user_id == current_user.id)
    )
    change_request = request_result.scalar_one_or_none()
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending email change.",
        )

    now = datetime.now(UTC)
    cooldown = timedelta(seconds=settings.base.verification_resend_cooldown_seconds)
    if now < change_request.last_sent_at + cooldown:
        return EmailChangeResendResponse()

    code = generate_verification_code()
    change_request.code_hash = hash_verification_code(code, current_user.id)
    change_request.expires_at = now + timedelta(
        minutes=settings.base.verification_code_ttl_minutes
    )
    change_request.attempts = 0
    change_request.last_sent_at = now
    session.add(change_request)

    try:
        email_sender.send_email_change_code(
            to_email=change_request.new_email,
            code=code,
            verify_link=_build_email_change_link(change_request.new_email, code),
        )
    except Exception as err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("Unable to send the confirmation email. Please try again later."),
        ) from err

    await session.commit()
    return EmailChangeResendResponse()


# ---------------------------------------------------------------------------
# Account deletion (platform.md §15)
# ---------------------------------------------------------------------------


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    payload: AccountDeleteRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> None:
    """Soft-delete the caller's account.

    Requires the current password (re-auth) — HTTP 401 if it doesn't
    match. Anonymizes `email`/`display_name`, deactivates the account,
    and bumps `token_version` (platform.md §15). Cascading cleanup of
    app-owned data is out of scope here — each app owns its own data
    retention policy (constitution §4.1).
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    current_user.email = f"deleted-{current_user.id}@barrins.invalid"
    current_user.display_name = None
    current_user.hashed_password = "!"  # noqa: S105 — never a valid Argon2id hash
    current_user.is_active = False
    current_user.token_version += 1
    session.add(current_user)
    await session.commit()


# ---------------------------------------------------------------------------
# Per-app settings (platform.md §17)
# ---------------------------------------------------------------------------


async def _get_app_settings(
    session: DatabaseSession, user_id: uuid.UUID, app_key: str
) -> AppSettings | None:
    result = await session.execute(
        select(AppSettings).where(
            AppSettings.user_id == user_id, AppSettings.app_key == app_key
        )
    )
    return result.scalar_one_or_none()


def _validate_app_key(app_key: str) -> None:
    """Raises HTTP 404 for an unknown `app_key` — not 422: this is an
    unknown resource, not a malformed request (platform.md §17.2)."""
    if app_key not in {member.value for member in AppKey}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown app_key '{app_key}'.",
        )


@router.get("/me/settings/{app_key}", response_model=AppSettingsRead)
async def get_app_settings(
    app_key: str,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AppSettingsRead:
    """Return the caller's settings blob for one app.

    Returns `{}` if no row exists yet — a `GET` never creates one (only
    `PUT` does, avoiding empty-row churn from read-only clients).
    """
    _validate_app_key(app_key)
    row = await _get_app_settings(session, current_user.id, app_key)
    return AppSettingsRead(data=row.data if row is not None else {})


@router.put("/me/settings/{app_key}", response_model=AppSettingsRead)
async def put_app_settings(
    app_key: str,
    payload: Annotated[dict[str, Any], Body()],
    session: DatabaseSession,
    current_user: CurrentUser,
) -> AppSettingsRead:
    """Replace the caller's settings blob for one app (upsert).

    Full replace, not a merge — capped at `MAX_APP_SETTINGS_BYTES`. The
    size check happens here, not in the request schema: Pydantic
    validation failures are always 422, but "too large" is semantically
    a 413 (platform.md §17.3).
    """
    _validate_app_key(app_key)

    size = len(json.dumps(payload).encode())
    if size > settings.base.max_app_settings_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Settings payload too large ({size} bytes, "
                f"max {settings.base.max_app_settings_bytes})."
            ),
        )

    row = await _get_app_settings(session, current_user.id, app_key)
    if row is None:
        row = AppSettings(user_id=current_user.id, app_key=app_key, data=payload)
    else:
        row.data = payload
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return AppSettingsRead(data=row.data)
