"""Unit tests for app/services/tamiyo_scroll/stats.py (pure functions)."""

import uuid

from app.models.tamiyo_scroll import (
    ArchetypeCategory,
    ExpectedLevel,
    GameResult,
    TSMatch,
    TSMetaDeck,
)
from app.services.tamiyo_scroll.stats import (
    _ratio,
    _tally_games,
    _winrate,
    compute_archetype_summary,
    compute_matchup_summary,
)


def _match(
    *,
    opponent_deck_id: uuid.UUID,
    on_play: bool = True,
    game1: GameResult | None = None,
    game2: GameResult | None = None,
    game3: GameResult | None = None,
    personal_deck_id: uuid.UUID | None = None,
) -> TSMatch:
    return TSMatch(
        owner_id=uuid.uuid4(),
        personal_deck_id=personal_deck_id or uuid.uuid4(),
        opponent_deck_id=opponent_deck_id,
        on_play=on_play,
        game1=game1,
        game2=game2,
        game3=game3,
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
        assert control["decks"] == [{"id": deck.id, "name": deck.name, "winrate": None}]
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
