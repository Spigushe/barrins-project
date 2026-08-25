"""Add personal_deck_id + updated_at to ts_meta_decks, backfill (F10)

Revision ID: e91a4c7f2b56
Revises: b7d1f4a290ec
Create Date: 2026-08-18 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e91a4c7f2b56"
down_revision: str | Sequence[str] | None = "b7d1f4a290ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ARCHETYPE_CATEGORY = sa.Enum(
    "aggro",
    "midrange",
    "control",
    "combo",
    name="ts_archetype_category",
    create_type=False,
)
_CARD_GAME = sa.Enum(
    "magic",
    "yu_gi_oh",
    "pokemon",
    "flesh_and_blood",
    "one_piece",
    "lorcana",
    "star_wars_unlimited",
    "digimon",
    "cardfight_vanguard",
    "riftbound",
    "other",
    name="ts_card_game",
    create_type=False,
)
_EXPECTED_LEVEL = sa.Enum(
    "as_expected",
    "more_expected",
    "less_expected",
    name="ts_expected_level",
    create_type=False,
)

_meta_decks = sa.table(
    "ts_meta_decks",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("owner_id", postgresql.UUID(as_uuid=True)),
    sa.column("personal_deck_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("tier", sa.Numeric),
    sa.column("category", _ARCHETYPE_CATEGORY),
    sa.column("game", _CARD_GAME),
    sa.column("decklist_notes", sa.Text),
    sa.column("top8", sa.Integer),
    sa.column("presence", sa.Integer),
    sa.column("expected", _EXPECTED_LEVEL),
    sa.column("tests_status", sa.Text),
    sa.column("archived_at", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
_matches = sa.table(
    "ts_matches",
    sa.column("owner_id", postgresql.UUID(as_uuid=True)),
    sa.column("personal_deck_id", postgresql.UUID(as_uuid=True)),
    sa.column("opponent_deck_id", postgresql.UUID(as_uuid=True)),
)
_personal_decks = sa.table(
    "ts_personal_decks",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("owner_id", postgresql.UUID(as_uuid=True)),
    sa.column("game", _CARD_GAME),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
_user_settings = sa.table(
    "ts_user_settings",
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("active_personal_deck_id", postgresql.UUID(as_uuid=True)),
)


def _game_for_personal_deck(
    bind: sa.engine.Connection, personal_deck_id: uuid.UUID
) -> str:
    return bind.execute(
        sa.select(_personal_decks.c.game).where(
            _personal_decks.c.id == personal_deck_id
        )
    ).scalar_one()


def _backfill(bind: sa.engine.Connection) -> None:
    """Derives each roster row's owning personal deck(s) from match
    history, the same grouping `_sync_opponent_deck_games` already used
    for `game` — see F10 doc items 1-3.

    - Exactly one personal deck fought this roster deck: assign it.
    - More than one: duplicate-and-allocate — one row per personal deck,
      repointing only the matches that belong to each duplicate.
    - No match history at all (an "Expected metagame" entry never
      actually played): assign to the owner's `active_personal_deck_id`,
      or — if that's unset — the owner's oldest personal deck. Confirmed
      with the user that an owner with roster rows always owns at least
      one personal deck (the Metagame tab requires one), so this always
      resolves.

    Every branch also (re)sets `game` from the resolved personal deck's
    own `game`, never trusting the row's existing value: `game` was only
    ever populated by `_sync_opponent_deck_games` (an active-deck PATCH)
    or `create_meta_deck`'s own explicit assignment, neither of which
    covered every pre-F10 creation path — plenty of legacy rows carry
    `game IS NULL` despite belonging to a deck whose game is well known.
    Left alone, list_meta_decks's `"game"`-scope filter (`d.game ==
    active_game`) would silently drop those rows forever, since NULL
    never equals any `CardGame` value.
    """
    all_decks = bind.execute(sa.select(_meta_decks.c.id, _meta_decks.c.owner_id)).all()

    for deck_id, owner_id in all_decks:
        distinct_personal_deck_ids = [
            row[0]
            for row in bind.execute(
                sa.select(_matches.c.personal_deck_id)
                .where(
                    _matches.c.opponent_deck_id == deck_id,
                    _matches.c.owner_id == owner_id,
                )
                .distinct()
            ).all()
        ]

        if distinct_personal_deck_ids:
            first_id, *rest_ids = distinct_personal_deck_ids
            bind.execute(
                sa.update(_meta_decks)
                .where(_meta_decks.c.id == deck_id)
                .values(
                    personal_deck_id=first_id,
                    game=_game_for_personal_deck(bind, first_id),
                )
            )
            if rest_ids:
                original = (
                    bind.execute(
                        sa.select(_meta_decks).where(_meta_decks.c.id == deck_id)
                    )
                    .mappings()
                    .one()
                )
                for extra_personal_deck_id in rest_ids:
                    new_id = uuid.uuid4()
                    bind.execute(
                        sa.insert(_meta_decks).values(
                            id=new_id,
                            owner_id=original["owner_id"],
                            personal_deck_id=extra_personal_deck_id,
                            name=original["name"],
                            tier=original["tier"],
                            category=original["category"],
                            game=_game_for_personal_deck(bind, extra_personal_deck_id),
                            decklist_notes=original["decklist_notes"],
                            top8=original["top8"],
                            presence=original["presence"],
                            expected=original["expected"],
                            tests_status=original["tests_status"],
                            archived_at=original["archived_at"],
                            created_at=original["created_at"],
                            updated_at=original["updated_at"],
                        )
                    )
                    bind.execute(
                        sa.update(_matches)
                        .where(
                            _matches.c.opponent_deck_id == deck_id,
                            _matches.c.personal_deck_id == extra_personal_deck_id,
                        )
                        .values(opponent_deck_id=new_id)
                    )
            continue

        active_id = bind.execute(
            sa.select(_user_settings.c.active_personal_deck_id).where(
                _user_settings.c.user_id == owner_id
            )
        ).scalar_one_or_none()
        if active_id is None:
            active_id = bind.execute(
                sa.select(_personal_decks.c.id)
                .where(_personal_decks.c.owner_id == owner_id)
                .order_by(_personal_decks.c.created_at.asc())
                .limit(1)
            ).scalar_one()
        bind.execute(
            sa.update(_meta_decks)
            .where(_meta_decks.c.id == deck_id)
            .values(
                personal_deck_id=active_id,
                game=_game_for_personal_deck(bind, active_id),
            )
        )


def upgrade() -> None:
    op.add_column(
        "ts_meta_decks",
        sa.Column(
            "personal_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_personal_decks.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ts_meta_decks_personal_deck_id",
        "ts_meta_decks",
        ["personal_deck_id"],
    )
    # `updated_at` (needed by F10 items 5/6 — "most recently updated row
    # wins"). Existing rows have never been edited through this new
    # tracking, so `created_at` is the correct starting value — added
    # nullable first so the backfill controls the value, rather than a
    # `server_default=func.now()` NOT NULL add stamping every historical
    # row with the migration's own run time.
    op.add_column(
        "ts_meta_decks",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE ts_meta_decks SET updated_at = created_at")
    op.alter_column(
        "ts_meta_decks", "updated_at", nullable=False, server_default=sa.func.now()
    )

    _backfill(op.get_bind())

    op.alter_column("ts_meta_decks", "personal_deck_id", nullable=False)


def downgrade() -> None:
    """Drops both columns. Duplicates created by the backfill are not
    un-duplicated — a downgrade of a data migration is already lossy
    elsewhere in this repo (cf. b6e4d18a5f3c)."""
    op.drop_index("ix_ts_meta_decks_personal_deck_id", table_name="ts_meta_decks")
    op.drop_column("ts_meta_decks", "personal_deck_id")
    op.drop_column("ts_meta_decks", "updated_at")
