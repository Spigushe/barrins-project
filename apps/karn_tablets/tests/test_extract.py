from datetime import date

import pandas as pd
import pytest

from karn_tablets import extract


class TestLoadDecklistsFromDf:
    def test_splits_mainboard_and_sideboard_by_deck(self):
        df = pd.DataFrame(
            [
                {
                    "deck_id": "d1",
                    "card_uuid": "sol-ring",
                    "count": 1,
                    "is_sideboard": False,
                },
                {
                    "deck_id": "d1",
                    "card_uuid": "swords",
                    "count": 1,
                    "is_sideboard": True,
                },
                {
                    "deck_id": "d2",
                    "card_uuid": "sol-ring",
                    "count": 1,
                    "is_sideboard": False,
                },
            ]
        )
        result = extract.load_decklists_from_df(df)
        assert len(result) == 2
        assert result[0].mainboard == {"sol-ring": 1}
        assert result[0].sideboard == {"swords": 1}
        assert result[1].mainboard == {"sol-ring": 1}
        assert result[1].sideboard == {}

    def test_sums_duplicate_card_rows(self):
        # Same card appearing in two rows for one deck (shouldn't happen
        # given bs_deck_cards' own unique constraint, but the aggregation
        # should still be correct if it ever did).
        df = pd.DataFrame(
            [
                {
                    "deck_id": "d1",
                    "card_uuid": "plains",
                    "count": 5,
                    "is_sideboard": False,
                },
                {
                    "deck_id": "d1",
                    "card_uuid": "plains",
                    "count": 3,
                    "is_sideboard": False,
                },
            ]
        )
        result = extract.load_decklists_from_df(df)
        assert result[0].mainboard == {"plains": 8}

    def test_one_decklist_per_distinct_deck_id(self):
        df = pd.DataFrame(
            [
                {"deck_id": "z", "card_uuid": "a", "count": 1, "is_sideboard": False},
                {"deck_id": "a", "card_uuid": "a", "count": 1, "is_sideboard": False},
            ]
        )
        result = extract.load_decklists_from_df(df)
        assert len(result) == 2


class TestLoadDeckCards:
    def test_drops_unresolved_card_names(self, monkeypatch: pytest.MonkeyPatch):
        fake_df = pd.DataFrame(
            [
                {
                    "deck_id": "d1",
                    "card_uuid": "sol-ring",
                    "count": 1,
                    "is_sideboard": False,
                    "tournament_id": "t1",
                    "date": "2026-05-10",
                    "players_count": 8,
                },
                {
                    "deck_id": "d1",
                    "card_uuid": None,  # unresolved -- LEFT JOIN LATERAL found nothing
                    "count": 1,
                    "is_sideboard": False,
                    "tournament_id": "t1",
                    "date": "2026-05-10",
                    "players_count": 8,
                },
            ]
        )
        monkeypatch.setattr(extract, "read_sql", lambda *_a, **_kw: fake_df)
        result = extract.load_deck_cards(date(2026, 5, 1), date(2026, 5, 31))
        assert len(result) == 1
        assert result.iloc[0]["card_uuid"] == "sol-ring"

    def test_empty_result_is_returned_as_is(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(extract, "read_sql", lambda *_a, **_kw: pd.DataFrame())
        result = extract.load_deck_cards(date(2026, 5, 1), date(2026, 5, 31))
        assert result.empty


class TestEngine:
    def test_raises_when_database_url_is_unset(self, monkeypatch: pytest.MonkeyPatch):
        extract._engine.cache_clear()
        monkeypatch.setattr(extract, "database_url", lambda: None)
        with pytest.raises(RuntimeError, match="KARN_TABLETS_DATABASE_URL_RO"):
            extract._engine()
        extract._engine.cache_clear()
