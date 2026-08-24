"""Split ts_card_tests into card logs + ts_card_test_evaluations (S17)

`opponent_deck_id`/`rating` move off `ts_card_tests` onto a new
`ts_card_test_evaluations` table (one log, many evaluations), per the
user's 2026-08-24 decision (S17, Option A). Existing rows are backfilled
one evaluation each, carrying their old `opponent_deck_id`/`rating`
unchanged -- no feedback data lost, mirroring S16's own "keep existing
rows as-is" precedent (see
docs/project/v2.0.0-bump/s17-card-log-matchup-evaluations).

`opponent_deck_id` is nullable on `ts_card_tests` today, but required on
the new evaluation table -- an evaluation is specifically a match-up, so
one without an opponent deck isn't meaningful. Checked against the dev
database (2026-08-24): rows with a null `opponent_deck_id` do exist in
practice (a rating logged with no specific matchup in mind). Such a row
cannot become a valid evaluation (opponent is required), so it is
skipped by the backfill rather than forced -- its card log (removed/
added names, own notes) is unaffected, it just ends up with zero
evaluations post-migration instead of one, the same state a freshly
created S17 card log with no evaluation yet would have. Its old rating
is the only piece of data that doesn't carry forward, since there is no
non-lossy place left to put a rating that was never actually tied to an
opponent.

Revision ID: 4f9a00bfb15a
Revises: 71b1aa5022dd
Create Date: 2026-08-24 00:00:05.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "4f9a00bfb15a"
down_revision: str | Sequence[str] | None = "71b1aa5022dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ts_card_test_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_card_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opponent_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_meta_decks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_check_constraint(
        "ck_ts_card_test_evaluations_rating_range",
        "ts_card_test_evaluations",
        "rating BETWEEN 1 AND 5",
    )

    op.execute(
        """
        INSERT INTO ts_card_test_evaluations
            (id, test_id, opponent_deck_id, rating, notes, created_at)
        SELECT gen_random_uuid(), id, opponent_deck_id, rating, notes, created_at
        FROM ts_card_tests
        WHERE opponent_deck_id IS NOT NULL
        """
    )

    op.drop_constraint("ck_ts_card_tests_rating_range", "ts_card_tests", type_="check")
    op.drop_column("ts_card_tests", "opponent_deck_id")
    op.drop_column("ts_card_tests", "rating")


def downgrade() -> None:
    op.add_column(
        "ts_card_tests",
        sa.Column(
            "opponent_deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ts_meta_decks.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("ts_card_tests", sa.Column("rating", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_ts_card_tests_rating_range", "ts_card_tests", "rating BETWEEN 1 AND 5"
    )

    # Degenerate: a log with more than one evaluation only gets its most
    # recent evaluation's values back -- the rest are lost on downgrade,
    # an accepted, documented lossy path (not the upgrade path).
    op.execute(
        """
        UPDATE ts_card_tests
        SET opponent_deck_id = latest.opponent_deck_id, rating = latest.rating
        FROM (
            SELECT DISTINCT ON (test_id) test_id, opponent_deck_id, rating
            FROM ts_card_test_evaluations
            ORDER BY test_id, created_at DESC
        ) AS latest
        WHERE ts_card_tests.id = latest.test_id
        """
    )

    op.drop_table("ts_card_test_evaluations")
