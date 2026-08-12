"""Frequency-based decklist aggregation (the 1/2^order algorithm).

Ported near-verbatim from the prior attempt at this
(`barrins-archive/barrins_api/app/services/ml/aggregation.py`) -- no
schema adaptation needed, this module only ever sees `Decklist` objects,
never touches the database directly.
"""

import re
from collections import Counter, defaultdict
from itertools import combinations

from karn_tablets.schemas import AggregatedDecklist, Decklist


def aggregate_decks(
    decks: list[Decklist],
    order: int = 1,
    limit: int = 100,
) -> AggregatedDecklist | None:
    """Main entry point -- aggregates a list of `Decklist` into one
    representative list.
    """
    if not decks:
        return None
    decks = decks[:limit]

    sideboard_sizes = [sum((d.sideboard or {}).values()) for d in decks]
    min_sb = Counter(sideboard_sizes).most_common(1)[0][0]
    mb_sizes = [sum((d.mainboard or {}).values()) for d in decks]
    target_mb = Counter(mb_sizes).most_common(1)[0][0]  # mode -- robust to outliers

    aggregated_sideboard: dict[str, int] = {}
    for target in range(min_sb, 16):
        try:
            aggregated_sideboard = _aggregate_zone(decks, "sideboard", target, order)
            break
        except ValueError:
            continue

    if not aggregated_sideboard:
        all_sb: Counter[str] = Counter()
        for d in decks:
            all_sb.update(d.sideboard or {})
        aggregated_sideboard = dict(all_sb.most_common(15))

    aggregated_mainboard = _aggregate_zone(decks, "mainboard", target_mb, order)
    return AggregatedDecklist(
        decklist=Decklist(
            mainboard=aggregated_mainboard,
            sideboard=aggregated_sideboard,
        ),
        decks=decks,
        order=order,
        frequency_threshold=-1,
    )


def _aggregate_zone(
    decks: list[Decklist],
    zone: str,
    target_size: int,
    order: int,
) -> dict[str, int]:
    collective: Counter[str] = Counter()
    ranking: Counter[tuple[str, ...]] = Counter()

    for deck in decks:
        card_list = _to_indexed_list(deck, zone)
        collective.update(card_list)
        ranking.update(
            _combinations(card_list, order)
            if order > 1
            else [(card,) for card in card_list]
        )

    if len(collective) > target_size:
        collective = _remove_cards(collective, ranking, target_size)

    result: Counter[str] = Counter()
    result.update(re.sub(r"\d+$", "", line).strip() for line in collective)
    return dict(result.items())


def _to_indexed_list(deck: Decklist, zone: str) -> list[str]:
    """
    "Lightning Bolt": 4 -> ["Lightning Bolt 1", ..., "Lightning Bolt 4"].
    Distinguishes copies so multi-copy combinations are possible.
    """
    return [
        f"{card} {i}"
        for card, qty in (getattr(deck, zone) or {}).items()
        for i in range(qty)
    ]


def _combinations(lst: list[str], size: int) -> list[tuple[str, ...]]:
    return [tuple(sorted(c)) for c in combinations(lst, size)]


def _calculate_scores(
    rankings: Counter[tuple[str, ...]],
    current_cards: set[str],
) -> dict[float, list[str]]:
    """
    Importance score = sum(count(C) x 1/2^|C|) for every combination C
    containing the card. A low score is a removal candidate.
    """
    scores: dict[str, float] = defaultdict(float)
    for comb, count in rankings.items():
        if set(comb).issubset(current_cards):
            w = count * (1 / (2 ** len(comb)))
            for card in comb:
                scores[card] += w
    transposed: dict[float, list[str]] = defaultdict(list)
    for card, score in scores.items():
        transposed[score].append(card)
    return dict(transposed)


def _remove_cards(
    pool: Counter[str],
    rankings: Counter[tuple[str, ...]],
    target_size: int,
) -> Counter[str]:
    while len(pool) > target_size:
        scores = _calculate_scores(rankings, set(pool.keys()))
        if not scores:
            return Counter(dict(Counter(pool).most_common(target_size)))
        lowest = min(scores.keys())
        candidates = {k: v for k, v in pool.items() if k in scores[lowest]}
        pool = Counter({k: v for k, v in pool.items() if k not in scores[lowest]})
        slots = target_size - len(pool)
        if slots > 0:
            for card, qty in list(candidates.items())[:slots]:
                pool[card] = qty
    return pool
