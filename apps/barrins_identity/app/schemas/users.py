"""Pydantic schemas for account-resource management (platform.md §15-§17)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountSettingsUpdate(BaseModel):
    """Payload for PATCH /users/me (platform.md §16.2).

    Partial-update semantics via `model_fields_set`: a field absent from
    the payload is left untouched; `display_name` explicitly set to
    `null` clears it. Setting `email` does not necessarily apply it
    immediately — see the route handler (`REQUIRE_EMAIL_VERIFICATION`
    gating, platform.md §16.2).
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    email: EmailStr | None = None


class AccountDeleteRequest(BaseModel):
    """Payload for DELETE /users/me (platform.md §15.2).

    Re-auth via current password, not a token-freshness check — see
    platform.md §15.2 for why.
    """

    model_config = ConfigDict(extra="forbid")

    current_password: str


class EmailChangeVerifyRequest(BaseModel):
    """Payload for POST /users/me/email-change/verify (platform.md §16.3).

    No `email` field, unlike `VerifyEmailRequest` (signup) — the caller
    is already authenticated as the account with the pending change.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^\d{6}$", description="6-digit code received by email.")


class EmailChangeResendResponse(BaseModel):
    """Response of POST /users/me/email-change/resend.

    Unlike `ResendVerificationResponse`, this is not anti-enumeration
    sensitive (the caller is already authenticated), so the message can
    be specific.
    """

    detail: str = "A new code has been sent to the pending email address."
