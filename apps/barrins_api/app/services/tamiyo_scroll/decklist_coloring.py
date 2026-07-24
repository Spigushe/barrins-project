"""Coloring of decklist lines based on tested card feedback.

Pure function — cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option F.
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal, TypedDict

from app.models.tamiyo_scroll import TSCardTest

LineStatus = Literal["validated", "rejected", "in_test", "neutral"]


class ColoredLine(TypedDict):
    line: str
    status: LineStatus


def _line_status(ratings: Sequence[int]) -> LineStatus:
    total = len(ratings)
    if total == 0:
        return "in_test"
    high = sum(1 for r in ratings if r >= 4)
    low = sum(1 for r in ratings if r <= 2)
    if high > total / 2:
        return "validated"
    if low > total / 2:
        return "rejected"
    return "in_test"


def color_decklist(content: str, card_tests: Sequence[TSCardTest]) -> list[ColoredLine]:
    """Color each line based on the test feedback for the card it contains.

    For each line, finds the longest card name that appears in it
    (case-insensitive) among the test feedback, then derives the line's
    status from the majority of the associated ratings: validated (>=4
    majority), rejected (<=2 majority), in test (feedback without a
    majority), neutral (no feedback for this card).
    """
    ratings_by_card: dict[str, list[int]] = defaultdict(list)
    for test in card_tests:
        ratings_by_card[test.card_name.lower()].append(test.rating)

    # Longest name first — prevents a short name (e.g. "Duress") from
    # masking a longer name that contains it (e.g. "Extended Duress").
    card_names_longest_first = sorted(ratings_by_card, key=len, reverse=True)

    lines: list[ColoredLine] = []
    for raw_line in content.splitlines():
        line_lower = raw_line.lower()
        matched_card = next(
            (name for name in card_names_longest_first if name in line_lower), None
        )
        status: LineStatus = "neutral"
        if matched_card is not None:
            status = _line_status(ratings_by_card[matched_card])
        lines.append({"line": raw_line, "status": status})
    return lines
