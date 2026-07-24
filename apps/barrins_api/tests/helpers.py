"""Utilities shared between test modules."""

from sqlalchemy import create_engine, text


def ensure_test_db_exists(sync_url: str) -> None:
    """Creates the test database if it doesn't already exist."""
    db_name = sync_url.rsplit("/", 1)[1]
    admin_url = sync_url.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()
