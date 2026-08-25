from datetime import date

import numpy as np
import pandas as pd
import pytest
from dc_calendar.windowing import Window, WindowKind

from karn_tablets import clustering
from karn_tablets.clustering import clusterize, suggest_clusters, suggest_clusters_bic
from karn_tablets.features import flatten_features_dict


class TestSuggestClusters:
    def test_fewer_than_three_points_returns_one(self):
        assert suggest_clusters(np.array([[0.0, 0.0], [1.0, 1.0]])) == 1

    def test_bounded_by_min_and_max(self):
        rng = np.random.default_rng(42)
        vectors = rng.normal(size=(20, 3))
        k = suggest_clusters(vectors, min_clusters=4, max_clusters=10)
        assert 4 <= k <= 10


class TestSuggestClustersBic:
    def test_fewer_than_two_points_returns_one(self):
        assert suggest_clusters_bic(np.array([[0.0, 0.0]])) == 1

    def test_bounded_by_min_and_max(self):
        rng = np.random.default_rng(42)
        vectors = rng.normal(size=(20, 3))
        k = suggest_clusters_bic(vectors, min_clusters=4, max_clusters=10)
        assert 4 <= k <= 10


class TestClusterize:
    def test_empty_features_returns_empty_list(self):
        assert clusterize(pd.DataFrame()) == []

    def test_every_deck_gets_a_coordinate(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        coords = clusterize(df_feat)
        assert {c.deck_id for c in coords} == {"deck-1", "deck-2", "deck-3"}

    def test_dbscan_algorithm_runs_without_error(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        coords = clusterize(df_feat, algorithm="dbscan")
        assert len(coords) == 3
        assert all(c.cluster >= 0 for c in coords)

    def test_gmm_algorithm_runs_without_error(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        coords = clusterize(df_feat, algorithm="gmm")
        assert len(coords) == 3
        assert all(c.cluster >= 1 for c in coords)

    def test_unknown_algorithm_raises(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        df_main = deck_cards_df[~deck_cards_df["is_sideboard"]]
        df_feat = flatten_features_dict(df_main, cards_df)
        with pytest.raises(ValueError, match="unknown algorithm"):
            clusterize(df_feat, algorithm="bogus")  # type: ignore[arg-type]


class TestClusterizeByWindow:
    def test_empty_extraction_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            clustering.extract, "load_deck_cards", lambda *_a, **_kw: pd.DataFrame()
        )
        window = Window(
            kind=WindowKind.rolling_30d,
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 31),
        )
        assert clustering.clusterize_by_window(window) == []

    def test_extracted_decks_get_clustered(
        self,
        monkeypatch: pytest.MonkeyPatch,
        deck_cards_df: pd.DataFrame,
        cards_df: pd.DataFrame,
    ):
        monkeypatch.setattr(
            clustering.extract, "load_deck_cards", lambda *_a, **_kw: deck_cards_df
        )
        monkeypatch.setattr(clustering.extract, "load_cards_features", lambda: cards_df)
        window = Window(
            kind=WindowKind.rolling_30d,
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 31),
        )
        coords = clustering.clusterize_by_window(window)
        assert {c.deck_id for c in coords} == {"deck-1", "deck-2", "deck-3"}
