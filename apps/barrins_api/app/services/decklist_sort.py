"""Shared card-type sort/group order for rendered decklists (Duel Commander).

Used by both `tamiyo_scroll.decklist_view` (a player's own decklist) and
`tolaria_news.decks` (a scraped tournament decklist) so the display order
and section grouping are defined once rather than duplicated per app.

Commander cards are never grouped by this module -- both callers already
carry them in their own dedicated section (`commander_cards` /
`commanders`), structurally separate from the type-grouped list this
module builds.
"""

from collections.abc import Callable, Sequence
from typing import Literal

DecklistCardCategory = Literal[
    "planeswalker",
    "battle",
    "creature",
    "instant",
    "sorcery",
    "artifact",
    "enchantment",
    "land",
    "other",
]

#: 1st sort key / section order. Scryfall type lines can combine more than
#: one type (e.g. "Artifact Creature", "Enchantment Creature" for bestow)
#: -- walked in this priority order so e.g. a creature always ranks/groups
#: as a creature, never as its secondary artifact/enchantment type.
#: "other" (unresolved/unrecognized type lines) isn't listed here -- it's
#: `categorize`'s fallback, and always sorts/groups last.
CATEGORY_ORDER: tuple[DecklistCardCategory, ...] = (
    "planeswalker",
    "battle",
    "creature",
    "instant",
    "sorcery",
    "artifact",
    "enchantment",
    "land",
)


def categorize(type_line: str | None) -> DecklistCardCategory:
    """Highest-priority `CATEGORY_ORDER` category present in `type_line`,
    or "other" if `type_line` is unresolved or matches none of them."""
    if type_line is not None:
        lowered = type_line.casefold()
        for category in CATEGORY_ORDER:
            if category in lowered:
                return category
    return "other"


def _category_rank(category: DecklistCardCategory) -> int:
    return (
        CATEGORY_ORDER.index(category) if category != "other" else len(CATEGORY_ORDER)
    )


def decklist_sort_key(
    type_line: str | None, mana_value: float | None, name: str
) -> tuple[int, float, str]:
    """(type, then mana value, then name) sort key for one decklist card."""
    return (
        _category_rank(categorize(type_line)),
        mana_value if mana_value is not None else float("inf"),
        name.casefold(),
    )


def group_by_category[T](
    cards: Sequence[T], type_line_of: Callable[[T], str | None]
) -> list[tuple[DecklistCardCategory, list[T]]]:
    """Buckets `cards` into `(category, cards)` groups, `CATEGORY_ORDER`
    order with "other" last, dropping categories with no cards.

    `cards` must already be sorted by `decklist_sort_key` (or at least by
    category) -- this only buckets, it doesn't sort within a bucket.
    """
    buckets: dict[DecklistCardCategory, list[T]] = {}
    for card in cards:
        buckets.setdefault(categorize(type_line_of(card)), []).append(card)
    return [
        (category, buckets[category])
        for category in (*CATEGORY_ORDER, "other")
        if category in buckets
    ]
