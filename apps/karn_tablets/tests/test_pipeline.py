from datetime import date

import pandas as pd
import pytest

from karn_tablets import pipeline
from karn_tablets.windowing import Window, WindowKind

_WINDOW = Window(
    kind=WindowKind.rolling_30d, date_from=date(2026, 5, 1), date_to=date(2026, 5, 31)
)


class TestRun:
    def test_empty_window_returns_zero_archetypes(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            pipeline.clustering, "clusterize_by_window", lambda *_a, **_kw: []
        )
        result = pipeline.run(_WINDOW)
        assert result.total_decks == 0
        assert result.archetypes == []
        assert result.window == _WINDOW

    def test_archetype_shares_sum_to_one(
        self,
        monkeypatch: pytest.MonkeyPatch,
        deck_cards_df: pd.DataFrame,
        cards_df: pd.DataFrame,
    ):
        from karn_tablets.clustering import clusterize
        from karn_tablets.features import flatten_features_dict

        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        coordinates = clusterize(df_feat)

        monkeypatch.setattr(
            pipeline.clustering, "clusterize_by_window", lambda *_a, **_kw: coordinates
        )
        monkeypatch.setattr(
            pipeline.extract, "load_deck_cards", lambda *_a, **_kw: deck_cards_df
        )
        monkeypatch.setattr(pipeline.extract, "load_cards_features", lambda: cards_df)

        result = pipeline.run(_WINDOW)
        assert result.total_decks == 3
        total_share = sum(a.share for a in result.archetypes)
        assert total_share == pytest.approx(1.0, abs=0.01)

    def test_representative_decklist_uses_card_names_not_uuids(
        self,
        monkeypatch: pytest.MonkeyPatch,
        deck_cards_df: pd.DataFrame,
        cards_df: pd.DataFrame,
    ):
        from karn_tablets.clustering import clusterize
        from karn_tablets.features import flatten_features_dict

        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        coordinates = clusterize(df_feat)

        monkeypatch.setattr(
            pipeline.clustering, "clusterize_by_window", lambda *_a, **_kw: coordinates
        )
        monkeypatch.setattr(
            pipeline.extract, "load_deck_cards", lambda *_a, **_kw: deck_cards_df
        )
        monkeypatch.setattr(pipeline.extract, "load_cards_features", lambda: cards_df)

        result = pipeline.run(_WINDOW)
        all_card_names = {
            name
            for a in result.archetypes
            for name in (*a.representative_mainboard, *a.representative_sideboard)
        }
        known_names = {c["name"] for c in cards_df.to_dict("records")}
        assert all_card_names <= known_names

    def test_pipeline_version_and_timestamp_are_recorded(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            pipeline.clustering, "clusterize_by_window", lambda *_a, **_kw: []
        )
        result = pipeline.run(_WINDOW)
        assert result.pipeline_version == pipeline.PIPELINE_VERSION
        assert result.generated_at is not None
