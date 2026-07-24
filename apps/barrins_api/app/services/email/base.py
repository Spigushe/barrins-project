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
        a GET API route (cf. docs/signup_email_verification/00_plan_general.md,
        Option D: the page must require an explicit click before calling
        `POST /auth/signup/verify`, so it isn't consumed by the link
        scanners of corporate email gateways).
        """
        ...
