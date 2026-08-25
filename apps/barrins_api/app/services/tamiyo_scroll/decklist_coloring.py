"""Coloring of decklist lines based on tested card feedback.

Pure function — cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option F.
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Literal, TypedDict

from app.models.tamiyo_scroll import TSCardTest, TSCardTestEvaluation

LineStatus = Literal["validated", "rejected", "in_test", "neutral", "pending"]

_COMMANDER_HEADER = "commander"
# Mirrors apps/barrins_scripture/barrins_scripture/parsers/mtgo.py's
# `_get_cards` regex (not imported cross-app — barrins_api doesn't depend
# on barrins_scripture, only mirrors the same "N Name" text convention).
_CARD_LINE_RE = re.compile(r"(\d+)[xX]?\s+(.*)")


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


def color_decklist(
    content: str,
    card_tests: Sequence[TSCardTest],
    evaluations: Sequence[TSCardTestEvaluation],
) -> list[ColoredLine]:
    """Color each line based on card logs/evaluations for the card it contains.

    Two independent axes, checked in order per line (S17):

    1. **Pending** — the line's card name matches some card log's
       `removed_card_name` (still literally present in `content`, since
       that's what's being scanned). The swap hasn't landed in this
       decklist yet. Takes priority over the evaluation-based pass below
       so the two never collide on one line.
    2. **Evaluation-based majority** — same rule as before S17, just fed
       by `TSCardTestEvaluation` ratings pooled by their parent card log's
       `added_card_name` instead of a rating living directly on the card
       log: validated (>=4 majority), rejected (<=2 majority), in test
       (feedback without a majority), neutral (no feedback for this card).
    """
    test_by_id = {test.id: test for test in card_tests}
    ratings_by_added_name: dict[str, list[int]] = defaultdict(list)
    for evaluation in evaluations:
        test = test_by_id.get(evaluation.test_id)
        if test is not None:
            ratings_by_added_name[test.added_card_name.lower()].append(
                evaluation.rating
            )

    # Longest name first — prevents a short name (e.g. "Duress") from
    # masking a longer name that contains it (e.g. "Extended Duress").
    removed_names_longest_first = sorted(
        {test.removed_card_name.lower() for test in card_tests}, key=len, reverse=True
    )
    added_names_longest_first = sorted(ratings_by_added_name, key=len, reverse=True)

    lines: list[ColoredLine] = []
    for raw_line in content.splitlines():
        line_lower = raw_line.lower()
        if any(name in line_lower for name in removed_names_longest_first):
            lines.append({"line": raw_line, "status": "pending"})
            continue
        matched_card = next(
            (name for name in added_names_longest_first if name in line_lower), None
        )
        status: LineStatus = "neutral"
        if matched_card is not None:
            status = _line_status(ratings_by_added_name[matched_card])
        lines.append({"line": raw_line, "status": status})
    return lines


def commander_section_indices(lines: Sequence[str]) -> set[int]:
    """Indices of `lines` belonging to an optional "Commander" section.

    A line whose stripped, casefolded text is exactly "commander" (alone
    on its own line) starts the section; every following non-blank line
    is a commander line until the next blank line or end of content. No
    such header -> empty set, meaning the whole decklist renders as
    library (expected fallback for manually-pasted/legacy decks, not an
    error). Only "Commander" is recognized — Sideboard/Companion
    detection is explicitly out of scope (2026-08-14 decision).
    """
    indices: set[int] = set()
    in_section = False
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.casefold() == _COMMANDER_HEADER:
            in_section = True
            continue
        if in_section:
            if not stripped:
                in_section = False
                continue
            indices.add(i)
    return indices


def parse_card_line(line: str) -> tuple[int, str] | None:
    """`(qty, name)` if `line` matches "<qty>[x] <name>", else None
    (section headers, blank lines, free-text notes, malformed lines)."""
    stripped = line.strip()
    if not stripped:
        return None
    match = _CARD_LINE_RE.match(stripped)
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()
