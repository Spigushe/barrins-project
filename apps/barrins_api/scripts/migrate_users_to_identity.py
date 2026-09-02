"""One-shot migration of `barrins_api.users` into `barrins_identity.users`.

Part of the identity cutover (ADR-20, rollout Phase 7+8). `barrins_api`
drops its local `users` table; every account it held must first be copied
into `barrins_identity`'s database so the (now FK-less) `owner_id` /
`user_id` columns on the Tamiyo Scroll domain rows keep resolving.

What it does
------------
* Reads every row from the **source** (`barrins_api`) `users` table.
* Inserts it into the **target** (`barrins_identity`) `users` table
  *with the same `id`* (UUID-preserving — the domain rows reference it).
* Argon2id password hashes and `token_version` are copied verbatim
  (the Argon2 parameters are encoded in the hash string, so identity's
  own `ARGON2_*` settings are irrelevant for verification).
* Role mapping: the source enum's ``placeholder`` becomes the target
  enum's ``moderator`` (platform.md §7 rename); every other value is
  identical.
* **Email dedup:** if the target already has a row with that email, no
  second account is created — the existing target row is kept and only
  its ``role`` is raised to the higher of the two by level
  (``user`` < ``moderator`` < ``ml_developer`` < ``admin``). Every other
  target field is left untouched.
* **Username synthesis:** `barrins_api` has no `username`; identity
  requires a unique non-null one. It is derived from the email local
  part, sanitised, and given a ``-2`` / ``-3`` … suffix on collision.
  Every synthesised or de-duplicated username is written to the
  ``--report`` file for a human to review before the cutover.

The whole run is one transaction on the target
(``target_engine.begin()``): a failure part-way through rolls the target
back completely. ``--dry-run`` always rolls back.

Usage
-----
    python scripts/migrate_users_to_identity.py \
        --source-url postgresql://…/barrins_api \
        --target-url postgresql://…/barrins_identity \
        --report users-migration-report.txt --dry-run

URL resolution for each side: ``--source-url`` / ``--target-url`` flag,
then ``$SOURCE_DATABASE_URL`` / ``$TARGET_DATABASE_URL``, then the same
keys in ``apps/barrins_api/.env`` (plain ``KEY=value`` lines only).

Exit codes: ``0`` success (including a clean ``--dry-run``); ``1`` on any
error (the target transaction is rolled back).
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

# ---------------------------------------------------------------------------
# URL resolution: CLI flag > real env var > apps/barrins_api/.env
# ---------------------------------------------------------------------------
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
    for raw_line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        found_key, _, value = line.partition("=")
        if found_key.strip() == key:
            return value.strip().strip("'\"")
    return None


def _resolve_value(cli_value: str | None, env_key: str) -> str | None:
    """Resolves a setting with precedence: CLI flag > env var > .env file."""
    return cli_value or os.environ.get(env_key) or _read_dotenv_value(env_key)


# ---------------------------------------------------------------------------
# Role ordering (mirrors app/core/roles.py and barrins_identity's UserRole)
# ---------------------------------------------------------------------------
_ROLE_LEVEL: dict[str, int] = {
    "user": 1,
    "moderator": 2,
    "ml_developer": 3,
    "admin": 4,
}
# barrins_api's local enum used "placeholder" for what identity calls
# "moderator" (clean-slate rename on the new schema).
_SOURCE_ROLE_ALIASES: dict[str, str] = {"placeholder": "moderator"}


def _map_role(source_role: str) -> str:
    return _SOURCE_ROLE_ALIASES.get(source_role, source_role)


def _higher_role(a: str, b: str) -> str:
    return a if _ROLE_LEVEL.get(a, 0) >= _ROLE_LEVEL.get(b, 0) else b


# ---------------------------------------------------------------------------
# Username synthesis
# ---------------------------------------------------------------------------
_USERNAME_SANITISE = re.compile(r"[^a-z0-9_.-]+")


def _base_username(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    cleaned = _USERNAME_SANITISE.sub("-", local).strip("-._")
    cleaned = cleaned or "user"
    # identity's column is String(64); leave room for a numeric suffix.
    return cleaned[:56]


def _unique_username(email: str, taken: set[str]) -> tuple[str, bool]:
    """Return a username not in `taken`; the bool says whether a suffix was added."""
    base = _base_username(email)
    if base not in taken:
        return base, False
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}", True


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------
@dataclass
class MigrationResult:
    inserted: int = 0
    email_deduped: int = 0
    role_bumped: int = 0
    total_source: int = 0
    synthesised_usernames: list[tuple[str, str]] = field(default_factory=list)
    suffixed_usernames: list[tuple[str, str]] = field(default_factory=list)
    deduped_emails: list[str] = field(default_factory=list)

    def report_text(self) -> str:
        lines = [
            "barrins_api -> barrins_identity user migration report",
            f"generated: {datetime.now(UTC).isoformat()}",
            "",
            f"source rows                 : {self.total_source}",
            f"inserted into identity      : {self.inserted}",
            f"skipped (email already there): {self.email_deduped}",
            f"  of which role was raised  : {self.role_bumped}",
            "",
            "synthesised usernames (email -> username):",
        ]
        lines += [
            f"  {email} -> {username}" for email, username in self.synthesised_usernames
        ] or ["  (none)"]
        lines += ["", "usernames that needed a -N suffix (collision):"]
        lines += [
            f"  {email} -> {username}" for email, username in self.suffixed_usernames
        ] or ["  (none)"]
        lines += ["", "emails already present in identity (kept identity's row):"]
        lines += [f"  {email}" for email in self.deduped_emails] or ["  (none)"]
        lines += [""]
        return "\n".join(lines)


_SOURCE_SELECT = text(
    """
    SELECT id, email, hashed_password, role, is_active, is_verified,
           display_name, token_version, created_at, updated_at
    FROM users
    ORDER BY created_at, id
    """
)

_TARGET_INSERT = text(
    """
    INSERT INTO users (
        id, email, username, hashed_password, role, is_active, is_verified,
        display_name, token_version, created_at, updated_at
    ) VALUES (
        :id, :email, :username, :hashed_password, :role, :is_active, :is_verified,
        :display_name, :token_version, :created_at, :updated_at
    )
    """
)


def _normalise_url(url: str) -> str:
    """Force a synchronous psycopg2 driver — this script is plain sync SQL."""
    return url.replace("+asyncpg", "+psycopg2")


class _DryRunRollback(Exception):
    """Internal sentinel — raised to force the target transaction to roll back."""


def migrate(source: Connection, target: Connection) -> MigrationResult:
    """Copy users source->target on the given (open, in-transaction) connections."""
    result = MigrationResult()

    existing = target.execute(text("SELECT lower(email) AS email, role FROM users"))
    target_role_by_email: dict[str, str] = {row.email: row.role for row in existing}
    taken_usernames: set[str] = {
        row.username for row in target.execute(text("SELECT username FROM users"))
    }

    for row in source.execute(_SOURCE_SELECT):
        result.total_source += 1
        email_key = row.email.lower()
        mapped_role = _map_role(row.role)

        if email_key in target_role_by_email:
            result.email_deduped += 1
            result.deduped_emails.append(row.email)
            current = target_role_by_email[email_key]
            raised = _higher_role(current, mapped_role)
            if raised != current:
                result.role_bumped += 1
                target.execute(
                    text(
                        "UPDATE users SET role = :role, updated_at = now() "
                        "WHERE lower(email) = :email"
                    ),
                    {"role": raised, "email": email_key},
                )
                target_role_by_email[email_key] = raised
            continue

        username, suffixed = _unique_username(row.email, taken_usernames)
        taken_usernames.add(username)
        result.synthesised_usernames.append((row.email, username))
        if suffixed:
            result.suffixed_usernames.append((row.email, username))

        target.execute(
            _TARGET_INSERT,
            {
                "id": row.id,
                "email": row.email,
                "username": username,
                "hashed_password": row.hashed_password,
                "role": mapped_role,
                "is_active": row.is_active,
                "is_verified": row.is_verified,
                "display_name": row.display_name,
                "token_version": row.token_version,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        target_role_by_email[email_key] = mapped_role
        result.inserted += 1

    return result


def run(
    source_url: str, target_url: str, *, dry_run: bool, report_path: str | None
) -> MigrationResult:
    source_engine: Engine = create_engine(_normalise_url(source_url))
    target_engine: Engine = create_engine(_normalise_url(target_url))
    result = MigrationResult()
    try:
        # target_engine.begin() -> one transaction, committed on clean exit,
        # rolled back on any exception (incl. the dry-run sentinel).
        with (
            source_engine.connect() as source_conn,
            target_engine.begin() as target_conn,
        ):
            result = migrate(source_conn, target_conn)
            if dry_run:
                raise _DryRunRollback
    except _DryRunRollback:
        pass
    finally:
        source_engine.dispose()
        target_engine.dispose()

    if report_path:
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(result.report_text())

    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source-url",
        default=None,
        help="SQLAlchemy URL of the barrins_api database "
        "(default: $SOURCE_DATABASE_URL, then .env's SOURCE_DATABASE_URL).",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="SQLAlchemy URL of the barrins_identity database "
        "(default: $TARGET_DATABASE_URL, then .env's TARGET_DATABASE_URL).",
    )
    parser.add_argument(
        "--report",
        default=None,
        metavar="PATH",
        help="Write the username / dedup report to this file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the whole migration in a transaction, then roll back.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source_url = _resolve_value(args.source_url, "SOURCE_DATABASE_URL")
    target_url = _resolve_value(args.target_url, "TARGET_DATABASE_URL")
    if not source_url or not target_url:
        print(
            "error: both --source-url and --target-url (or their env vars, "
            "or .env entries) are required.",
            file=sys.stderr,
        )
        return 1

    try:
        result = run(
            source_url,
            target_url,
            dry_run=args.dry_run,
            report_path=args.report,
        )
    except Exception as exc:  # operator script: report the failure and exit 1
        print(f"error: migration failed and was rolled back: {exc}", file=sys.stderr)
        return 1

    mode = "DRY RUN (rolled back)" if args.dry_run else "COMMITTED"
    print(f"[{mode}]")
    print(f"  source rows              : {result.total_source}")
    print(f"  inserted into identity   : {result.inserted}")
    print(f"  skipped (email dedup)    : {result.email_deduped}")
    print(f"  role raised on dedup     : {result.role_bumped}")
    print(f"  usernames needing suffix : {len(result.suffixed_usernames)}")
    if args.report:
        print(f"  report written to        : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
