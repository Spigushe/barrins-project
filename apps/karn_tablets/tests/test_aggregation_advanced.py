from datetime import date

import numpy as np
import pytest

from karn_tablets.aggregation_advanced import (
    consensus_aggregate,
    prototype_deck,
    temporal_weights,
)
from karn_tablets.schemas import Decklist


class TestPrototypeDeck:
    def test_returns_the_deck_closest_to_the_centroid(self):
        decklists = [
            Decklist(mainboard={"A": 1}),
            Decklist(mainboard={"B": 1}),
            Decklist(mainboard={"C": 1}),
        ]
        x_clust = np.array([[0.0, 0.0], [10.0, 10.0], [0.1, 0.1]])
        mask = np.array([True, True, True])
        deck, idx = prototype_deck(x_clust, mask, decklists)
        # Centroid is (3.37, 3.37); deck 2 (0.1, 0.1) is nominally closer
        # to it than deck 0 (0, 0).
        assert idx == 2
        assert deck == decklists[2]

    def test_mask_restricts_the_search_to_cluster_members(self):
        decklists = [Decklist(mainboard={"A": 1}), Decklist(mainboard={"B": 1})]
        x_clust = np.array([[0.0, 0.0], [100.0, 100.0]])
        mask = np.array([False, True])
        deck, idx = prototype_deck(x_clust, mask, decklists)
        assert idx == 1
        assert deck == decklists[1]


class TestConsensusAggregate:
    def test_cards_in_every_deck_meet_a_full_threshold(self):
        decks = [
            Decklist(mainboard={"Sol Ring": 1, "Only In One": 1}),
            Decklist(mainboard={"Sol Ring": 1}),
            Decklist(mainboard={"Sol Ring": 1}),
        ]
        result = consensus_aggregate(decks, threshold=1.0)
        assert result == {"Sol Ring": 1}

    def test_half_threshold_includes_cards_in_at_least_half(self):
        decks = [
            Decklist(mainboard={"A": 1}),
            Decklist(mainboard={"A": 1}),
            Decklist(mainboard={"B": 1}),
        ]
        result = consensus_aggregate(decks, threshold=0.5)
        assert result == {"A": 1}

    def test_empty_decks_returns_empty_dict(self):
        assert consensus_aggregate([]) == {}

    def test_counts_are_rounded_averages(self):
        decks = [
            Decklist(mainboard={"Lightning Bolt": 4}),
            Decklist(mainboard={"Lightning Bolt": 2}),
        ]
        result = consensus_aggregate(decks, threshold=1.0)
        assert result == {"Lightning Bolt": 3}  # round((4+2)/2)


class TestTemporalWeights:
    def test_same_day_weight_is_one(self):
        weights = temporal_weights([date(2026, 6, 15)], date(2026, 6, 15))
        assert weights == [1.0]

    def test_half_life_days_old_is_half_weight(self):
        weights = temporal_weights(
            [date(2026, 6, 1)], date(2026, 6, 15), half_life_days=14
        )
        assert weights[0] == pytest.approx(0.5, rel=1e-2)

    def test_more_recent_tournaments_weigh_more(self):
        weights = temporal_weights(
            [date(2026, 6, 1), date(2026, 6, 14)], date(2026, 6, 15)
        )
        assert weights[1] > weights[0]
