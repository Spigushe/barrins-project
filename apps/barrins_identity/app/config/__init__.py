"""Application configuration package with hierarchical settings.

This package provides a unified configuration system using Pydantic Settings
with environment variable support.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings

from app.config.base import BaseAppSettings


class AppSettings(BaseSettings):
    """Root configuration class combining all application settings."""

    base: BaseAppSettings = BaseAppSettings()  # type: ignore[call-arg]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.base.environment == "production"

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.base.debug

    def __repr__(self) -> str:
        return f"<Settings env={self.base.environment}>"

    @property
    def project_version(self) -> str:
        return f"{self.base.project_name} v{self.base.version}"


@lru_cache
def get_settings() -> AppSettings:
    """Get the singleton application settings instance.

    Uses lru_cache to ensure settings are loaded only once, even across
    multiple imports.
    """
    return AppSettings()


settings = get_settings()

__all__ = ["get_settings", "settings"]
