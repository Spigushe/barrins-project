"""Add ts_match_games (+ ts_match_game_events), backfill from
ts_matches.game1/2/3/on_play (#123/#124)

Migration 1 of 2 (D1, 2026-09-15 decision — "Full normalization, migration
split in two"): creates `ts_match_games` and backfills one row per
historically-played game from every existing `ts_matches` row. The flat
`game1`/`game2`/`game3` columns are left untouched — still present, still
holding their original data — for this migration's rollback window.
`on_play` is the one necessary exception: it was `NOT NULL` with no
default, and application code stops populating it as of this deploy (see
`app.models.tamiyo_scroll.TSMatch.on_play`'s docstring), so it is widened
to nullable here. No existing row's `on_play` value is changed.

Also creates `ts_match_game_events` (D2's second amendment, 2026-09-15):
individual logged mulligans/misplays, one row per event, each with its
own optional comment — `ts_match_games.player_mulligans`/
`opponent_mulligans`/`player_misplays`/`opponent_misplays` become a
backend-only derived cache of `len(events)` per `(side, kind)` rather
than a directly client-written counter (see `TSMatchGame`'s docstring).
The backfill above never populates those four counters or any event rows
— a historical, pre-feature game has no tracking concept at all, not
"confirmed zero" (they stay `NULL`, same as before this amendment).

Migration 2 — a later, separate deploy, only after a production
verification window (row-for-row check: `ts_match_games` row count and
values per match match the pre-migration `game1`/`game2`/`game3`/
`on_play` data) — drops `game1`/`game2`/`game3`/`on_play` entirely. Not
part of this revision (out of scope per the accepted plan).

Revision ID: c4f8a1d3e9b6
Revises: a7c2e9f13b40
Create Date: 2026-09-15 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f8a1d3e9b6"
down_revision: str | Sequence[str] | None = "a7c2e9f13b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Reuses the existing `ts_game_result` PG enum type (created by the
# original tamiyo-scroll-tracker migration) — never a second type for the
# same three values. Must be `postgresql.ENUM`, not the generic `sa.Enum`:
# confirmed against a live database that a generic `sa.Enum(..., create_type=
# False)` still re-emits `CREATE TYPE` (and fails with `DuplicateObject`)
# when used as a column in `op.create_table` — the dialect-specific class is
# what actually honors `create_type=False` in that code path.
_GAME_RESULT = postgresql.ENUM(
    "win", "loss", "draw", name="ts_game_result", create_type=False
)

_matches = sa.table(
    "ts_matches",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("on_play", sa.Boolean),
    sa.column("game1", _GAME_RESULT),
    sa.column("game2", _GAME_RESULT),
    sa.column("game3", _GAME_RESULT),
)
_match_games = sa.table(
    "ts_match_games",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("match_id", postgresql.UUID(as_uuid=True)),
    sa.column("game_number", sa.Integer),
    sa.column("on_play", sa.Boolean),
    sa.column("result", _GAME_RESULT),
)


def _backfill(bind: sa.engine.Connection) -> None:
    """One `ts_match_games` row per non-NULL `game{N}` on every existing
    match — `game_number=1` also carries the match's old `on_play` (the
    only game whose starting player was ever historically tracked);
    `game_number` 2/3 backfill rows get `on_play=NULL` (D1/`TSMatchGame`
    docstring)."""
    rows = bind.execute(
        sa.select(
            _matches.c.id,
            _matches.c.on_play,
            _matches.c.game1,
            _matches.c.game2,
            _matches.c.game3,
        )
    ).all()

    for match_id, on_play, game1, game2, game3 in rows:
        for game_number, (result, game_on_play) in enumerate(
            ((game1, on_play), (game2, None), (game3, None)), start=1
        ):
            if result is None:
                continue
            bind.execute(
                sa.insert(_match_games).values(
                    id=uuid.uuid4(),
                    match_id=match_id,
                    game_number=game_number,
                    on_play=game_on_play,
                    result=result,
                )
            )


def upgrade() -> None:
    op.create_table(
        "ts_match_games",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("game_number", sa.Integer, nullable=False),
        sa.Column("on_play", sa.Boolean, nullable=True),
        sa.Column("result", _GAME_RESULT, nullable=True),
        # Backend-only derived cache of `len(events)` per `(side, kind)` in
        # `ts_match_game_events` below — never populated by this migration's
        # backfill (see module docstring), only ever written by
        # `app/api/tamiyo_scroll/matches.py::_apply_payload` going forward.
        sa.Column("player_mulligans", sa.Integer, nullable=True),
        sa.Column("opponent_mulligans", sa.Integer, nullable=True),
        sa.Column("player_misplays", sa.Integer, nullable=True),
        sa.Column("opponent_misplays", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("match_id", "game_number", name="uq_ts_match_games_number"),
        sa.CheckConstraint(
            "game_number BETWEEN 1 AND 3", name="ck_ts_match_games_number_range"
        ),
        sa.CheckConstraint(
            "player_mulligans IS NULL OR player_mulligans BETWEEN 0 AND 7",
            name="ck_ts_match_games_player_mulligans_range",
        ),
        sa.CheckConstraint(
            "opponent_mulligans IS NULL OR opponent_mulligans BETWEEN 0 AND 7",
            name="ck_ts_match_games_opponent_mulligans_range",
        ),
        sa.CheckConstraint(
            "player_misplays IS NULL OR player_misplays >= 0",
            name="ck_ts_match_games_player_misplays_range",
        ),
        sa.CheckConstraint(
            "opponent_misplays IS NULL OR opponent_misplays >= 0",
            name="ck_ts_match_games_opponent_misplays_range",
        ),
    )

    op.create_table(
        "ts_match_game_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_match_games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "side",
            sa.Enum("player", "opponent", name="ts_match_event_side"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum("mulligan", "misplay", name="ts_match_event_kind"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "game_id",
            "side",
            "kind",
            "sequence",
            name="uq_ts_match_game_events_position",
        ),
        sa.CheckConstraint(
            "sequence >= 1", name="ck_ts_match_game_events_sequence_min"
        ),
    )

    _backfill(op.get_bind())

    # See module docstring: the one necessary exception to "don't touch
    # the flat columns" — nullability only, no data altered or lost.
    op.alter_column("ts_matches", "on_play", nullable=True)


def downgrade() -> None:
    """Drops `ts_match_game_events` and `ts_match_games` (in that FK
    order). `ts_matches.on_play` is intentionally left nullable rather
    than reverted to `NOT NULL` — a match created while this migration was
    applied may carry `NULL` there (application code stopped populating
    it, per D1), so re-imposing `NOT NULL` here could fail against data
    accumulated since upgrade. Same lossy-downgrade precedent as
    `e91a4c7f2b56` (backfills aren't perfectly reversible).
    """
    op.drop_table("ts_match_game_events")
    op.drop_table("ts_match_games")
    op.execute("DROP TYPE IF EXISTS ts_match_event_side")
    op.execute("DROP TYPE IF EXISTS ts_match_event_kind")
