"""Tests for app.config (AppSettings) and app.config.base (BaseAppSettings)."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError


def _rsa_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


class TestAppSettings:
    def test_is_production_false_by_default(self):
        from app.config import settings

        assert settings.is_production is False

    def test_is_debug(self):
        from app.config import settings

        assert settings.is_debug is settings.base.debug

    def test_repr(self):
        from app.config import settings

        assert "development" in repr(settings)

    def test_project_version(self):
        from app.config import settings

        assert settings.base.project_name in settings.project_version
        assert settings.base.version in settings.project_version


class TestBaseAppSettingsValidators:
    def test_jwt_private_key_rejects_garbage(self):
        from app.config.base import BaseAppSettings

        with pytest.raises((ValueError, ValidationError), match="JWT_PRIVATE_KEY"):
            BaseAppSettings(
                _env_file=None,
                database_url="postgresql+asyncpg://u:p@localhost/db",
                jwt_private_key="not-a-pem",
                allowed_origins=["http://localhost:5173"],
            )

    def test_jwt_private_key_rejects_non_rsa_key(self):
        """An EC key is syntactically a valid PEM private key but not RSA."""
        from cryptography.hazmat.primitives.asymmetric import ec

        from app.config.base import BaseAppSettings

        ec_key = ec.generate_private_key(ec.SECP256R1())
        pem = ec_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        with pytest.raises((ValueError, ValidationError), match="RSA"):
            BaseAppSettings(
                _env_file=None,
                database_url="postgresql+asyncpg://u:p@localhost/db",
                jwt_private_key=pem,
                allowed_origins=["http://localhost:5173"],
            )

    def test_valid_rsa_key_accepted(self, monkeypatch: pytest.MonkeyPatch):
        from app.config.base import BaseAppSettings

        monkeypatch.delenv("JWT_KID", raising=False)
        s = BaseAppSettings(
            _env_file=None,
            database_url="postgresql+asyncpg://u:p@localhost/db",
            jwt_private_key=_rsa_pem(),
            allowed_origins=["http://localhost:5173"],
        )
        assert s.jwt_kid == "2026-07"

    def test_database_url_sync_replaces_asyncpg(self):
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(
            _env_file=None,
            database_url="postgresql+asyncpg://u:p@localhost/db",
            jwt_private_key=_rsa_pem(),
            allowed_origins=["http://localhost:5173"],
        )
        assert "+psycopg2" in s.database_url_sync
        assert "+asyncpg" not in s.database_url_sync

    def test_missing_required_fields_raise(self, monkeypatch: pytest.MonkeyPatch):
        from app.config.base import BaseAppSettings

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("JWT_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        with pytest.raises(ValidationError):
            BaseAppSettings(_env_file=None)
