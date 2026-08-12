"""Advanced aggregation: prototype-deck selection and consensus aggregation.

Ported subset of the prior attempt at this
(`barrins-archive/barrins_api/app/services/ml/aggregation_advanced.py`).

**Not ported**: `standing_weights`/`weighted_aggregate`. The original
derived a per-deck weight from `dl_decks.rank`, a plain integer column
that schema doesn't have an equivalent of -- `bs_decks` has no numeric
rank, only a free-form `result` string (MTGTop8 reports ties as ranges
like "5-8") and a separate `bs_standings` table keyed by player name, not
`deck_id`. Building a reliable deck-to-standing linkage is its own small
design problem, not a mechanical port -- deferred rather than guessed at.
`temporal_weights` has no such dependency and is kept.
"""

import datetime as dt
import math

import numpy as np

from karn_tablets.schemas import Decklist

# -- Prototype (centroid) deck ---------------------------------------------------


def prototype_deck(
    x_clust: np.ndarray,  # (n_decks x n_pca) -- the clustering space
    cluster_mask: np.ndarray,  # bool mask selecting this cluster's decks
    decklists: list[Decklist],
) -> tuple[Decklist, int]:
    """Returns the real deck closest to the cluster's centroid, and its
    index into `decklists`. Always a legal, existing deck (real counts).
    """
    x_cluster = x_clust[cluster_mask]
    centroid = x_cluster.mean(axis=0)
    idx = int(np.argmin(np.linalg.norm(x_cluster - centroid, axis=1)))
    original_idx = int(np.where(cluster_mask)[0][idx])
    return decklists[original_idx], original_idx


# -- Presence-threshold (consensus) aggregation ----------------------------------


def consensus_aggregate(
    decks: list[Decklist],
    threshold: float = 0.5,
    zone: str = "mainboard",
) -> dict[str, int]:
    """Returns cards played in >= `threshold` x `len(decks)` decks, with
    the count set to the rounded average across those decks.
    """
    card_counts: dict[str, int] = {}
    card_total_copies: dict[str, int] = {}

    for deck in decks:
        zone_data = getattr(deck, zone) or {}
        for card, qty in zone_data.items():
            card_counts[card] = card_counts.get(card, 0) + 1
            card_total_copies[card] = card_total_copies.get(card, 0) + qty

    n = len(decks)
    if n == 0:
        return {}
    return {
        card: max(1, round(card_total_copies[card] / n))
        for card, count in card_counts.items()
        if count / n >= threshold
    }


# -- Temporal decay -------------------------------------------------------------


def temporal_weights(
    tournament_dates: list[dt.date],
    date_to: dt.date,
    half_life_days: int = 14,
) -> list[float]:
    """w_i = 0.5 ** (age_days / half_life). A tournament `half_life_days`
    old has exactly half the weight of a recent one.

    The original ported implementation used `exp(-age/half_life)`, which
    despite its name and docstring is *not* true half-life decay -- at
    `age == half_life` that formula gives `exp(-1) ≈ 0.368`, not `0.5`.
    Fixed to match what the parameter name and docstring actually promise
    (`0.5 ** (age/half_life) = exp(-ln(2) * age/half_life)`).
    """
    return [
        math.exp(-math.log(2) * (date_to - d).days / half_life_days)
        for d in tournament_dates
    ]
