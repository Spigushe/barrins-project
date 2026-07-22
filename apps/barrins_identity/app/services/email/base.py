"""Common interface for email senders."""

from typing import Protocol


class EmailSender(Protocol):
    """Contract implemented by every email sender in the project."""

    def send_verification_code(
        self,
        *,
        to_email: str,
        code: str,
        verify_link: str,
    ) -> None:
        """Send the verification code to `to_email`.

        `verify_link` points to the frontend confirmation page
        (`{frontend_base_url}/verify-email?email=...&code=...`) — never to
        a GET API route, so it isn't consumed by the link scanners of
        corporate email gateways before the user explicitly clicks through
        to call `POST /auth/signup/verify`.
        """
        ...

    def send_password_reset_code(
        self,
        *,
        to_email: str,
        code: str,
        reset_link: str,
    ) -> None:
        """Send a password reset code to `to_email` (platform.md §14.4).

        A distinct method from `send_verification_code` rather than a
        shared method branching on a purpose flag — the email copy
        differs ("reset your password" vs. "confirm your account"), kept
        explicit (constitution §4.6).
        """
        ...

    def send_email_change_code(
        self,
        *,
        to_email: str,
        code: str,
        verify_link: str,
    ) -> None:
        """Send an email-change confirmation code to the pending new
        address (platform.md §16.3). Distinct from `send_verification_code`
        for the same reason as `send_password_reset_code`."""
        ...
