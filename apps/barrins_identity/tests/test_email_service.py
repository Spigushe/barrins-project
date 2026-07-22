"""Tests for app/services/email/ (ConsoleEmailSender, SMTPEmailSender, factory)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.services.email import ConsoleEmailSender, SMTPEmailSender, get_email_sender
from app.services.email.smtp_sender import smtplib

_SETTINGS = "app.services.email.smtp_sender.settings.base"


class _FakeSMTP:
    """Test double for smtplib.SMTP — captures calls without any network access."""

    instances: ClassVar[list[_FakeSMTP]] = []

    def __init__(self, host: str, port: int, timeout: int = 10) -> None:
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_call: tuple[str, str] | None = None
        self.sent_message = None
        _FakeSMTP.instances.append(self)

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_call = (username, password)

    def send_message(self, message) -> None:
        self.sent_message = message


class TestConsoleEmailSender:
    def test_logs_without_network_call(self, caplog: pytest.LogCaptureFixture):
        sender = ConsoleEmailSender()
        with caplog.at_level("INFO"):
            sender.send_verification_code(
                to_email="test@example.com",
                code="123456",
                verify_link="http://localhost:5173/verify-email?code=123456",
            )
        assert "123456" in caplog.text
        assert "test@example.com" in caplog.text


class TestSMTPEmailSender:
    def test_sends_via_smtp_with_tls_and_auth(self, monkeypatch: pytest.MonkeyPatch):
        _FakeSMTP.instances.clear()
        monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
        monkeypatch.setattr(f"{_SETTINGS}.smtp_host", "smtp.gmail.com")
        monkeypatch.setattr(f"{_SETTINGS}.smtp_port", 587)
        monkeypatch.setattr(f"{_SETTINGS}.smtp_use_tls", True)
        gmail_address = "barrins-identity@gmail.com"
        monkeypatch.setattr(f"{_SETTINGS}.smtp_username", gmail_address)

        from pydantic import SecretStr

        monkeypatch.setattr(f"{_SETTINGS}.smtp_password", SecretStr("app-password"))
        monkeypatch.setattr(f"{_SETTINGS}.smtp_from_address", gmail_address)

        sender = SMTPEmailSender()
        sender.send_verification_code(
            to_email="player@example.com",
            code="654321",
            verify_link="http://localhost:5173/verify-email?code=654321",
        )

        assert len(_FakeSMTP.instances) == 1
        fake = _FakeSMTP.instances[0]
        assert fake.started_tls is True
        assert fake.login_call == ("barrins-identity@gmail.com", "app-password")
        assert fake.sent_message is not None
        assert fake.sent_message["To"] == "player@example.com"

    def test_raises_without_smtp_host_configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(f"{_SETTINGS}.smtp_host", None)
        sender = SMTPEmailSender()
        with pytest.raises(RuntimeError):
            sender.send_verification_code(
                to_email="player@example.com", code="654321", verify_link="http://x"
            )

    def test_skips_login_without_credentials(self, monkeypatch: pytest.MonkeyPatch):
        _FakeSMTP.instances.clear()
        monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
        monkeypatch.setattr(f"{_SETTINGS}.smtp_host", "smtp.gmail.com")
        monkeypatch.setattr(f"{_SETTINGS}.smtp_use_tls", False)
        monkeypatch.setattr(f"{_SETTINGS}.smtp_username", None)
        monkeypatch.setattr(f"{_SETTINGS}.smtp_password", None)

        sender = SMTPEmailSender()
        sender.send_verification_code(
            to_email="player@example.com", code="654321", verify_link="http://x"
        )

        fake = _FakeSMTP.instances[0]
        assert fake.started_tls is False
        assert fake.login_call is None


class TestGetEmailSender:
    def test_returns_console_sender_when_no_smtp_host(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.services.email.settings.base.smtp_host", None)
        assert isinstance(get_email_sender(), ConsoleEmailSender)

    def test_returns_smtp_sender_when_smtp_host_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.services.email.settings.base.smtp_host", "smtp.gmail.com"
        )
        assert isinstance(get_email_sender(), SMTPEmailSender)
