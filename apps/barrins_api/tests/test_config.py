"""Unit tests for app.config (AppSettings) and app.config.base."""


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

        base = BaseAppSettings(environment="production")
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
# app.config.base — BaseAppSettings
# ---------------------------------------------------------------------------
class TestBaseAppSettings:
    def test_database_url_sync_replaces_asyncpg(self):
        """database_url_sync replaces +asyncpg with +psycopg2."""
        from app.config.base import BaseAppSettings

        s = BaseAppSettings()
        assert "+psycopg2" in s.database_url_sync
        assert "+asyncpg" not in s.database_url_sync

    def test_production_needs_no_extra_config(self):
        """Since the identity cutover (ADR-20) `barrins_api` sends no email,
        so `ENVIRONMENT=production` alone is a valid config — there is no
        SMTP / FRONTEND_BASE_URL requirement any more."""
        from app.config.base import BaseAppSettings

        s = BaseAppSettings(_env_file=None, environment="production")
        assert s.environment == "production"
