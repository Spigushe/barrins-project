"""Application configuration package with hierarchical settings.

This package provides a unified configuration system using Pydantic Settings
with environment variable support. Settings are organized into logical groups
and accessed through a singleton AppSettings instance.

Classes:
    AppSettings: Root configuration class combining all setting groups

Functions:
    get_settings: Factory function returning the singleton settings instance

Module Attributes:
    settings: Singleton AppSettings instance for application-wide use
"""

from functools import lru_cache

from pydantic_settings import BaseSettings

from app.config.base import BaseAppSettings


class AppSettings(BaseSettings):
    """Root configuration class combining all application settings.

    Aggregates all configuration groups into a single hierarchical
    settings object with environment variable support.

    Attributes:
        base: Core application settings (database, security, logging)
    """

    base: BaseAppSettings = BaseAppSettings()
    # ...

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

    @property
    def _project_version(self) -> str:
        """Backward compatibility: old internal alias."""
        return self.project_version


@lru_cache
def get_settings() -> AppSettings:
    """Get the singleton application settings instance.

    Uses lru_cache to ensure settings are loaded only once,
    even across multiple imports.

    Returns:
        AppSettings: Configured settings instance
    """
    return AppSettings()


settings = get_settings()

__all__ = ["get_settings", "settings"]
