"""SMTP sender (production/staging) — stdlib only, no pip dependency."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.core.log_config import get_logger

logger = get_logger(__name__)


class SMTPEmailSender:
    """`EmailSender` implementation based on `smtplib` (Gmail relay by default).

    Uses STARTTLS + app-password authentication — see
    docs/signup_email_verification/00_plan_general.md for the
    Gmail-specific constraints (From == username, ~500/day quota).
    """

    def send_verification_code(
        self,
        *,
        to_email: str,
        code: str,
        verify_link: str,
    ) -> None:
        if not settings.base.smtp_host:
            raise RuntimeError(
                "SMTPEmailSender used without SMTP_HOST configured — "
                "check get_email_sender()."
            )

        message = MIMEMultipart("alternative")
        message["Subject"] = "Confirm your Barrin account"
        message["From"] = settings.base.smtp_from_address
        message["To"] = to_email

        ttl = settings.base.verification_code_ttl_minutes
        text_body = (
            f"Your verification code: {code}\n\n"
            f"This code expires in {ttl} minutes.\n\n"
            f"You can also confirm your account by following this link:\n"
            f"{verify_link}"
        )
        html_body = (
            f"<p>Your verification code: <strong>{code}</strong></p>"
            f"<p>This code expires in {ttl} minutes.</p>"
            f'<p><a href="{verify_link}">Confirm my account</a></p>'
        )
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(
            settings.base.smtp_host, settings.base.smtp_port, timeout=10
        ) as smtp:
            if settings.base.smtp_use_tls:
                smtp.starttls()
            if settings.base.smtp_username and settings.base.smtp_password:
                smtp.login(
                    settings.base.smtp_username,
                    settings.base.smtp_password.get_secret_value(),
                )
            smtp.send_message(message)

        logger.info("Verification email sent to %s via SMTP.", to_email)
