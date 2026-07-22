"""Base application configuration settings.

This module defines core application settings for barrins-identity:
project metadata, database connection, RS256 JWT signing, Argon2id cost
parameters, login rate limiting, and logging configuration.

Classes:
    BaseAppSettings: Pydantic Settings class for core application config
"""

from typing import Literal

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pydantic import Field, PostgresDsn, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    """Core application configuration settings for barrins-identity."""

    # Metadata
    project_name: str = Field(default="Barrin's Identity", description="Project name")
    version: str = Field(default="0.1.0", description="Application version")
    api_str: str = Field(default="/api/v1", description="API routes prefix")

    # Database — required, this service owns its own database (no shared DB
    # with barrins_api, see platform.md §5).
    database_url: PostgresDsn = Field(description="PostgreSQL connection URL")
    database_echo: bool = Field(default=False, description="Enable SQL logs")

    # --- RS256 JWT signing (see platform.md §4, §6) ---
    jwt_private_key: SecretStr = Field(
        description=(
            "RSA private key PEM, generated via `openssl genrsa`. Required — "
            "never committed, never given a default value."
        ),
    )
    jwt_kid: str = Field(
        default="2026-07", description="Current signing key id (rotation)."
    )
    access_token_expire_minutes: int = Field(
        default=10, description="User access token validity duration in minutes."
    )
    refresh_token_expire_days: int = Field(
        default=7, description="User refresh token validity duration in days."
    )
    service_token_expire_minutes: int = Field(
        default=15, description="Service-account token validity duration in minutes."
    )

    # --- Argon2id cost parameters (RFC 9106 LOW_MEMORY defaults) ---
    argon2_memory_cost_kib: int = Field(
        default=65536, description="Argon2id memory cost (KiB)."
    )
    argon2_time_cost: int = Field(default=3, description="Argon2id time cost.")
    argon2_parallelism: int = Field(default=4, description="Argon2id parallelism.")

    # --- Rate limiting ---
    login_rate_limit: str = Field(
        default="5/minute",
        description="slowapi rate limit spec applied to POST /auth/token, per IP.",
    )

    # CORS — required, no wildcard (constitution §33.1).
    allowed_origins: list[str] = Field(description="Allowed origins for CORS.")

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
        default=10485760, description="Maximum size of a log file (10MB by default)"
    )
    log_backup_count: int = Field(
        default=5, description="Number of backup files to keep"
    )
    log_to_console: bool = Field(default=True, description="Enable console logging")
    log_to_file: bool = Field(default=True, description="Enable file logging")

    @field_validator("jwt_private_key")
    @classmethod
    def jwt_private_key_must_be_a_valid_rsa_key(cls, v: SecretStr) -> SecretStr:
        """Fails fast at startup rather than at the first token issuance."""
        try:
            key = load_pem_private_key(v.get_secret_value().encode(), password=None)
        except ValueError as exc:
            raise ValueError(
                "JWT_PRIVATE_KEY is not a valid PEM-encoded private key."
            ) from exc
        if not isinstance(key, RSAPrivateKey):
            raise ValueError("JWT_PRIVATE_KEY must be an RSA private key (RS256).")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Synchronous PostgreSQL connection URL (psycopg2) for Alembic."""
        return str(self.database_url).replace("+asyncpg", "+psycopg2")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings env={self.environment} debug={self.debug}>"
