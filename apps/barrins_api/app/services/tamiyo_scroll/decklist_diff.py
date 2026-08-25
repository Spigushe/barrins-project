"""Card-aware diff between two decklist version contents (S15).

Cards are matched by name across the two versions rather than by line
position, so reordering a decklist never shows up as a spurious
added+removed pair -- only an actual quantity/presence change does.
Lines that aren't a "<qty> <name>" card line (headers, free-text notes)
can't be matched by name, so they get a plain line-level diff instead,
mirroring `decklist_view.py`'s `unparsed_lines` fallback.
"""

import difflib
from collections.abc import Sequence
from typing import Literal

from app.schemas.responses_tamiyo_scroll import (
    ResponseDecklistCardDiff,
    ResponseDecklistLineDiff,
)
from app.services.tamiyo_scroll.decklist_coloring import (
    commander_section_indices,
    parse_card_line,
)

CardDiffStatus = Literal["added", "removed", "unchanged", "quantity_changed"]


def _card_quantities(content: str) -> tuple[dict[str, int], set[str]]:
    """`name -> total qty` (summed if a name appears on multiple lines),
    plus the set of names found within the Commander section."""
    lines = content.splitlines()
    commander_idx = commander_section_indices(lines)
    quantities: dict[str, int] = {}
    commander_names: set[str] = set()
    for i, raw in enumerate(lines):
        parsed = parse_card_line(raw)
        if parsed is None:
            continue
        qty, name = parsed
        quantities[name] = quantities.get(name, 0) + qty
        if i in commander_idx:
            commander_names.add(name)
    return quantities, commander_names


def _unparsed_lines(content: str) -> list[str]:
    result: list[str] = []
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.casefold() == "commander":
            continue
        if parse_card_line(raw) is None:
            result.append(raw)
    return result


def diff_decklist_cards(
    old_content: str, new_content: str
) -> list[ResponseDecklistCardDiff]:
    old_qty, old_commander = _card_quantities(old_content)
    new_qty, new_commander = _card_quantities(new_content)

    diffs: list[ResponseDecklistCardDiff] = []
    for name in sorted(set(old_qty) | set(new_qty)):
        old = old_qty.get(name)
        new = new_qty.get(name)
        status: CardDiffStatus
        if old is None:
            status = "added"
        elif new is None:
            status = "removed"
        elif old != new:
            status = "quantity_changed"
        else:
            status = "unchanged"
        is_commander = name in new_commander or (new is None and name in old_commander)
        diffs.append(
            ResponseDecklistCardDiff(
                name=name,
                status=status,
                old_qty=old,
                new_qty=new,
                is_commander=is_commander,
            )
        )

    # Commander cards first, then alphabetical within each group -- a
    # lightweight approximation of decklist_view's full type/mana-value
    # sort, without a DB round trip just to order a diff.
    diffs.sort(key=lambda d: (not d.is_commander, d.name))
    return diffs


def diff_decklist_unparsed_lines(
    old_content: str, new_content: str
) -> list[ResponseDecklistLineDiff]:
    old_lines = _unparsed_lines(old_content)
    new_lines = _unparsed_lines(new_content)
    return _line_diff(old_lines, new_lines)


def _line_diff(
    old_lines: Sequence[str], new_lines: Sequence[str]
) -> list[ResponseDecklistLineDiff]:
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    result: list[ResponseDecklistLineDiff] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.extend(
                ResponseDecklistLineDiff(line=line, status="unchanged")
                for line in old_lines[i1:i2]
            )
        else:
            result.extend(
                ResponseDecklistLineDiff(line=line, status="removed")
                for line in old_lines[i1:i2]
            )
            result.extend(
                ResponseDecklistLineDiff(line=line, status="added")
                for line in new_lines[j1:j2]
            )
    return result
