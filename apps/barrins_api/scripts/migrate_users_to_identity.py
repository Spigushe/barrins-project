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
* **Local reference remap (dedup UUID mismatch):** a dedup means
  identity already had its own row for that email — under its own id,
  not the source row's id. Every domain table in `barrins_api` that
  still points at the *source* id (``ts_personal_decks.owner_id`` and
  the other columns in ``_PLAIN_REMAP_TABLES``/``_SETTINGS_TABLE``/
  ``_TEAM_MEMBERS_TABLE`` below) is re-pointed at identity's id, or the
  whole local account (decks, matches, sessions, …) would silently
  become unreachable once the source `users` table is dropped. A
  ``ts_user_settings`` collision (identity's id already has a row, e.g.
  from a login between deploy and migration) keeps the *old* row's real
  preferences and discards the blank auto-created one. A
  ``ts_team_members`` collision (already a member of the same team
  under both ids) is left untouched and flagged in the report — that
  one is ambiguous enough to need a human.
* **Username synthesis:** `barrins_api` has no `username`; identity
  requires a unique non-null one. It is derived from the email local
  part, sanitised, and given a ``-2`` / ``-3`` … suffix on collision.
  Every synthesised or de-duplicated username is written to the
  ``--report`` file for a human to review before the cutover.

The whole run is one transaction on **both** the source and the target
(``source_engine.begin()`` / ``target_engine.begin()``): a failure
part-way through rolls both back completely. ``--dry-run`` always rolls
back.

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

from sqlalchemy import column, create_engine, delete, select, table, text, update
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
    remapped_users: list[tuple[str, str, str]] = field(default_factory=list)
    remap_row_counts: dict[str, int] = field(default_factory=dict)
    settings_merged: list[str] = field(default_factory=list)
    manual_review: list[str] = field(default_factory=list)

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
        lines += [
            "",
            "local references remapped onto identity's existing id "
            "(email: old-uuid -> new-uuid):",
        ]
        lines += [
            f"  {email}: {old} -> {new}" for email, old, new in self.remapped_users
        ] or ["  (none)"]
        lines += ["", "rows updated per table:"]
        lines += [
            f"  {table_name}: {count}"
            for table_name, count in sorted(self.remap_row_counts.items())
        ] or ["  (none)"]
        lines += [
            "",
            "ts_user_settings rows merged (kept the pre-existing local row, "
            "discarded a blank auto-created one):",
        ]
        lines += [f"  {email}" for email in self.settings_merged] or ["  (none)"]
        lines += ["", "NEEDS MANUAL REVIEW:"]
        lines += [f"  {warning}" for warning in self.manual_review] or ["  (none)"]
        lines += [""]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Local reference remap — run on the *source* (barrins_api) database
# whenever a dedup means identity's id for an email differs from the
# source row's id. Table/column list mirrors `_USER_FKS` in
# apps/barrins_api/alembic/versions/
# d9e1a2c3b4f5_drop_local_auth_schema_identity_cutover.py as of the
# schema this script targets — keep both in sync if a table gains a new
# users.id reference before the cutover runs.
# ---------------------------------------------------------------------------
#: (table, column) pairs with no uniqueness constraint on the column
#: itself — a blind UPDATE is always safe regardless of what the target
#: id already has.
_PLAIN_REMAP_TABLES: tuple[tuple[str, str], ...] = (
    ("ts_card_tests", "owner_id"),
    ("ts_matches", "owner_id"),
    ("ts_meta_decks", "owner_id"),
    ("ts_personal_decks", "owner_id"),
    ("ts_sessions", "owner_id"),
    ("ts_teams", "owner_id"),
    ("ts_team_deck_flags", "flagged_by"),
    ("ts_team_deck_messages", "author_id"),
    ("ts_invite_attempts", "user_id"),
)
#: One row per user (user_id is the sole primary key) — a target-id
#: collision needs delete-the-blank-row-then-rename, not a blind UPDATE.
_SETTINGS_TABLE: tuple[str, str] = ("ts_user_settings", "user_id")
#: Composite primary key (team_id, user_id) — a target-id collision means
#: the same person is already a member of the same team under both ids,
#: which is ambiguous enough to leave for manual review.
_TEAM_MEMBERS_TABLE: tuple[str, str] = ("ts_team_members", "user_id")


def _remap_local_references(
    source: Connection,
    *,
    old_id: object,
    new_id: object,
    email: str,
    result: MigrationResult,
) -> None:
    """Re-point every local FK-style reference to `old_id` onto `new_id`.

    Needed whenever email dedup keeps identity's existing row instead of
    inserting a fresh one: the source row's id and identity's id for that
    same person then diverge, and every domain table still carrying the
    source id would otherwise reference a UUID identity has never heard
    of once the source `users` table is dropped. Uses SQLAlchemy Core's
    `table()`/`column()` rather than string-formatted SQL so the
    hardcoded identifiers above are the only place table/column names are
    named — never concatenated into a query string.
    """
    if str(old_id) == str(new_id):
        return

    for table_name, column_name in _PLAIN_REMAP_TABLES:
        tbl = table(table_name, column(column_name))
        col = tbl.c[column_name]
        stmt = update(tbl).where(col == old_id).values({column_name: new_id})
        res = source.execute(stmt)
        if res.rowcount:
            result.remap_row_counts[table_name] = (
                result.remap_row_counts.get(table_name, 0) + res.rowcount
            )

    settings_table_name, settings_col_name = _SETTINGS_TABLE
    settings_tbl = table(settings_table_name, column(settings_col_name))
    settings_col = settings_tbl.c[settings_col_name]
    target_has_settings = source.execute(
        select(settings_col).where(settings_col == new_id)
    ).first()
    if target_has_settings:
        source.execute(delete(settings_tbl).where(settings_col == new_id))
        result.settings_merged.append(email)
    res = source.execute(
        update(settings_tbl)
        .where(settings_col == old_id)
        .values({settings_col_name: new_id})
    )
    if res.rowcount:
        result.remap_row_counts[settings_table_name] = (
            result.remap_row_counts.get(settings_table_name, 0) + res.rowcount
        )

    team_table_name, team_col_name = _TEAM_MEMBERS_TABLE
    team_tbl = table(team_table_name, column("team_id"), column(team_col_name))
    team_col = team_tbl.c[team_col_name]
    memberships = source.execute(
        select(team_tbl.c.team_id).where(team_col == old_id)
    ).all()
    for membership in memberships:
        collision = source.execute(
            select(team_col).where(
                (team_tbl.c.team_id == membership.team_id) & (team_col == new_id)
            )
        ).first()
        if collision:
            result.manual_review.append(
                f"{email}: {team_table_name} team {membership.team_id} already "
                f"has a row for the target id {new_id} — old row (team_id="
                f"{membership.team_id}, {team_col_name}={old_id}) left "
                "untouched, resolve by hand"
            )
            continue
        source.execute(
            update(team_tbl)
            .where((team_tbl.c.team_id == membership.team_id) & (team_col == old_id))
            .values({team_col_name: new_id})
        )
        result.remap_row_counts[team_table_name] = (
            result.remap_row_counts.get(team_table_name, 0) + 1
        )

    result.remapped_users.append((email, str(old_id), str(new_id)))


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

    existing = target.execute(
        text("SELECT lower(email) AS email, id, role FROM users")
    ).all()
    target_role_by_email: dict[str, str] = {row.email: row.role for row in existing}
    target_id_by_email: dict[str, object] = {row.email: row.id for row in existing}
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
            _remap_local_references(
                source,
                old_id=row.id,
                new_id=target_id_by_email[email_key],
                email=row.email,
                result=result,
            )
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
        # .begin() on both -> one transaction each, committed together on
        # clean exit, rolled back together on any exception (incl. the
        # dry-run sentinel). Source needs a write transaction too, not
        # just a read connection, since a dedup can remap local
        # references on the source side (see _remap_local_references).
        with (
            source_engine.begin() as source_conn,
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
    print(f"  local refs remapped      : {len(result.remapped_users)}")
    print(f"  settings rows merged     : {len(result.settings_merged)}")
    if args.report:
        print(f"  report written to        : {args.report}")
    if result.manual_review:
        print(
            f"\n  ⚠ {len(result.manual_review)} item(s) NEED MANUAL REVIEW "
            "-- see the report.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
