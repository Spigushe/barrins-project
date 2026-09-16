"""Unit tests for app/services/tamiyo_scroll/stats.py (pure functions)."""

import uuid
from dataclasses import dataclass, field

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    ExpectedLevel,
    GameResult,
    TSMetaDeck,
)
from app.services.tamiyo_scroll.stats import (
    _ratio,
    _tally_games,
    _winrate,
    compute_archetype_summary,
    compute_hand_size_and_misplay_averages,
    compute_matchup_summary,
)


@dataclass(frozen=True)
class _FakeGame:
    """Minimal stand-in for `TSMatchGame`/`EffectiveGame` — satisfies
    `stats.GameLike` structurally."""

    game_number: int
    on_play: bool | None = None
    result: GameResult | None = None
    player_mulligans: int | None = None
    opponent_mulligans: int | None = None
    player_misplays: int | None = None
    opponent_misplays: int | None = None


@dataclass(frozen=True)
class _FakeMatch:
    """Minimal stand-in for `TSMatch`/`EffectiveMatch` — satisfies
    `stats.MatchLike` structurally."""

    opponent_deck_id: uuid.UUID
    decklist_version_id: uuid.UUID | None = None
    games: tuple[_FakeGame, ...] = field(default_factory=tuple)
    is_readonly: bool = False


def _match(
    *,
    opponent_deck_id: uuid.UUID,
    on_play: bool = True,
    game1: GameResult | None = None,
    game2: GameResult | None = None,
    game3: GameResult | None = None,
    is_readonly: bool = False,
    player_mulligans: int | None = None,
    player_misplays: int | None = None,
    opponent_misplays: int | None = None,
) -> _FakeMatch:
    """Builds a `MatchLike` fixture. `on_play`/`game1`/`game2`/`game3` are
    convenience kwargs (pre-#123/#124 flat shape) translated into one
    `_FakeGame` per non-`None` result — `on_play` applies to every game
    the fixture builds (a real match's games each carry their own
    `on_play` post-#123/#124, but this generic per-game-tally fixture has
    no reason to model the historical-backfill "only game 1 tracked"
    case specifically — that's covered separately, at the migration
    level, in `test_match_games.py`)."""
    games: list[_FakeGame] = []
    for number, result in ((1, game1), (2, game2), (3, game3)):
        if result is None:
            continue
        games.append(
            _FakeGame(
                game_number=number,
                on_play=on_play,
                result=result,
                player_mulligans=player_mulligans if number == 1 else None,
                player_misplays=player_misplays if number == 1 else None,
                opponent_misplays=opponent_misplays if number == 1 else None,
            )
        )
    return _FakeMatch(
        opponent_deck_id=opponent_deck_id,
        games=tuple(games),
        is_readonly=is_readonly,
    )


def _meta_deck(
    *, name: str = "Deck", category: ArchetypeCategory = ArchetypeCategory.aggro
) -> TSMetaDeck:
    deck = TSMetaDeck(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name=name,
        category=category,
        expected=ExpectedLevel.as_expected,
    )
    return deck


class TestTallyGames:
    def test_empty_matches_returns_zeros(self):
        assert _tally_games([]) == (0, 0, 0)

    def test_counts_wins_losses_draws_across_games(self):
        opponent = uuid.uuid4()
        matches = [
            _match(
                opponent_deck_id=opponent,
                game1=GameResult.win,
                game2=GameResult.loss,
                game3=GameResult.draw,
            ),
            _match(opponent_deck_id=opponent, game1=GameResult.win, game2=None),
        ]
        assert _tally_games(matches) == (2, 1, 1)

    def test_ignores_null_games(self):
        matches = [_match(opponent_deck_id=uuid.uuid4(), game1=GameResult.win)]
        assert _tally_games(matches) == (1, 0, 0)

    def test_filters_by_on_play(self):
        opponent = uuid.uuid4()
        matches = [
            _match(opponent_deck_id=opponent, on_play=True, game1=GameResult.win),
            _match(opponent_deck_id=opponent, on_play=False, game1=GameResult.loss),
        ]
        assert _tally_games(matches, on_play=True) == (1, 0, 0)
        assert _tally_games(matches, on_play=False) == (0, 1, 0)


class TestWinrate:
    def test_no_decisive_games_returns_none(self):
        assert _winrate(0, 0) is None

    def test_computes_percentage(self):
        assert _winrate(3, 1) == 75.0

    def test_all_losses(self):
        assert _winrate(0, 4) == 0.0


class TestRatio:
    def test_formats_wins_dash_losses(self):
        assert _ratio(3, 1) == "3-1"

    def test_zero_zero(self):
        assert _ratio(0, 0) == "0-0"


class TestComputeArchetypeSummary:
    def test_returns_all_four_categories_even_when_empty(self):
        summaries = compute_archetype_summary([], [])
        categories = {s["category"] for s in summaries}
        assert categories == set(ArchetypeCategory)
        assert all(s["average_winrate"] is None for s in summaries)
        assert all(s["decks"] == [] for s in summaries)

    def test_deck_without_matches_has_none_winrate_and_excluded_from_average(self):
        deck = _meta_deck(category=ArchetypeCategory.control)
        summaries = compute_archetype_summary([deck], [])
        control = next(
            s for s in summaries if s["category"] == ArchetypeCategory.control
        )
        assert control["decks"] == [
            {
                "id": deck.id,
                "name": deck.name,
                "winrate": None,
                "is_readonly": False,
                "has_shared_data": False,
            }
        ]
        assert control["average_winrate"] is None

    def test_average_winrate_ignores_decks_without_data(self):
        deck_with_data = _meta_deck(name="A", category=ArchetypeCategory.combo)
        deck_without_data = _meta_deck(name="B", category=ArchetypeCategory.combo)
        matches = [
            _match(opponent_deck_id=deck_with_data.id, game1=GameResult.win),
            _match(opponent_deck_id=deck_with_data.id, game1=GameResult.win),
        ]
        summaries = compute_archetype_summary(
            [deck_with_data, deck_without_data], matches
        )
        combo = next(s for s in summaries if s["category"] == ArchetypeCategory.combo)
        assert combo["average_winrate"] == 100.0
        winrates = {d["name"]: d["winrate"] for d in combo["decks"]}
        assert winrates == {"A": 100.0, "B": None}

    def test_has_shared_data_true_when_an_own_deck_has_a_readonly_match(self):
        deck = _meta_deck(name="Mixed Deck", category=ArchetypeCategory.midrange)
        matches = [
            _match(opponent_deck_id=deck.id, game1=GameResult.win, is_readonly=False),
            _match(opponent_deck_id=deck.id, game1=GameResult.loss, is_readonly=True),
        ]
        summaries = compute_archetype_summary([deck], matches)
        midrange = next(
            s for s in summaries if s["category"] == ArchetypeCategory.midrange
        )
        assert midrange["decks"][0]["has_shared_data"] is True

    def test_has_shared_data_false_for_a_fully_readonly_deck(self):
        """A fully-foreign deck is flagged via is_readonly already — its own
        matches being read-only isn't additionally "mixed" data."""
        deck = _meta_deck(name="Foreign Deck", category=ArchetypeCategory.midrange)
        matches = [
            _match(opponent_deck_id=deck.id, game1=GameResult.win, is_readonly=True)
        ]
        summaries = compute_archetype_summary(
            [deck], matches, readonly_meta_deck_ids=frozenset({deck.id})
        )
        midrange = next(
            s for s in summaries if s["category"] == ArchetypeCategory.midrange
        )
        assert midrange["decks"][0]["is_readonly"] is True
        assert midrange["decks"][0]["has_shared_data"] is False

    def test_decks_sorted_by_name(self):
        deck_z = _meta_deck(name="Zoo", category=ArchetypeCategory.aggro)
        deck_a = _meta_deck(name="Affinity", category=ArchetypeCategory.aggro)
        summaries = compute_archetype_summary([deck_z, deck_a], [])
        aggro = next(s for s in summaries if s["category"] == ArchetypeCategory.aggro)
        assert [d["name"] for d in aggro["decks"]] == ["Affinity", "Zoo"]


class TestComputeMatchupSummary:
    def test_no_matches_returns_empty_rows_and_none_average(self):
        rows, average = compute_matchup_summary([], {})
        assert rows == []
        assert average is None

    def test_groups_by_opponent_and_computes_ratios(self):
        opponent = _meta_deck(name="Burn")
        matches = [
            _match(
                opponent_deck_id=opponent.id,
                on_play=True,
                game1=GameResult.win,
                game2=GameResult.loss,
            ),
            _match(opponent_deck_id=opponent.id, on_play=False, game1=GameResult.win),
        ]
        rows, average = compute_matchup_summary(matches, {opponent.id: opponent})
        assert len(rows) == 1
        row = rows[0]
        assert row["opponent_deck_name"] == "Burn"
        assert row["match_count"] == 2
        assert row["winrate_otp"] == 50.0
        assert row["ratio_otp"] == "1-1"
        assert row["winrate_otd"] == 100.0
        assert row["ratio_otd"] == "1-0"
        assert row["winrate_global"] == 66.67
        assert average == 66.67

    def test_unknown_opponent_deck_falls_back_to_placeholder_name(self):
        opponent_id = uuid.uuid4()
        matches = [_match(opponent_deck_id=opponent_id, game1=GameResult.win)]
        rows, _ = compute_matchup_summary(matches, {})
        assert rows[0]["opponent_deck_name"] == "?"

    def test_rows_sorted_by_opponent_name(self):
        deck_z = _meta_deck(name="Zoo")
        deck_a = _meta_deck(name="Affinity")
        matches = [
            _match(opponent_deck_id=deck_z.id, game1=GameResult.win),
            _match(opponent_deck_id=deck_a.id, game1=GameResult.win),
        ]
        rows, _ = compute_matchup_summary(
            matches, {deck_z.id: deck_z, deck_a.id: deck_a}
        )
        assert [r["opponent_deck_name"] for r in rows] == ["Affinity", "Zoo"]


class TestComputeHandSizeAndMisplayAverages:
    """#123/#124 (D4/D5/D6/D8)."""

    def test_no_games_yields_none_for_every_average(self):
        result = compute_hand_size_and_misplay_averages([])
        assert result == {
            "avg_hand_size": None,
            "avg_player_misplays": None,
            "avg_opponent_misplays": None,
        }

    def test_averages_ignore_games_with_no_entered_value(self):
        """D8: NULL ("not entered") is excluded, never treated as 0."""
        opponent = uuid.uuid4()
        matches = [
            _match(
                opponent_deck_id=opponent,
                game1=GameResult.win,
                player_mulligans=2,
                player_misplays=1,
                opponent_misplays=0,
            ),
            # No mulligan/misplay data entered for this game at all.
            _match(opponent_deck_id=opponent, game1=GameResult.loss),
        ]
        result = compute_hand_size_and_misplay_averages(matches)
        # avg(player_mulligans) = 2 (the second game's None is excluded,
        # not averaged in as 0) -> avg_hand_size = 7 - 2 = 5.
        assert result["avg_hand_size"] == 5.0
        assert result["avg_player_misplays"] == 1.0
        assert result["avg_opponent_misplays"] == 0.0

    def test_london_mulligan_formula(self):
        """D4: hand_size = 7 - mulligans."""
        opponent = uuid.uuid4()
        matches = [
            _match(opponent_deck_id=opponent, game1=GameResult.win, player_mulligans=0),
            _match(opponent_deck_id=opponent, game1=GameResult.win, player_mulligans=4),
        ]
        result = compute_hand_size_and_misplay_averages(matches)
        # avg(player_mulligans) = 2 -> avg_hand_size = 7 - 2 = 5.
        assert result["avg_hand_size"] == 5.0
