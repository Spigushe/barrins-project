"""Unit tests for app.config (AppSettings) and app.config.base."""

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# app.config — AppSettings properties
# ---------------------------------------------------------------------------
class TestAppSettings:
    def test_is_production_false_by_default(self):
        """is_production returns False in the development environment (line 46)."""
        from app.config import AppSettings

        s = AppSettings()
        assert s.is_production is False

    def test_is_production_true(self):
        """is_production returns True when environment == 'production'."""
        from app.config import AppSettings
        from app.config.base import BaseAppSettings

        base = BaseAppSettings(
            environment="production",
            secret_key="a" * 32,
            smtp_host="smtp.gmail.com",
            frontend_base_url="https://barrins-codex.org",
        )
        s = AppSettings(base=base)
        assert s.is_production is True

    def test_is_debug(self):
        """is_debug reflects base.debug."""
        from app.config import AppSettings

        s = AppSettings()
        assert s.is_debug is s.base.debug

    def test_repr(self):
        """__repr__ contains the environment name."""
        from app.config import AppSettings

        s = AppSettings()
        assert "development" in repr(s)

    def test_project_version(self):
        """_project_version combines project_name and version."""
        from app.config import AppSettings

        s = AppSettings()
        assert s.base.project_name in s.project_version
        assert s.base.version in s.project_version


# ---------------------------------------------------------------------------
# app.config.base — BaseAppSettings validators
# ---------------------------------------------------------------------------
class TestBaseAppSettingsValidators:
    @pytest.fixture(autouse=True)
    def _clear_env_for_config_tests(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_PORT", raising=False)
        monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
        monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)

    def test_secret_key_placeholder_raises(self):
        """secret_key_must_not_be_placeholder raises ValueError for a placeholder key
        (covers line 131)."""
        with pytest.raises((ValueError, ValidationError), match="SECRET_KEY"):
            from app.config.base import BaseAppSettings

            BaseAppSettings(secret_key="CHANGE_ME_GENERATE_WITH_OPENSSL")  # noqa: S106

    def test_secret_key_changeme_raises(self):
        """The 'changeme' variant is also rejected."""
        with pytest.raises((ValueError, ValidationError)):
            from app.config.base import BaseAppSettings

            BaseAppSettings(secret_key="changeme")  # noqa: S106

    def test_valid_secret_key_accepted(self):
        """A valid key is accepted without error."""
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(_env_file=None, secret_key="a" * 32)
        assert s.secret_key == "a" * 32

    def test_database_url_sync_replaces_asyncpg(self):
        """database_url_sync replaces +asyncpg with +psycopg2."""
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(secret_key="a" * 32)
        assert "+psycopg2" in s.database_url_sync
        assert "+asyncpg" not in s.database_url_sync

    def test_production_without_smtp_host_raises(self):
        from app.config.base import BaseAppSettings

        with pytest.raises((ValueError, ValidationError), match="SMTP_HOST"):
            BaseAppSettings(
                _env_file=None,
                secret_key="a" * 32,
                environment="production",
                frontend_base_url="https://barrins-codex.org",
            )

    def test_production_with_default_frontend_url_raises(self):
        from app.config.base import BaseAppSettings

        with pytest.raises((ValueError, ValidationError), match="FRONTEND_BASE_URL"):
            BaseAppSettings(
                _env_file=None,
                secret_key="a" * 32,
                environment="production",
                smtp_host="smtp.gmail.com",
            )

    def test_production_with_both_configured_accepted(self):
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(
            _env_file=None,
            secret_key="a" * 32,
            environment="production",
            smtp_host="smtp.gmail.com",
            frontend_base_url="https://barrins-codex.org",
        )
        assert s.smtp_host == "smtp.gmail.com"

    def test_development_does_not_require_smtp_host(self):
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(
            _env_file=None,
            secret_key="a" * 32,
            environment="development",
        )
        assert s.smtp_host is None

    def test_production_with_verification_disabled_does_not_require_smtp(self):
        """require_email_verification=False also disables the FRONTEND_BASE_URL
        constraint in production — neither is used if no verification email
        is ever sent."""
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(
            _env_file=None,
            secret_key="a" * 32,
            environment="production",
            require_email_verification=False,
        )
        assert s.smtp_host is None
        assert s.frontend_base_url == "http://localhost:5173"
