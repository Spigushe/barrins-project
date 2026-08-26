"""Copies the `mj_*` (MTGJSON) and `bs_*` (Barrin's Scripture) tables from
the staging database into the dev database.

Usage
-----
    python scripts/sync_staging_to_dev_db.py \
        --staging-db-url postgresql://user:pass@host:5432/barrins_api_staging \
        --dev-db-url postgresql://user:pass@host:5432/barrins_api_dev \
        --yes

URLs can also be supplied via the STAGING_DATABASE_URL / DEV_DATABASE_URL
env vars, or left out entirely: if unset, they fall back to those same
keys read directly from apps/barrins_api/.env (this script does not
import the app, so pydantic-settings' own .env loading doesn't apply
here — this is a minimal, separate reader for just these two keys).
Precedence: --flag > env var > .env file. Any of these forms accepts
the app's own `postgresql+asyncpg://...` value as-is (the `+asyncpg`
driver suffix is stripped before shelling out, since `pg_dump`/
`pg_restore` don't know it).

What it does
------------
Runs `pg_dump --format=custom -t 'mj_*' -t 'bs_*'` against staging, then
`pg_restore --clean --if-exists` against dev. Table selection is by
wildcard, not an enumerated list, so it automatically picks up any future
`mj_*`/`bs_*` table without needing this script updated. `--clean`
means the existing `mj_*`/`bs_*` tables in dev are dropped and recreated
from staging's schema (handles schema drift too), then reloaded with
staging's data. `pg_dump`/`pg_restore` order DROP/CREATE/INSERT
statements to respect the tables' internal foreign keys automatically —
no `mj_*`/`bs_*` table has a foreign key to a non-prefixed table (e.g.
`users`), so this subset is self-contained and safe to copy in
isolation.

Nothing outside `mj_*`/`bs_*` (users, ts_* Tamiyo Scroll tables, the
alembic version table, ...) is touched.

Requires the `pg_dump`/`pg_restore` client binaries (PostgreSQL
`postgresql-client` package) on PATH, matching the target server's major
version or older. A newer `pg_dump` can emit preamble settings the
server doesn't recognize (e.g. PG17's `pg_dump` emits `SET
transaction_timeout = 0;`, which a pre-17 server rejects) -- `pg_restore`
treats that as a non-fatal, ignored error and still restores everything
else, but still exits non-zero, which this script treats as failure. If
your PATH has a newer major version than the server, install a
matching-version binaries-only build alongside it and point
--pg-dump-bin/--pg-restore-bin (or $PG_DUMP_BIN/$PG_RESTORE_BIN, or
.env's PG_DUMP_BIN/PG_RESTORE_BIN) at it instead of changing PATH
globally.

Exit codes
----------
    0 — success
    1 — error (bad args, missing binaries, dump/restore failure...)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

TABLE_PATTERNS = ["mj_*", "bs_*"]

#: apps/barrins_api/.env -- this script lives in apps/barrins_api/scripts/.
DOTENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _read_dotenv_value(key: str) -> str | None:
    """Minimal `KEY=value` reader for DOTENV_PATH, used only as a fallback
    when `key` isn't set as a real env var. Not a general .env parser
    (no quoting/export/multiline support) -- just enough for the plain
    `KEY=value` lines this project's .env files use.
    """
    if not DOTENV_PATH.is_file():
        return None
    for line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        found_key, _, value = line.partition("=")
        if found_key.strip() == key:
            return value.strip().strip("'\"")
    return None


def _resolve_value(cli_value: str | None, env_key: str) -> str | None:
    """Resolves a setting with precedence: CLI flag > env var > .env file."""
    return cli_value or os.environ.get(env_key) or _read_dotenv_value(env_key)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copies the mj_* and bs_* tables from the staging database "
            "into the dev database (drops and recreates them in dev)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--staging-db-url",
        default=None,
        metavar="URL",
        help=(
            "Staging DB connection URL "
            "(default: $STAGING_DATABASE_URL, then .env's STAGING_DATABASE_URL)."
        ),
    )
    parser.add_argument(
        "--dev-db-url",
        default=None,
        metavar="URL",
        help=(
            "Dev DB connection URL "
            "(default: $DEV_DATABASE_URL, then .env's DEV_DATABASE_URL)."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Proceed even though the dev URL's host or database name "
            "contains 'prod'. Without this flag, that is refused as a "
            "likely misconfiguration."
        ),
    )
    parser.add_argument(
        "--pg-dump-bin",
        default=None,
        metavar="PATH",
        help=(
            "Path to the pg_dump binary to use "
            "(default: $PG_DUMP_BIN, then .env's PG_DUMP_BIN, then 'pg_dump' on PATH)."
        ),
    )
    parser.add_argument(
        "--pg-restore-bin",
        default=None,
        metavar="PATH",
        help=(
            "Path to the pg_restore binary to use "
            "(default: $PG_RESTORE_BIN, then .env's PG_RESTORE_BIN, "
            "then 'pg_restore' on PATH)."
        ),
    )
    return parser.parse_args()


def _to_libpq_url(url: str) -> str:
    """Strips SQLAlchemy driver suffixes (e.g. `+asyncpg`) so `pg_dump`/
    `pg_restore`/`psql` accept the URL as a plain libpq connection string.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.split("+", 1)[0]
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))


def _describe(url: str) -> str:
    """Host + database name only, never the password, for confirmation prompts."""
    parts = urlsplit(url)
    return f"{parts.hostname}:{parts.port or 5432}{parts.path}"


def _require_binary(name: str, explicit_path: str | None) -> str:
    if explicit_path is not None:
        if not Path(explicit_path).is_file():
            print(f"ERROR: '{explicit_path}' does not exist.", file=sys.stderr)
            sys.exit(1)
        return explicit_path

    path = shutil.which(name)
    if path is None:
        print(
            f"ERROR: '{name}' not found on PATH. Install the PostgreSQL "
            "client tools (e.g. the 'postgresql-client' package) first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def _run(command: list[str]) -> None:
    result = subprocess.run(command)  # noqa: S603
    if result.returncode != 0:
        print(
            f"ERROR: command failed ({result.returncode}): {command[0]}",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    args = _parse_args()

    staging_db_url = _resolve_value(args.staging_db_url, "STAGING_DATABASE_URL")
    dev_db_url = _resolve_value(args.dev_db_url, "DEV_DATABASE_URL")
    pg_dump_bin = _resolve_value(args.pg_dump_bin, "PG_DUMP_BIN")
    pg_restore_bin = _resolve_value(args.pg_restore_bin, "PG_RESTORE_BIN")

    if not staging_db_url:
        print(
            "ERROR: staging DB URL required "
            "(--staging-db-url, $STAGING_DATABASE_URL, or .env).",
            file=sys.stderr,
        )
        sys.exit(1)
    if not dev_db_url:
        print(
            "ERROR: dev DB URL required (--dev-db-url, $DEV_DATABASE_URL, or .env).",
            file=sys.stderr,
        )
        sys.exit(1)

    staging_url = _to_libpq_url(staging_db_url)
    dev_url = _to_libpq_url(dev_db_url)

    if staging_url == dev_url:
        print(
            "ERROR: staging and dev URLs are identical — refusing to run.",
            file=sys.stderr,
        )
        sys.exit(1)

    if "prod" in dev_url.lower() and not args.force:
        print(
            "ERROR: the dev URL's host or database name contains 'prod'. "
            "Refusing to run without --force, since this would drop and "
            "overwrite mj_*/bs_* tables at that target.",
            file=sys.stderr,
        )
        sys.exit(1)

    pg_dump = _require_binary("pg_dump", pg_dump_bin)
    pg_restore = _require_binary("pg_restore", pg_restore_bin)

    print(f"Source (staging): {_describe(staging_url)}")
    print(f"Target (dev):     {_describe(dev_url)}")
    print(
        f"Tables:           {', '.join(TABLE_PATTERNS)} "
        "(and any future tables matching these prefixes)"
    )
    print("This will DROP and recreate the matching tables in the dev database.")

    if not args.yes:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        dump_path = Path(tmp_dir) / "mj_bs_staging.dump"

        dump_command = [pg_dump, "--format=custom", "--no-owner", "--no-privileges"]
        for pattern in TABLE_PATTERNS:
            dump_command += ["-t", pattern]
        dump_command += ["--file", str(dump_path), staging_url]

        print("\nDumping from staging...")
        _run(dump_command)

        restore_command = [
            pg_restore,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            f"--dbname={dev_url}",
            str(dump_path),
        ]

        print("Restoring into dev...")
        _run(restore_command)

    print("\nDone. mj_* and bs_* tables in dev now mirror staging.")


if __name__ == "__main__":
    main()
