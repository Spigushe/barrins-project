"""Environment-variable configuration.

Plain `os.environ` reads, matching `barrins_scripture.sweep`'s pattern --
this is a scheduled batch job, not a FastAPI app, so `barrins_api`'s
`pydantic_settings.BaseSettings` machinery (settings groups, `.env`
layering across multiple concerns) would be more structure than a
handful of flat variables needs. See `.env.example` for the full list.
"""

import os


def database_url() -> str | None:
    """Read-only Postgres credential scoped to bs_*/mj_cards only -- Karn
    Tablets never writes to barrins_api's schema (T6, ADR-13).
    """
    return os.environ.get("KARN_TABLETS_DATABASE_URL_RO")


def barrins_api_url() -> str | None:
    """barrins_api base URL, e.g. https://api.barrins-codex.org."""
    return os.environ.get("BARRINS_API_URL")


def karn_ingest_token() -> str | None:
    """Shared secret authenticating Karn Tablets' push to
    POST /internal/karn/ingest -- same shape as SCRIPTURE_INGEST_TOKEN.
    """
    return os.environ.get("KARN_INGEST_TOKEN")
