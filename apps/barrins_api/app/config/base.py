"""Base application configuration settings.

This module defines core application settings including project metadata,
database connection, security configuration, environment settings, and
logging configuration.

Classes:
    BaseAppSettings: Pydantic Settings class for core application config
"""

from typing import Literal

from pydantic import (
    Field,
    PostgresDsn,
    SecretStr,
    computed_field,
)
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    """Core application configuration settings.

    Includes database, security, environment, and logging settings
    with sensible defaults and environment variable override support.
    """

    # Metadata
    project_name: str = Field(default="Barrin's Project", description="Project name")
    version: str = Field(default="1.0.0", description="Application version")
    api_str: str = Field(default="/api/v1", description="API routes prefix")

    # Database
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://user:pass@localhost:5432/foobar"),
        description="PostgreSQL connection URL",
    )
    database_echo: bool = Field(default=False, description="Enable SQL logs")

    # Security — identity token verification (ADR-20). barrins_api no longer
    # issues or decodes its own JWTs; it verifies identity's access tokens
    # locally against that service's JWKS (libs/identity_client).
    identity_service_url: str = Field(
        default="http://localhost:8001",
        description="Base URL of the Barrin's Identity service (JWKS source)",
    )
    identity_jwks_cache_ttl_seconds: int = Field(
        default=3600,
        description="How long a fetched JWKS document is cached before refetch",
    )
    identity_service_client_id: str = Field(
        default="",
        description=(
            "This app's own barrins_identity service-account client id, used "
            "for POST /service-token when it needs to call identity (e.g. the "
            "user-directory lookup for team rosters). Empty disables the "
            "directory — labels then fall back to a generic placeholder."
        ),
    )
    identity_service_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Secret paired with identity_service_client_id.",
    )
    allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed origins for CORS",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file_path: str = Field(
        default="logs/app.log", description="Path to the log file"
    )
    log_max_bytes: int = Field(
        default=10485760,
        description="Maximum size of a log file (10MB by default)",
    )
    log_backup_count: int = Field(
        default=5, description="Number of backup files to keep"
    )
    log_to_console: bool = Field(default=True, description="Enable console logging")
    log_to_file: bool = Field(default=True, description="Enable file logging")

    # Self-registration, email verification and SMTP config were removed in
    # the identity cutover (ADR-20): signup / verification / password reset
    # now live entirely in `apps/barrins_identity`. `barrins_api` sends no
    # email.

    # --- Moxfield deck import ---
    moxfield_user_agent: SecretStr | None = Field(
        default=None,
        description=(
            "Moxfield-assigned User-Agent value, required to call their public "
            "deck API (api2.moxfield.com). Treated as a secret — Moxfield "
            "warns it can be permanently revoked if leaked. Empty in dev/test "
            "-> falls back to a stub client returning a fixed sample decklist."
        ),
    )

    # --- Scryfall card-image proxy ---
    scryfall_user_agent: str | None = Field(
        default=None,
        description=(
            "Descriptive User-Agent sent on Scryfall image requests, per "
            "Scryfall's API etiquette (no token/registration required, unlike "
            "Moxfield). Empty in dev/test -> falls back to a placeholder-"
            "image console client."
        ),
    )
    card_image_cache_dir: str = Field(
        default="var/cache/card_images",
        description="Disk directory the card-image proxy caches Scryfall JPEGs in.",
    )

    # --- Barrin's Scripture ingestion (T3) ---
    scripture_ingest_token: SecretStr | None = Field(
        default=None,
        description=(
            "Shared static token Barrin's Scripture's sweep sends as the "
            "X-Scripture-Token header on POST /internal/scripture/ingest. "
            "Compared with hmac.compare_digest (constant-time). Empty -> the "
            "route always responds 503 (misconfigured), never accepts a "
            "request unauthenticated."
        ),
    )

    # --- MTGJSON scheduled import (S8) ---
    mtgjson_import_token: SecretStr | None = Field(
        default=None,
        description=(
            "Shared static token the daily MTGJSON-refresh systemd timer "
            "(ops/my-server/roles/mtgjson_import_scheduler) sends as the "
            "X-MTGJSON-Import-Token header on POST /mtgjson/import, "
            "compared with hmac.compare_digest like scripture_ingest_token "
            "above. Unlike that token, a human admin can still call the "
            "same route via a normal JWT regardless of whether this is "
            "set -- see verify_mtgjson_or_admin. Empty -> only admin JWTs "
            "can trigger an import, matching the route's original "
            "admin-only behavior."
        ),
    )

    # --- Karn Tablets ingestion (ADR-13) ---
    karn_ingest_token: SecretStr | None = Field(
        default=None,
        description=(
            "Shared static token the Karn Tablets clustering job "
            "(apps/karn_tablets) sends as the X-Karn-Token header on "
            "POST /internal/karn/ingest, compared with hmac.compare_digest "
            "exactly like scripture_ingest_token. Empty -> the route "
            "always responds 503 (misconfigured), never accepts a request "
            "unauthenticated."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Synchronous PostgreSQL connection URL (psycopg2) for Alembic.

        Derived from database_url by replacing +asyncpg with +psycopg2.
        """
        return str(self.database_url).replace("+asyncpg", "+psycopg2")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings env={self.environment} debug={self.debug}>"
