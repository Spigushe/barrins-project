"""Script made to organize my personal collection from Moxfield.

The collection is split into physical binders, sorted within each binder by
Color Identity, then Mana Value, then Card Type, and finally Card Name.
Binders have 360 slots in pages of 9 cards each; some room is deliberately
left on every page for future additions (see `--reserve-per-page`).

Several binder layouts ("schemes") are registered below (see `SCHEMES`),
selectable via `--scheme`, so that trying a different way to split the
collection across binders as it grows doesn't require rewriting this
script -- only adding a new `BinderScheme` entry.

- `classic4` (default): Binder 1 White/Blue, Binder 2 Black/Red/Green,
  Binder 3 Multicolor/Colorless, Binder 4 Lands/Tokens (its Land block
  further split by color identity).
- `gold3`: Binder 1 White/Blue/Black, Binder 2 Red/Green/Gold
  (multicolor), Binder 3 Colorless/Lands/Tokens.

Data source: a Moxfield "Haves" CSV export, read by default from
`scripts/input/` (see `DEFAULT_CSV_PATH`) -- both `input/` and `outputs/`
hold personal collection data and are git-ignored, not checked in. Card
attributes needed for sorting (color identity, mana value, type) come from
the local MTGJSON-backed `cards`/`sets` tables (see `app/models/mtgjson.py`),
matched by set code + collector number, falling back to a name-only lookup
(latest printing).

Usage
-----
    python scripts/collection_organization.py
    python scripts/collection_organization.py --scheme gold3
    python scripts/collection_organization.py --reserve-per-page 3
    python scripts/collection_organization.py --csv input/other_export.csv \\
        --output-csv outputs/binders.csv --output-json outputs/binders.json \\
        --output-md outputs/binders.md
"""

import argparse
import asyncio
import csv
import itertools
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal
from app.models.mtgjson import Card, MTGSet

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "outputs"
DEFAULT_CSV_PATH = INPUT_DIR / "moxfield_haves_2026-08-06-1040Z.csv"
DEFAULT_CSV_OUTPUT = OUTPUT_DIR / "collection_binders.csv"
DEFAULT_JSON_OUTPUT = OUTPUT_DIR / "collection_binders.json"
DEFAULT_MARKDOWN_OUTPUT = OUTPUT_DIR / "collection_binders.md"

PAGE_SIZE = 9
BINDER_CAPACITY = 360
TOTAL_PAGES = BINDER_CAPACITY // PAGE_SIZE
DEFAULT_RESERVE_PER_PAGE = 2
DEFAULT_SCHEME = "classic4"

# Highest-priority match wins for a card with multiple types
# (e.g. "Artifact Creature" sorts as "Creature").
TYPE_PRIORITY: tuple[str, ...] = (
    "Creature",
    "Planeswalker",
    "Battle",
    "Instant",
    "Sorcery",
    "Artifact",
    "Enchantment",
    "Land",
    "Token",
)

WUBRG_INDEX: dict[str, int] = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}
FIVE_COLORS = "WUBRG"


def _color_label(colors: frozenset[str]) -> str:
    """Canonical WUBRG-ordered label for a set of colors, e.g. {"U", "W"} -> "WU"."""
    return "".join(c for c in FIVE_COLORS if c in colors)


BINDER3_PAIRS: tuple[str, ...] = tuple(
    _color_label(frozenset(combo)) for combo in itertools.combinations(FIVE_COLORS, 2)
)
BINDER3_TRIPLES: tuple[str, ...] = tuple(
    _color_label(frozenset(combo)) for combo in itertools.combinations(FIVE_COLORS, 3)
)
BINDER3_MANY_COLORS = "4+ Colors"
BINDER_TOKEN_PAGES = 2


@dataclass(frozen=True)
class CollectionRow:
    """One typed row from the Moxfield CSV export."""

    line_no: int
    count: int
    tradelist_count: int
    name: str
    edition: str
    condition: str
    language: str
    foil: bool
    collector_number: str


@dataclass(frozen=True)
class MatchedCard:
    """Attributes pulled from `Card`, needed for binder assignment/sorting."""

    card_id: str
    name: str
    set_code: str
    number: str
    type_line: str
    types: tuple[str, ...]
    supertypes: tuple[str, ...]
    mana_value: float | None
    color_identity: tuple[str, ...]
    match_method: str


@dataclass(frozen=True)
class UnmatchedRow:
    row: CollectionRow
    reason: str


@dataclass(frozen=True)
class BinderSlot:
    binder: int
    page: int
    slot_in_page: int
    global_slot: int
    row: CollectionRow
    card: MatchedCard


@dataclass(frozen=True)
class Subgroup:
    """One within-binder page block.

    Either `weight` (relative share of the binder's remaining pages,
    apportioned by `_apportion_pages`) or `fixed_pages` (an exact page
    count, carved out before weights are applied) drives its size --
    `fixed_pages` is for a block whose size is a deliberate policy
    decision (e.g. Token) rather than proportional to the others.
    """

    label: str
    weight: int = 1
    fixed_pages: int | None = None


@dataclass(frozen=True)
class BinderDef:
    number: int
    label: str
    classify: Callable[[MatchedCard], str]
    subgroups: tuple[Subgroup, ...]


@dataclass(frozen=True)
class BinderScheme:
    """A complete way to split the collection across binders.

    `assign_binder` picks which binder a card goes to; each binder's own
    `classify` then picks which of its subgroups (page block) the card
    lands in. Adding a new layout is adding a new `BinderScheme` value to
    `SCHEMES`, not editing the allocation logic itself.
    """

    name: str
    description: str
    assign_binder: Callable[[MatchedCard], int]
    binders: tuple[BinderDef, ...] = field(default_factory=tuple)


def parse_csv(path: Path) -> list[CollectionRow]:
    """Reads the Moxfield "Haves" export into typed rows.

    Exits with code 1 if the file doesn't exist -- this is a one-off
    personal script, an uncaught traceback for any other I/O failure is
    acceptable (matches `create_admin.py`'s own error-handling style).
    """
    if not path.exists():
        print(f"ERROR: CSV file not found: {path}", file=sys.stderr)
        sys.exit(1)

    rows: list[CollectionRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for line_no, entry in enumerate(reader, start=2):
            rows.append(
                CollectionRow(
                    line_no=line_no,
                    count=int(entry["Count"]),
                    tradelist_count=int(entry["Tradelist Count"]),
                    name=entry["Name"].strip(),
                    edition=entry["Edition"].strip(),
                    condition=entry["Condition"].strip(),
                    language=entry["Language"].strip(),
                    foil=bool(entry["Foil"].strip()),
                    collector_number=entry["Collector Number"].strip(),
                )
            )
    return rows


async def fetch_cards_by_set_and_number(
    session: AsyncSession, set_codes: set[str]
) -> dict[tuple[str, str], Card]:
    """One `Card` per (set_code, number).

    A modal-DFC/split card has 2 rows sharing the same `(set_code,
    number)` (one per face) -- ordering by `side` ascending (NULLs last)
    and keeping only the first-seen row per key prefers the front face
    (`side == "a"`), per this script's own binder-routing decision.
    """
    if not set_codes:
        return {}
    result = await session.execute(
        select(Card)
        .where(Card.set_code.in_(set_codes))
        .order_by(Card.side.asc().nulls_last())
    )
    index: dict[tuple[str, str], Card] = {}
    for card in result.scalars().all():
        index.setdefault((card.set_code, card.number), card)
    return index


async def fetch_cards_by_name(
    session: AsyncSession, names: set[str]
) -> dict[str, Card]:
    """Fallback index: most recently released printing per card name.

    Mirrors `app/api/general/mtgjson.py`'s `get_card_by_name` route, with
    the same front-face preference as `fetch_cards_by_set_and_number` on
    ties.
    """
    if not names:
        return {}
    result = await session.execute(
        select(Card)
        .join(MTGSet, Card.set_code == MTGSet.code)
        .where(Card.name.in_(names))
        .order_by(MTGSet.release_date.desc(), Card.side.asc().nulls_last())
    )
    index: dict[str, Card] = {}
    for card in result.scalars().all():
        index.setdefault(card.name, card)
    return index


def _to_matched_card(card: Card, match_method: str) -> MatchedCard:
    return MatchedCard(
        card_id=str(card.id),
        name=card.name,
        set_code=card.set_code,
        number=card.number,
        type_line=card.type_line,
        types=tuple(card.types),
        supertypes=tuple(card.supertypes),
        mana_value=card.mana_value,
        color_identity=tuple(card.color_identity),
        match_method=match_method,
    )


def resolve_card(
    row: CollectionRow,
    by_set_number: dict[tuple[str, str], Card],
    by_name: dict[str, Card],
) -> MatchedCard | None:
    card = by_set_number.get((row.edition.upper(), row.collector_number))
    if card is not None:
        return _to_matched_card(card, "exact_set_number")

    card = by_name.get(row.name)
    if card is not None:
        return _to_matched_card(card, "name_fallback")

    return None


async def resolve_all(
    rows: list[CollectionRow], session: AsyncSession
) -> tuple[list[tuple[CollectionRow, MatchedCard]], list[UnmatchedRow]]:
    by_set_number = await fetch_cards_by_set_and_number(
        session, {row.edition.upper() for row in rows}
    )
    by_name = await fetch_cards_by_name(session, {row.name for row in rows})

    matched: list[tuple[CollectionRow, MatchedCard]] = []
    unmatched: list[UnmatchedRow] = []
    for row in rows:
        card = resolve_card(row, by_set_number, by_name)
        if card is None:
            reason = (
                f"No card found for edition={row.edition!r}, "
                f"collector_number={row.collector_number!r}, "
                f"nor by exact name match on {row.name!r}."
            )
            unmatched.append(UnmatchedRow(row=row, reason=reason))
        else:
            matched.append((row, card))
    return matched, unmatched


def type_category(types: tuple[str, ...]) -> str:
    for category in TYPE_PRIORITY:
        if category in types:
            return category
    return "Other"


def _type_category_rank(category: str) -> int:
    if category in TYPE_PRIORITY:
        return TYPE_PRIORITY.index(category)
    return len(TYPE_PRIORITY)


def color_identity_sort_key(color_identity: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(sorted(WUBRG_INDEX[c] for c in color_identity if c in WUBRG_INDEX))


def sort_key(
    row: CollectionRow, card: MatchedCard
) -> tuple[tuple[int, ...], float, int, str, str, str, bool, int]:
    return (
        color_identity_sort_key(card.color_identity),
        card.mana_value if card.mana_value is not None else 0.0,
        _type_category_rank(type_category(card.types)),
        card.name.casefold(),
        card.set_code,
        card.number,
        row.foil,
        row.line_no,
    )


def is_basic(card: MatchedCard) -> bool:
    return "Basic" in card.supertypes


def copies_needed(row: CollectionRow, card: MatchedCard) -> int:
    """Physical slots one CSV row needs.

    Basic lands get 1 slot per owned copy -- unlike every other card,
    they're cheap enough that pairing 2 identical copies per slot isn't
    worth the density loss. Everything else keeps the ceil(count / 2)
    pairing rule.
    """
    if is_basic(card):
        return row.count
    return (row.count + 1) // 2  # ceil(count / 2)


# --- classic4 scheme -------------------------------------------------------
#
# Binder 1/2 split evenly by color so a color never shares a page with
# another and always keeps guaranteed room to grow. Binder 3 splits by
# weight (colorless gets relatively more room, specific 2-color pairs more
# than specific 3-color combos, 4/5-color combos share one small block).
# Binder 4 gives Token a small fixed block (no token is ever resolved from
# the local card DB today, see `fetch_cards_by_set_and_number`'s
# docstring, so this stays empty room for whenever that changes) and
# splits the remaining Land pages by color identity: multicolor lands
# (duals/triomes/fetches) are typically the most numerous nonbasic-land
# category, colorless next, each mono-color an equal smaller share.


def _classify_binder1_classic4(card: MatchedCard) -> str:
    return "W" if "W" in card.color_identity else "U"


def _classify_binder2_classic4(card: MatchedCard) -> str:
    colors = set(card.color_identity)
    for color in ("B", "R", "G"):
        if color in colors:
            return color
    raise AssertionError(f"classic4 Binder 2 card with no B/R/G color: {card.name!r}")


def _classify_binder3_classic4(card: MatchedCard) -> str:
    colors = frozenset(card.color_identity)
    if not colors:
        return "Colorless"
    if len(colors) in (2, 3):
        return _color_label(colors)
    return BINDER3_MANY_COLORS


def _classify_binder4_classic4(card: MatchedCard) -> str:
    if "Token" in card.types:
        return "Token"
    colors = frozenset(card.color_identity)
    if not colors:
        return "Colorless"
    if len(colors) == 1:
        return next(iter(colors))
    return "Multicolor"


def _assign_binder_classic4(card: MatchedCard) -> int:
    """Binder 4 for Land/Token (overrides color); else by color identity.

    Binder 1/2 are for mono-colored cards only (exactly one color in their
    color identity). Any card with 2+ colors -- including a WU or BRG
    pair -- is "multicolor" and goes to Binder 3, same as colorless.
    """
    if "Land" in card.types or "Token" in card.types:
        return 4

    color_set = set(card.color_identity)
    if len(color_set) >= 2:
        return 3
    if not color_set:  # colorless, checked separately from the W/U subset test below
        return 3
    if color_set <= {"W", "U"}:  # exactly one of W/U
        return 1
    if color_set <= {"B", "R", "G"}:  # exactly one of B/R/G
        return 2
    return 3


CLASSIC4_SCHEME = BinderScheme(
    name="classic4",
    description=(
        "Binder 1 White/Blue, Binder 2 Black/Red/Green, Binder 3 "
        "Multicolor/Colorless, Binder 4 Lands/Tokens (Land block split by color)."
    ),
    assign_binder=_assign_binder_classic4,
    binders=(
        BinderDef(
            1,
            "White/Blue",
            _classify_binder1_classic4,
            (Subgroup("W"), Subgroup("U")),
        ),
        BinderDef(
            2,
            "Black/Red/Green",
            _classify_binder2_classic4,
            (Subgroup("B"), Subgroup("R"), Subgroup("G")),
        ),
        BinderDef(
            3,
            "Multicolor/Colorless",
            _classify_binder3_classic4,
            (
                Subgroup("Colorless", weight=3),
                *(Subgroup(label, weight=2) for label in BINDER3_PAIRS),
                *(Subgroup(label, weight=1) for label in BINDER3_TRIPLES),
                Subgroup(BINDER3_MANY_COLORS, weight=1),
            ),
        ),
        BinderDef(
            4,
            "Lands/Tokens",
            _classify_binder4_classic4,
            (
                Subgroup("Colorless", weight=2),
                Subgroup("W", weight=1),
                Subgroup("U", weight=1),
                Subgroup("B", weight=1),
                Subgroup("R", weight=1),
                Subgroup("G", weight=1),
                Subgroup("Multicolor", weight=3),
                Subgroup("Token", fixed_pages=BINDER_TOKEN_PAGES),
            ),
        ),
    ),
)


# --- gold3 scheme -----------------------------------------------------------
#
# Binder 1/2 still split evenly by color (now 3-way: W/U/B and R/G).
# Multicolor cards join Binder 2 as "Gold" instead of getting their own
# binder. Binder 3 becomes the "colorless-flavored" binder: colorless
# spells plus every Land (split by color identity, same reasoning as
# classic4's Binder 4) plus Token.


def _classify_binder1_gold3(card: MatchedCard) -> str:
    colors = set(card.color_identity)
    for color in ("W", "U", "B"):
        if color in colors:
            return color
    raise AssertionError(f"gold3 Binder 1 card with no W/U/B color: {card.name!r}")


def _classify_binder2_gold3(card: MatchedCard) -> str:
    colors = set(card.color_identity)
    if len(colors) >= 2:
        return "Gold"
    for color in ("R", "G"):
        if color in colors:
            return color
    raise AssertionError(f"gold3 Binder 2 card with no R/G color: {card.name!r}")


def _classify_binder3_gold3(card: MatchedCard) -> str:
    if "Token" in card.types:
        return "Token"
    if "Land" in card.types:
        colors = frozenset(card.color_identity)
        if not colors:
            return "Land: Colorless"
        if len(colors) == 1:
            return f"Land: {next(iter(colors))}"
        return "Land: Multicolor"
    return "Colorless spells"  # guaranteed colorless non-land/token to reach here


def _assign_binder_gold3(card: MatchedCard) -> int:
    """Land/Token and colorless spells all land in Binder 3 (the
    "colorless-flavored" binder); multicolor is "Gold" in Binder 2.
    """
    if "Land" in card.types or "Token" in card.types:
        return 3

    colors = set(card.color_identity)
    if len(colors) >= 2:
        return 2  # Gold
    if not colors:
        return 3  # colorless spell
    if colors <= {"W", "U", "B"}:
        return 1
    return 2  # R or G


GOLD3_SCHEME = BinderScheme(
    name="gold3",
    description=(
        "Binder 1 White/Blue/Black, Binder 2 Red/Green/Gold (multicolor), "
        "Binder 3 Colorless/Lands/Tokens."
    ),
    assign_binder=_assign_binder_gold3,
    binders=(
        BinderDef(
            1,
            "White/Blue/Black",
            _classify_binder1_gold3,
            (Subgroup("W"), Subgroup("U"), Subgroup("B")),
        ),
        BinderDef(
            2,
            "Red/Green/Gold",
            _classify_binder2_gold3,
            (Subgroup("R"), Subgroup("G"), Subgroup("Gold", weight=2)),
        ),
        BinderDef(
            3,
            "Colorless/Lands/Tokens",
            _classify_binder3_gold3,
            (
                Subgroup("Colorless spells", weight=2),
                Subgroup("Land: Colorless", weight=3),
                Subgroup("Land: W", weight=1),
                Subgroup("Land: U", weight=2),
                Subgroup("Land: B", weight=1),
                Subgroup("Land: R", weight=2),
                Subgroup("Land: G", weight=1),
                Subgroup("Land: Multicolor", weight=4),
                Subgroup("Token", fixed_pages=BINDER_TOKEN_PAGES),
            ),
        ),
    ),
)


SCHEMES: dict[str, BinderScheme] = {
    CLASSIC4_SCHEME.name: CLASSIC4_SCHEME,
    GOLD3_SCHEME.name: GOLD3_SCHEME,
}


def _apportion_pages(total_pages: int, weights: tuple[int, ...]) -> list[int]:
    """Largest-remainder apportionment of `total_pages` across weighted
    groups, guaranteeing at least 1 page per group.
    """
    count = len(weights)
    guaranteed = count
    remaining = total_pages - guaranteed
    if remaining < 0:
        raise ValueError(
            f"Not enough pages ({total_pages}) to give each of {count} groups "
            "at least one page."
        )
    total_weight = sum(weights)
    exact_shares = [remaining * weight / total_weight for weight in weights]
    base = [int(share) for share in exact_shares]
    leftover = remaining - sum(base)
    by_remainder = sorted(
        range(count), key=lambda i: exact_shares[i] - base[i], reverse=True
    )
    pages = [1 + b for b in base]
    for i in by_remainder[:leftover]:
        pages[i] += 1
    return pages


def pages_per_binder(binder_def: BinderDef, total_pages: int) -> dict[str, int]:
    fixed = {
        sg.label: sg.fixed_pages
        for sg in binder_def.subgroups
        if sg.fixed_pages is not None
    }
    weighted = [sg for sg in binder_def.subgroups if sg.fixed_pages is None]

    pages: dict[str, int] = dict(fixed)
    if weighted:
        remaining = total_pages - sum(fixed.values())
        weights = tuple(sg.weight for sg in weighted)
        apportioned = _apportion_pages(remaining, weights)
        pages.update(zip((sg.label for sg in weighted), apportioned, strict=True))
    return pages


def _fit_reserve(total_units: int, allotted_pages: int, max_reserve: int) -> int:
    """Largest reserve-per-page (0..max_reserve) that still fits
    `total_units` slots within `allotted_pages`, shrinking the reserve
    one step at a time before ever letting a subgroup overflow into its
    neighbor's pages.
    """
    if total_units == 0:
        return max_reserve
    for reserve in range(max_reserve, -1, -1):
        usable = PAGE_SIZE - reserve
        pages_needed = -(-total_units // usable)  # ceil
        if pages_needed <= allotted_pages:
            return reserve
    return 0  # doesn't fit even with 0 reserve -- true overflow, handled by the caller


def _place_subgroup(
    entries: list[tuple[CollectionRow, MatchedCard]],
    binder_number: int,
    binder_label: str,
    subgroup_label: str,
    start_page: int,
    allotted_pages: int,
    reserve_per_page: int,
) -> tuple[list[BinderSlot], int]:
    """Returns the placed slots and how many pages this subgroup actually used.

    Before overflowing into the next subgroup's pages, this shrinks its
    own reserve (down to 0 if needed) to fit within `allotted_pages`.
    """
    sorted_entries = sorted(entries, key=lambda pair: sort_key(*pair))
    total_units = sum(copies_needed(row, card) for row, card in sorted_entries)

    reserve = _fit_reserve(total_units, allotted_pages, reserve_per_page)
    usable_per_page = PAGE_SIZE - reserve
    if reserve < reserve_per_page:
        print(
            f"NOTE: binder {binder_number} ({binder_label}) subgroup "
            f"{subgroup_label!r} reduced its per-page reserve from "
            f"{reserve_per_page} to {reserve} to fit its {allotted_pages}-page "
            "allotment.",
            file=sys.stderr,
        )

    slots: list[BinderSlot] = []
    cursor = 0
    for row, card in sorted_entries:
        for _ in range(copies_needed(row, card)):
            page_in_group, slot_in_page = divmod(cursor, usable_per_page)
            page = start_page + page_in_group
            slots.append(
                BinderSlot(
                    binder=binder_number,
                    page=page,
                    slot_in_page=slot_in_page + 1,
                    global_slot=(page - 1) * PAGE_SIZE + slot_in_page + 1,
                    row=row,
                    card=card,
                )
            )
            cursor += 1

    pages_needed = -(-cursor // usable_per_page) if cursor else 0  # ceil
    if pages_needed > allotted_pages:
        print(
            f"WARNING: binder {binder_number} ({binder_label}) subgroup "
            f"{subgroup_label!r} needs {pages_needed} pages even with 0 "
            f"reserve, exceeds its {allotted_pages}-page allotment -- "
            "overflowing into the next subgroup's pages.",
            file=sys.stderr,
        )
    return slots, pages_needed


def allocate_slots(
    entries: list[tuple[CollectionRow, MatchedCard]],
    binder_def: BinderDef,
    reserve_per_page: int,
) -> list[BinderSlot]:
    """Places sorted entries into slots, one fixed page-block per
    within-binder subgroup (see `binder_def.subgroups`), leaving
    `reserve_per_page` empty pockets at the end of every page.

    Subgroups never share a page with each other -- each gets its own
    dedicated block of pages -- so a color/category always has guaranteed
    room to grow without displacing its neighbor. Reserving room on every
    page (not just at the end of a block) means a newly-arrived card can
    usually be inserted near its correct sorted position on its own page
    without having to shift every later card down by one. If a subgroup's
    real card count doesn't fit its allotment even with 0 reserve, it
    shrinks its own reserve as far as needed before ever spilling into the
    next subgroup's pages (see `_fit_reserve`).
    """
    allotted = pages_per_binder(binder_def, TOTAL_PAGES)

    grouped: dict[str, list[tuple[CollectionRow, MatchedCard]]] = defaultdict(list)
    for row, card in entries:
        grouped[binder_def.classify(card)].append((row, card))

    slots: list[BinderSlot] = []
    next_start_page = 1
    for subgroup in binder_def.subgroups:
        allotted_pages = allotted[subgroup.label]
        group_slots, pages_used = _place_subgroup(
            grouped.get(subgroup.label, []),
            binder_def.number,
            binder_def.label,
            subgroup.label,
            next_start_page,
            allotted_pages,
            reserve_per_page,
        )
        slots.extend(group_slots)
        next_start_page += max(pages_used, allotted_pages)

    total_slots = len(slots)
    if total_slots > BINDER_CAPACITY:
        print(
            f"WARNING: binder {binder_def.number} ({binder_def.label}) needs "
            f"{total_slots} slots, exceeds the {BINDER_CAPACITY}-slot capacity.",
            file=sys.stderr,
        )
    return slots


def build_binders(
    matched: list[tuple[CollectionRow, MatchedCard]],
    scheme: BinderScheme,
    reserve_per_page: int,
) -> dict[int, list[BinderSlot]]:
    groups: dict[int, list[tuple[CollectionRow, MatchedCard]]] = defaultdict(list)
    for row, card in matched:
        groups[scheme.assign_binder(card)].append((row, card))
    return {
        binder_def.number: allocate_slots(
            groups.get(binder_def.number, []), binder_def, reserve_per_page
        )
        for binder_def in scheme.binders
    }


def _color_identity_str(color_identity: tuple[str, ...]) -> str:
    return ",".join(color_identity)


def write_csv(
    path: Path,
    binders: dict[int, list[BinderSlot]],
    unmatched: list[UnmatchedRow],
    binder_labels: dict[int, str],
) -> None:
    fieldnames = [
        "binder",
        "binder_label",
        "page",
        "slot_in_page",
        "global_slot",
        "status",
        "match_method",
        "card_name",
        "csv_name",
        "set_code",
        "collector_number",
        "foil",
        "count",
        "tradelist_count",
        "color_identity",
        "mana_value",
        "type_line",
        "type_category",
        "reason",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for binder in sorted(binders):
            for slot in binders[binder]:
                writer.writerow({
                    "binder": slot.binder,
                    "binder_label": binder_labels[slot.binder],
                    "page": slot.page,
                    "slot_in_page": slot.slot_in_page,
                    "global_slot": slot.global_slot,
                    "status": "matched",
                    "match_method": slot.card.match_method,
                    "card_name": slot.card.name,
                    "csv_name": slot.row.name,
                    "set_code": slot.card.set_code,
                    "collector_number": slot.card.number,
                    "foil": slot.row.foil,
                    "count": slot.row.count,
                    "tradelist_count": slot.row.tradelist_count,
                    "color_identity": _color_identity_str(slot.card.color_identity),
                    "mana_value": slot.card.mana_value,
                    "type_line": slot.card.type_line,
                    "type_category": type_category(slot.card.types),
                    "reason": "",
                })

        for entry in sorted(unmatched, key=lambda u: u.row.line_no):
            writer.writerow({
                "binder": "",
                "binder_label": "",
                "page": "",
                "slot_in_page": "",
                "global_slot": "",
                "status": "unmatched",
                "match_method": "",
                "card_name": "",
                "csv_name": entry.row.name,
                "set_code": entry.row.edition,
                "collector_number": entry.row.collector_number,
                "foil": entry.row.foil,
                "count": entry.row.count,
                "tradelist_count": entry.row.tradelist_count,
                "color_identity": "",
                "mana_value": "",
                "type_line": "",
                "type_category": "",
                "reason": entry.reason,
            })


def _slot_to_dict(slot: BinderSlot) -> dict[str, object]:
    return {
        "slot_in_page": slot.slot_in_page,
        "global_slot": slot.global_slot,
        "card_name": slot.card.name,
        "csv_name": slot.row.name,
        "set_code": slot.card.set_code,
        "collector_number": slot.card.number,
        "foil": slot.row.foil,
        "count": slot.row.count,
        "tradelist_count": slot.row.tradelist_count,
        "color_identity": list(slot.card.color_identity),
        "mana_value": slot.card.mana_value,
        "type_line": slot.card.type_line,
        "type_category": type_category(slot.card.types),
        "match_method": slot.card.match_method,
    }


def write_json(
    path: Path,
    binders: dict[int, list[BinderSlot]],
    unmatched: list[UnmatchedRow],
    source_csv: Path,
    total_matched_rows: int,
    scheme: BinderScheme,
    binder_labels: dict[int, str],
) -> None:
    binders_payload: dict[str, object] = {}
    slots_per_binder: dict[str, int] = {}

    for binder, slots in binders.items():
        pages: dict[str, list[dict[str, object]]] = defaultdict(list)
        for slot in slots:
            pages[str(slot.page)].append(_slot_to_dict(slot))
        binders_payload[str(binder)] = {
            "label": binder_labels[binder],
            "total_slots_used": len(slots),
            "pages": pages,
        }
        slots_per_binder[str(binder)] = len(slots)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "source_csv": source_csv.name,
        "scheme": scheme.name,
        "binders": binders_payload,
        "unmatched": [
            {
                "csv_name": entry.row.name,
                "edition": entry.row.edition,
                "collector_number": entry.row.collector_number,
                "count": entry.row.count,
                "line_no": entry.row.line_no,
                "reason": entry.reason,
            }
            for entry in sorted(unmatched, key=lambda u: u.row.line_no)
        ],
        "summary": {
            "total_csv_rows": total_matched_rows + len(unmatched),
            "total_matched_rows": total_matched_rows,
            "total_unmatched_rows": len(unmatched),
            "slots_per_binder": slots_per_binder,
        },
    }

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def _md_slot_row(slot: BinderSlot) -> str:
    foil = "x" if slot.row.foil else "-"
    mana_value = "" if slot.card.mana_value is None else slot.card.mana_value
    return (
        f"| {slot.slot_in_page} "
        f"| {_md_escape(slot.card.name)} "
        f"| {slot.card.set_code} "
        f"| {slot.card.number} "
        f"| {foil} "
        f"| {mana_value} "
        f"| {_md_escape(type_category(slot.card.types))} |"
    )


def _md_blank_row(slot_in_page: int) -> str:
    return f"| {slot_in_page} | *(empty)* | | | | | |"


def write_markdown(
    path: Path,
    binders: dict[int, list[BinderSlot]],
    unmatched: list[UnmatchedRow],
    binder_labels: dict[int, str],
) -> None:
    lines: list[str] = ["# Collection Binder Map", ""]

    for binder in sorted(binder_labels):
        slots = binders.get(binder, [])
        label = binder_labels[binder]
        lines.append(
            f"## Binder {binder}: {label} ({len(slots)}/{BINDER_CAPACITY} slots)"
        )
        lines.append("")

        pages: dict[int, list[BinderSlot]] = defaultdict(list)
        for slot in slots:
            pages[slot.page].append(slot)

        for page in sorted(pages):
            lines.append(f"### Page {page}")
            lines.append("")
            lines.append("| Slot | Card | Set | # | Foil | MV | Type |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            page_slots = pages[page]
            for slot in page_slots:
                lines.append(_md_slot_row(slot))
            # Pad the page's table to a full 9 pockets, so an incomplete
            # page still shows every empty pocket left for future cards.
            for slot_in_page in range(len(page_slots) + 1, PAGE_SIZE + 1):
                lines.append(_md_blank_row(slot_in_page))
            lines.append("")

    if unmatched:
        lines.append(f"## Unmatched ({len(unmatched)})")
        lines.append("")
        lines.append("| Line | Card | Edition | # | Reason |")
        lines.append("| --- | --- | --- | --- | --- |")
        for entry in sorted(unmatched, key=lambda u: u.row.line_no):
            lines.append(
                f"| {entry.row.line_no} "
                f"| {_md_escape(entry.row.name)} "
                f"| {entry.row.edition} "
                f"| {entry.row.collector_number} "
                f"| {_md_escape(entry.reason)} |"
            )
        lines.append("")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def print_summary(
    binders: dict[int, list[BinderSlot]],
    unmatched: list[UnmatchedRow],
    binder_labels: dict[int, str],
) -> None:
    for binder in sorted(binder_labels):
        used = len(binders.get(binder, []))
        label = binder_labels[binder]
        print(f"Binder {binder} ({label}): {used}/{BINDER_CAPACITY} slots used")

    print(f"Unmatched rows: {len(unmatched)}")
    for entry in sorted(unmatched, key=lambda u: u.row.line_no):
        print(
            f"  - line {entry.row.line_no}: {entry.row.name!r} "
            f"({entry.row.edition}/{entry.row.collector_number}) — {entry.reason}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split the Moxfield collection export into physical binders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        metavar="PATH",
        help="Path to the Moxfield 'Haves' CSV export.",
    )
    parser.add_argument(
        "--scheme",
        choices=sorted(SCHEMES),
        default=DEFAULT_SCHEME,
        help=(
            "Binder layout to use (default: %(default)s). "
            + " ".join(
                f"{name}: {scheme.description}" for name, scheme in SCHEMES.items()
            )
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_CSV_OUTPUT,
        metavar="PATH",
        help="Path to write the binder map as CSV.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        metavar="PATH",
        help="Path to write the binder map as JSON.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT,
        metavar="PATH",
        help="Path to write the binder map as Markdown (one table per page).",
    )
    parser.add_argument(
        "--reserve-per-page",
        type=int,
        default=DEFAULT_RESERVE_PER_PAGE,
        metavar="N",
        help=(
            "Empty pockets to leave at the end of every page, for cards "
            f"you're expecting soon (default: {DEFAULT_RESERVE_PER_PAGE})."
        ),
    )
    args = parser.parse_args()
    if not (0 <= args.reserve_per_page < PAGE_SIZE):
        parser.error(f"--reserve-per-page must be between 0 and {PAGE_SIZE - 1}.")
    return args


async def run(
    csv_path: Path,
    output_csv: Path,
    output_json: Path,
    output_md: Path,
    reserve_per_page: int,
    scheme: BinderScheme,
) -> None:
    rows = parse_csv(csv_path)
    async with AsyncSessionLocal() as session:
        matched, unmatched = await resolve_all(rows, session)

    for output_path in (output_csv, output_json, output_md):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    binder_labels = {
        binder_def.number: binder_def.label for binder_def in scheme.binders
    }
    binders = build_binders(matched, scheme, reserve_per_page)
    write_csv(output_csv, binders, unmatched, binder_labels)
    write_json(
        output_json, binders, unmatched, csv_path, len(matched), scheme, binder_labels
    )
    write_markdown(output_md, binders, unmatched, binder_labels)
    print_summary(binders, unmatched, binder_labels)


def main() -> None:
    args = _parse_args()
    asyncio.run(
        run(
            args.csv,
            args.output_csv,
            args.output_json,
            args.output_md,
            args.reserve_per_page,
            SCHEMES[args.scheme],
        )
    )


if __name__ == "__main__":
    main()
