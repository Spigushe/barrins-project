"""Development/test sender: logs instead of sending."""

from app.core.log_config import get_logger

logger = get_logger(__name__)


class ConsoleEmailSender:
    """`EmailSender` implementation used when `smtp_host` is empty.

    Makes no network call — logs the code in plaintext, which is only
    acceptable in development/test (never in production, cf.
    `BaseAppSettings._production_requires_real_smtp_and_frontend_url`).
    """

    def send_verification_code(
        self,
        *,
        to_email: str,
        code: str,
        verify_link: str,
    ) -> None:
        logger.info(
            "ConsoleEmailSender — verification code for %s: %s (link: %s)",
            to_email,
            code,
            verify_link,
        )

    def send_password_reset_code(
        self,
        *,
        to_email: str,
        code: str,
        reset_link: str,
    ) -> None:
        logger.info(
            "ConsoleEmailSender — password reset code for %s: %s (link: %s)",
            to_email,
            code,
            reset_link,
        )

    def send_email_change_code(
        self,
        *,
        to_email: str,
        code: str,
        verify_link: str,
    ) -> None:
        logger.info(
            "ConsoleEmailSender — email change code for %s: %s (link: %s)",
            to_email,
            code,
            verify_link,
        )
