"""Tests for `scripts/migrate_users_to_identity.py` (identity cutover, ADR-20).

Runs against two throwaway PostgreSQL databases derived from the test DB
URL — no confirmation gate (that only guards production data). Covers:
UUID preservation, email dedup (skip insert + raise role), username
synthesis + collision suffixing, the report file, `--dry-run`, whole-run
atomicity on a mid-loop failure, and the local-reference remap a dedup
triggers on the *source* side (found live during the staging cutover:
a dedup keeps identity's pre-existing id, silently orphaning every
domain row still pointing at the source's own id for that person).
"""

import uuid

import pytest
from sqlalchemy import column as sa_column
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy import table as sa_table
from sqlalchemy.exc import IntegrityError

from app.config import settings
from scripts import migrate_users_to_identity as mig
from scripts.migrate_users_to_identity import run

_ADMIN_URL = (
    str(settings.base.database_url).replace("+asyncpg", "+psycopg2").rsplit("/", 1)[0]
    + "/postgres"
)
_SRC_DB = "barrins_mig_src_test"
_TGT_DB = "barrins_mig_tgt_test"
_SRC_URL = _ADMIN_URL.rsplit("/", 1)[0] + f"/{_SRC_DB}"
_TGT_URL = _ADMIN_URL.rsplit("/", 1)[0] + f"/{_TGT_DB}"

_SOURCE_DDL = """
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    display_name VARCHAR(100),
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Minimal mirror of every table _remap_local_references touches, so a
-- dedup exercises the exact same statements it runs against production.
CREATE TABLE ts_card_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID
);
CREATE TABLE ts_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID
);
CREATE TABLE ts_meta_decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID
);
CREATE TABLE ts_personal_decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID, name VARCHAR(100)
);
CREATE TABLE ts_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID
);
CREATE TABLE ts_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_id UUID
);
CREATE TABLE ts_team_deck_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), flagged_by UUID
);
CREATE TABLE ts_team_deck_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), author_id UUID
);
CREATE TABLE ts_invite_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID
);
CREATE TABLE ts_user_settings (user_id UUID PRIMARY KEY, note VARCHAR(100));
CREATE TABLE ts_team_members (
    team_id UUID NOT NULL, user_id UUID NOT NULL, PRIMARY KEY (team_id, user_id)
);
"""

_TARGET_DDL = """
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(64) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    display_name VARCHAR(100),
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _recreate(db_name: str, ddl: str) -> None:
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()
    eng = create_engine(_ADMIN_URL.rsplit("/", 1)[0] + f"/{db_name}")
    with eng.begin() as conn:
        conn.execute(text(ddl))
    eng.dispose()


@pytest.fixture()
def clean_dbs():
    _recreate(_SRC_DB, _SOURCE_DDL)
    _recreate(_TGT_DB, _TARGET_DDL)
    yield
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        for name in (_SRC_DB, _TGT_DB):
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def _seed_source(rows: list[dict]) -> None:
    eng = create_engine(_SRC_URL)
    with eng.begin() as conn:
        for row in rows:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, hashed_password, role, "
                    "display_name, token_version) VALUES (:id, :email, :hp, "
                    ":role, :dn, :tkv)"
                ),
                {
                    "id": row["id"],
                    "email": row["email"],
                    "hp": row.get("hp", "argon2$dummy"),
                    "role": row.get("role", "user"),
                    "dn": row.get("display_name"),
                    "tkv": row.get("token_version", 0),
                },
            )
    eng.dispose()


def _seed_target(rows: list[dict]) -> None:
    eng = create_engine(_TGT_URL)
    with eng.begin() as conn:
        for row in rows:
            conn.execute(
                text(
                    "INSERT INTO users (id, email, username, hashed_password, "
                    "role) VALUES (:id, :email, :username, :hp, :role)"
                ),
                {
                    "id": row.get("id", str(uuid.uuid4())),
                    "email": row["email"],
                    "username": row["username"],
                    "hp": row.get("hp", "argon2$identity"),
                    "role": row.get("role", "user"),
                },
            )
    eng.dispose()


def _target_users() -> list[dict]:
    eng = create_engine(_TGT_URL)
    with eng.connect() as conn:
        rows = [
            dict(r._mapping)
            for r in conn.execute(
                text("SELECT id, email, username, role, token_version FROM users")
            )
        ]
    eng.dispose()
    return rows


def _seed_source_domain_row(table_name: str, **columns: object) -> None:
    """Insert one row into a source-side domain table via Core's `table()`/
    `column()` (not string-formatted SQL) — same technique as
    `_remap_local_references` in the script under test.
    """
    tbl = sa_table(table_name, *(sa_column(c) for c in columns))
    eng = create_engine(_SRC_URL)
    with eng.begin() as conn:
        conn.execute(insert(tbl).values(**columns))
    eng.dispose()


def _source_rows(table_name: str, *select_columns: str) -> list[dict]:
    tbl = sa_table(table_name, *(sa_column(c) for c in select_columns))
    eng = create_engine(_SRC_URL)
    with eng.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(select(tbl))]
    eng.dispose()
    return rows


class TestUrlResolution:
    """`_resolve_value`: CLI flag > real env var > .env's `KEY=value` line."""

    def test_cli_flag_wins_over_env_and_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SOURCE_DATABASE_URL", "from-env")
        monkeypatch.setattr(mig, "DOTENV_PATH", tmp_path / ".env")
        (tmp_path / ".env").write_text("SOURCE_DATABASE_URL=from-dotenv\n")

        assert mig._resolve_value("from-cli", "SOURCE_DATABASE_URL") == "from-cli"

    def test_env_var_wins_over_dotenv(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TARGET_DATABASE_URL", "from-env")
        monkeypatch.setattr(mig, "DOTENV_PATH", tmp_path / ".env")
        (tmp_path / ".env").write_text("TARGET_DATABASE_URL=from-dotenv\n")

        assert mig._resolve_value(None, "TARGET_DATABASE_URL") == "from-env"

    def test_falls_back_to_dotenv_when_nothing_else_set(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TARGET_DATABASE_URL", raising=False)
        monkeypatch.setattr(mig, "DOTENV_PATH", tmp_path / ".env")
        (tmp_path / ".env").write_text(
            "# a comment\nTARGET_DATABASE_URL='quoted-value'\n"
        )

        assert mig._resolve_value(None, "TARGET_DATABASE_URL") == "quoted-value"

    def test_returns_none_when_unset_everywhere(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SOURCE_DATABASE_URL", raising=False)
        monkeypatch.setattr(mig, "DOTENV_PATH", tmp_path / "missing.env")

        assert mig._resolve_value(None, "SOURCE_DATABASE_URL") is None

    def test_main_errors_when_no_urls_resolvable(self, tmp_path, monkeypatch, capsys):
        monkeypatch.delenv("SOURCE_DATABASE_URL", raising=False)
        monkeypatch.delenv("TARGET_DATABASE_URL", raising=False)
        monkeypatch.setattr(mig, "DOTENV_PATH", tmp_path / "missing.env")

        assert mig.main([]) == 1
        assert "required" in capsys.readouterr().err


@pytest.mark.usefixtures("clean_dbs")
class TestMigrate:
    def test_inserts_non_colliding_users_preserving_uuid(self, tmp_path):
        uid = str(uuid.uuid4())
        _seed_source([{"id": uid, "email": "alice@example.com", "token_version": 3}])

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        assert result.inserted == 1
        assert result.email_deduped == 0
        target = _target_users()
        assert len(target) == 1
        assert str(target[0]["id"]) == uid
        assert target[0]["username"] == "alice"
        assert target[0]["token_version"] == 3

    def test_source_placeholder_role_maps_to_moderator(self, tmp_path):
        _seed_source(
            [
                {
                    "id": str(uuid.uuid4()),
                    "email": "mod@example.com",
                    "role": "placeholder",
                }
            ]
        )

        run(_SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt"))

        assert _target_users()[0]["role"] == "moderator"

    def test_email_dedup_skips_insert_and_raises_role(self, tmp_path):
        existing_id = str(uuid.uuid4())
        _seed_target(
            [
                {
                    "id": existing_id,
                    "email": "dup@example.com",
                    "username": "dup",
                    "role": "user",
                }
            ]
        )
        _seed_source(
            [{"id": str(uuid.uuid4()), "email": "dup@example.com", "role": "admin"}]
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        assert result.inserted == 0
        assert result.email_deduped == 1
        assert result.role_bumped == 1
        target = _target_users()
        assert len(target) == 1
        assert str(target[0]["id"]) == existing_id  # identity's row kept
        assert target[0]["role"] == "admin"  # raised to the higher level

    def test_email_dedup_does_not_lower_role(self, tmp_path):
        _seed_target(
            [{"email": "keep@example.com", "username": "keep", "role": "admin"}]
        )
        _seed_source(
            [{"id": str(uuid.uuid4()), "email": "keep@example.com", "role": "user"}]
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        assert result.role_bumped == 0
        assert _target_users()[0]["role"] == "admin"

    def test_username_collisions_get_suffixed_and_reported(self, tmp_path):
        _seed_target([{"email": "other@x.com", "username": "sam"}])
        _seed_source(
            [
                {"id": str(uuid.uuid4()), "email": "sam@a.com"},
                {"id": str(uuid.uuid4()), "email": "sam@b.com"},
            ]
        )
        report = tmp_path / "report.txt"

        result = run(_SRC_URL, _TGT_URL, dry_run=False, report_path=str(report))

        usernames = sorted(u["username"] for u in _target_users())
        assert usernames == ["sam", "sam-2", "sam-3"]
        assert len(result.suffixed_usernames) == 2
        text_report = report.read_text(encoding="utf-8")
        assert "sam-2" in text_report and "sam-3" in text_report

    def test_dry_run_writes_nothing(self, tmp_path):
        _seed_source([{"id": str(uuid.uuid4()), "email": "ghost@example.com"}])

        result = run(
            _SRC_URL, _TGT_URL, dry_run=True, report_path=str(tmp_path / "r.txt")
        )

        assert result.inserted == 1  # counted...
        assert _target_users() == []  # ...but rolled back

    def test_mid_loop_failure_rolls_back_the_whole_run(self, tmp_path):
        good_id = str(uuid.uuid4())
        clash_id = str(uuid.uuid4())
        # Target already holds `clash_id` under a different email, so email
        # dedup won't catch it — the second INSERT hits a PK violation.
        _seed_target(
            [{"id": clash_id, "email": "unrelated@example.com", "username": "unrel"}]
        )
        _seed_source(
            [
                {"id": good_id, "email": "first@example.com"},
                {"id": clash_id, "email": "second@example.com"},
            ]
        )

        with pytest.raises(IntegrityError):
            run(_SRC_URL, _TGT_URL, dry_run=False, report_path=None)

        emails = {u["email"] for u in _target_users()}
        assert emails == {"unrelated@example.com"}  # nothing from the source landed


@pytest.mark.usefixtures("clean_dbs")
class TestLocalReferenceRemap:
    """A dedup keeps *identity's* pre-existing id, not the source row's id.

    Found live during the staging cutover: an account already existed in
    identity under its own id before this script ever ran, so the dedup
    correctly skipped re-inserting it — but nothing re-pointed the source
    database's own domain rows (decks, sessions, settings, …) from the
    old local id onto identity's id. They silently kept referencing a
    UUID identity had never heard of, so a real person's decks vanished
    the moment `barrins_api` started reading `owner_id` as an opaque
    identity id instead of a local FK.
    """

    def test_dedup_remaps_plain_owner_columns_to_identity_id(self, tmp_path):
        old_id = str(uuid.uuid4())
        identity_id = str(uuid.uuid4())
        _seed_target(
            [{"id": identity_id, "email": "dup@example.com", "username": "dup"}]
        )
        _seed_source([{"id": old_id, "email": "dup@example.com"}])
        _seed_source_domain_row(
            "ts_personal_decks", id=str(uuid.uuid4()), owner_id=old_id, name="Deck A"
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        decks = _source_rows("ts_personal_decks", "owner_id")
        assert [str(d["owner_id"]) for d in decks] == [identity_id]
        assert result.remapped_users == [("dup@example.com", old_id, identity_id)]
        assert result.remap_row_counts["ts_personal_decks"] == 1

    def test_matching_uuid_dedup_needs_no_remap(self, tmp_path):
        same_id = str(uuid.uuid4())
        _seed_target([{"id": same_id, "email": "same@example.com", "username": "same"}])
        _seed_source([{"id": same_id, "email": "same@example.com"}])
        _seed_source_domain_row(
            "ts_personal_decks", id=str(uuid.uuid4()), owner_id=same_id, name="Deck A"
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        assert result.remapped_users == []
        assert result.remap_row_counts == {}

    def test_dedup_settings_collision_keeps_old_row_discards_blank_new_one(
        self, tmp_path
    ):
        old_id = str(uuid.uuid4())
        identity_id = str(uuid.uuid4())
        _seed_target(
            [{"id": identity_id, "email": "dup@example.com", "username": "dup"}]
        )
        _seed_source([{"id": old_id, "email": "dup@example.com"}])
        # old_id's row holds the person's real preferences; identity_id's
        # row is a blank default auto-created by an early login.
        _seed_source_domain_row("ts_user_settings", user_id=old_id, note="real prefs")
        _seed_source_domain_row(
            "ts_user_settings", user_id=identity_id, note="blank default"
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        rows = _source_rows("ts_user_settings", "user_id", "note")
        assert len(rows) == 1
        assert str(rows[0]["user_id"]) == identity_id
        assert rows[0]["note"] == "real prefs"
        assert result.settings_merged == ["dup@example.com"]

    def test_dedup_team_members_collision_is_left_untouched_and_flagged(self, tmp_path):
        old_id = str(uuid.uuid4())
        identity_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        _seed_target(
            [{"id": identity_id, "email": "dup@example.com", "username": "dup"}]
        )
        _seed_source([{"id": old_id, "email": "dup@example.com"}])
        # Same team, both ids already present -- ambiguous, must not be
        # silently merged or deleted.
        _seed_source_domain_row("ts_team_members", team_id=team_id, user_id=old_id)
        _seed_source_domain_row("ts_team_members", team_id=team_id, user_id=identity_id)

        result = run(
            _SRC_URL, _TGT_URL, dry_run=False, report_path=str(tmp_path / "r.txt")
        )

        memberships = {
            str(r["user_id"]) for r in _source_rows("ts_team_members", "user_id")
        }
        assert memberships == {old_id, identity_id}  # both rows untouched
        assert len(result.manual_review) == 1
        assert "dup@example.com" in result.manual_review[0]
        assert "ts_team_members" in result.manual_review[0]
        report_text = (tmp_path / "r.txt").read_text(encoding="utf-8")
        assert "NEEDS MANUAL REVIEW" in report_text
        assert "dup@example.com" in report_text

    def test_dry_run_rolls_back_source_side_remap_too(self, tmp_path):
        old_id = str(uuid.uuid4())
        identity_id = str(uuid.uuid4())
        _seed_target(
            [{"id": identity_id, "email": "dup@example.com", "username": "dup"}]
        )
        _seed_source([{"id": old_id, "email": "dup@example.com"}])
        _seed_source_domain_row(
            "ts_personal_decks", id=str(uuid.uuid4()), owner_id=old_id, name="Deck A"
        )

        result = run(
            _SRC_URL, _TGT_URL, dry_run=True, report_path=str(tmp_path / "r.txt")
        )

        assert result.remap_row_counts.get("ts_personal_decks") == 1  # counted...
        decks = _source_rows("ts_personal_decks", "owner_id")
        assert str(decks[0]["owner_id"]) == old_id  # ...but rolled back
