"""Model-level tests for `TSMatchGame`/`TSMatchGameEvent` (#123/#124):
`CheckConstraint` bounds, and Migration 1's
(`add_ts_match_games_and_backfill`) backfill correctness.

Uses `db_session`/ORM objects directly against the real (test) database,
same style as `tests/scripture/test_models.py` — these are DB-enforced
constraints and a migration data function, not HTTP routes.
"""

import uuid
from importlib import import_module

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    CardGame,
    ExpectedLevel,
    GameResult,
    MatchEventKind,
    MatchEventSide,
    TSMatch,
    TSMatchGame,
    TSMatchGameEvent,
    TSMetaDeck,
    TSPersonalDeck,
)

_migration = import_module(
    "alembic.versions.c4f8a1d3e9b6_add_ts_match_games_and_backfill"
)


@pytest.fixture()
async def match(db_session) -> TSMatch:
    owner_id = uuid.uuid4()
    personal_deck = TSPersonalDeck(
        owner_id=owner_id,
        name="Mono Red",
        game=CardGame.magic,
        category=ArchetypeCategory.aggro,
    )
    db_session.add(personal_deck)
    await db_session.flush()

    meta_deck = TSMetaDeck(
        owner_id=owner_id,
        personal_deck_id=personal_deck.id,
        name="Burn",
        category=ArchetypeCategory.aggro,
        expected=ExpectedLevel.as_expected,
    )
    db_session.add(meta_deck)
    await db_session.flush()

    ts_match = TSMatch(
        owner_id=owner_id,
        personal_deck_id=personal_deck.id,
        opponent_deck_id=meta_deck.id,
    )
    db_session.add(ts_match)
    await db_session.commit()
    await db_session.refresh(ts_match)
    return ts_match


class TestCheckConstraints:
    async def test_game_number_out_of_range_is_rejected(
        self, db_session, match: TSMatch
    ):
        db_session.add(TSMatchGame(match_id=match.id, game_number=4))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_player_mulligans_above_seven_is_rejected(
        self, db_session, match: TSMatch
    ):
        """London mulligan (D4): hand size 7 - mulligans can't go negative."""
        db_session.add(
            TSMatchGame(match_id=match.id, game_number=1, player_mulligans=8)
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_negative_mulligans_is_rejected(self, db_session, match: TSMatch):
        db_session.add(
            TSMatchGame(match_id=match.id, game_number=1, player_mulligans=-1)
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_negative_misplays_is_rejected(self, db_session, match: TSMatch):
        db_session.add(
            TSMatchGame(match_id=match.id, game_number=1, opponent_misplays=-1)
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_in_range_values_are_accepted(self, db_session, match: TSMatch):
        db_session.add(
            TSMatchGame(
                match_id=match.id,
                game_number=1,
                player_mulligans=7,
                opponent_mulligans=0,
                player_misplays=0,
                opponent_misplays=12,
            )
        )
        await db_session.commit()

    async def test_duplicate_game_number_is_rejected(self, db_session, match: TSMatch):
        db_session.add(TSMatchGame(match_id=match.id, game_number=1))
        await db_session.commit()
        db_session.add(TSMatchGame(match_id=match.id, game_number=1))
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.fixture()
async def game(db_session, match: TSMatch) -> TSMatchGame:
    ts_game = TSMatchGame(match_id=match.id, game_number=1)
    db_session.add(ts_game)
    await db_session.commit()
    await db_session.refresh(ts_game)
    return ts_game


class TestMatchGameEventCheckConstraints:
    """#123/#124, D2's second amendment (2026-09-15)."""

    async def test_sequence_zero_is_rejected(self, db_session, game: TSMatchGame):
        db_session.add(
            TSMatchGameEvent(
                game_id=game.id,
                side=MatchEventSide.player,
                kind=MatchEventKind.mulligan,
                sequence=0,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_duplicate_position_is_rejected(self, db_session, game: TSMatchGame):
        db_session.add(
            TSMatchGameEvent(
                game_id=game.id,
                side=MatchEventSide.player,
                kind=MatchEventKind.mulligan,
                sequence=1,
            )
        )
        await db_session.commit()
        db_session.add(
            TSMatchGameEvent(
                game_id=game.id,
                side=MatchEventSide.player,
                kind=MatchEventKind.mulligan,
                sequence=1,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_same_sequence_different_side_or_kind_is_accepted(
        self, db_session, game: TSMatchGame
    ):
        """`sequence` is scoped per `(game, side, kind)` — the same number
        reused across different groups is not a conflict."""
        db_session.add_all(
            [
                TSMatchGameEvent(
                    game_id=game.id,
                    side=MatchEventSide.player,
                    kind=MatchEventKind.mulligan,
                    sequence=1,
                ),
                TSMatchGameEvent(
                    game_id=game.id,
                    side=MatchEventSide.opponent,
                    kind=MatchEventKind.mulligan,
                    sequence=1,
                ),
                TSMatchGameEvent(
                    game_id=game.id,
                    side=MatchEventSide.player,
                    kind=MatchEventKind.misplay,
                    sequence=1,
                ),
            ]
        )
        await db_session.commit()

    async def test_cascade_deletes_with_its_game(self, db_session, game: TSMatchGame):
        db_session.add(
            TSMatchGameEvent(
                game_id=game.id,
                side=MatchEventSide.player,
                kind=MatchEventKind.mulligan,
                sequence=1,
            )
        )
        await db_session.commit()

        await db_session.delete(game)
        await db_session.commit()

        result = await db_session.execute(
            select(TSMatchGameEvent).where(TSMatchGameEvent.game_id == game.id)
        )
        assert list(result.scalars().all()) == []


class TestMigrationBackfill:
    """Migration 1's `_backfill`: one `ts_match_games` row per non-NULL
    `game{N}`, game 1 also carrying the match's old `on_play`."""

    async def test_backfills_one_row_per_played_game(
        self, db_connection, db_session, match: TSMatch
    ):
        # Simulate historical, pre-#123/#124 data: flat columns populated
        # directly (bypassing the API, which no longer writes them).
        await db_session.execute(
            TSMatch.__table__.update()
            .where(TSMatch.id == match.id)
            .values(
                on_play=True,
                game1=GameResult.win,
                game2=GameResult.loss,
                game3=None,
            )
        )
        await db_session.commit()

        await db_connection.run_sync(lambda conn: _migration._backfill(conn))

        result = await db_session.execute(
            select(TSMatchGame)
            .where(TSMatchGame.match_id == match.id)
            .order_by(TSMatchGame.game_number)
        )
        games = list(result.scalars().all())
        assert [g.game_number for g in games] == [1, 2]
        assert games[0].result == GameResult.win
        assert games[0].on_play is True
        assert games[1].result == GameResult.loss
        # Only game 1's `on_play` was ever historically tracked.
        assert games[1].on_play is None
        # D2's second amendment: the backfill never populates the derived
        # counter cache or any events — a historical, pre-feature game has
        # no tracking concept at all, not "confirmed zero" (D8).
        assert games[0].player_mulligans is None
        assert games[0].player_misplays is None
        assert games[0].events == []

    async def test_no_played_games_backfills_nothing(
        self, db_connection, db_session, match: TSMatch
    ):
        await db_connection.run_sync(lambda conn: _migration._backfill(conn))

        result = await db_session.execute(
            select(TSMatchGame).where(TSMatchGame.match_id == match.id)
        )
        assert list(result.scalars().all()) == []
