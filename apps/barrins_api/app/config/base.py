"""Base application configuration settings.

This module defines core application settings including project metadata,
database connection, security configuration, environment settings, and
logging configuration.

Classes:
    BaseAppSettings: Pydantic Settings class for core application config
"""

from typing import Literal, Self

from pydantic import (
    Field,
    PostgresDsn,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
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

    # Security
    secret_key: str = Field(
        default="CHANGE_ME_GENERATE_WITH_OPENSSL",
        description="Secret key for JWT (openssl rand -hex 32)",
    )
    access_token_expire_minutes: int = Field(
        default=30, description="JWT access token validity duration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="JWT refresh token validity duration in days"
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
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

    # --- Self-registration & email verification ---
    require_email_verification: bool = Field(
        default=True,
        description=(
            "If False, POST /auth/signup creates an already-verified account "
            "and logs the user in immediately (tokens in the response), "
            "without creating an EmailVerification or sending an email. "
            "Temporary workaround while SMTP isn't configured — "
            "cf. docs/signup_email_verification/00_plan_general.md."
        ),
    )
    smtp_host: str | None = Field(
        default=None,
        description=(
            "SMTP relay host. Empty in dev/test -> console logging "
            "instead of actually sending. Required in production."
        ),
    )
    smtp_port: int = Field(default=587, description="SMTP port (STARTTLS).")
    smtp_username: str | None = Field(
        default=None, description="SMTP username (dedicated Gmail address)."
    )
    smtp_password: SecretStr | None = Field(
        default=None,
        description="SMTP app password — never logged.",
    )
    smtp_use_tls: bool = Field(default=True, description="STARTTLS.")
    smtp_from_address: str = Field(
        default="barrins-identity@gmail.com",
        description=("Sender address — must be identical to smtp_username (Gmail)."),
    )
    verification_code_ttl_minutes: int = Field(
        default=15, ge=1, description="Verification code validity duration."
    )
    verification_max_attempts: int = Field(
        default=5, ge=1, description="Attempts allowed before the code is invalidated."
    )
    verification_resend_cooldown_seconds: int = Field(
        default=60, ge=0, description="Minimum delay between two code resends."
    )
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        description=(
            "Base used to build the confirmation link sent by email "
            "({frontend_base_url}/verify-email)."
        ),
    )

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
            "Compared with hmac.compare_digest, matching the constant-time "
            "style already used for email verification codes "
            "(app/core/security.py::verify_verification_code). Empty -> the "
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

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_placeholder(cls, v: str) -> str:
        insecure = {"CHANGE_ME_GENERATE_WITH_OPENSSL", "none", "changeme", ""}
        if v.lower() in {s.lower() for s in insecure}:
            raise ValueError(
                "SECRET_KEY is set to a placeholder. "
                "Generate a real key with: openssl rand -hex 32"
            )
        return v

    @model_validator(mode="after")
    def _production_requires_real_smtp_and_frontend_url(self) -> Self:
        if self.environment != "production":
            return self
        if not self.require_email_verification:
            return self
        if not self.smtp_host:
            raise ValueError(
                "SMTP_HOST is required in production (sending verification codes)."
            )
        if self.frontend_base_url == "http://localhost:5173":
            raise ValueError(
                "FRONTEND_BASE_URL must be set in production — the default "
                "value would point the email confirmation link to a "
                "development environment."
            )
        return self

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings env={self.environment} debug={self.debug}>"
