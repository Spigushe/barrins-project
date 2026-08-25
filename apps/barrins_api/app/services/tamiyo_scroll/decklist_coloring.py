"""Coloring of decklist lines based on tested card feedback.

Pure function — cf. docs/tamiyo_scroll_tracker/00_plan_general.md, Option F.
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Literal, TypedDict

from app.models.tamiyo_scroll import TSCardTest

LineStatus = Literal["validated", "rejected", "in_test", "neutral"]

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
