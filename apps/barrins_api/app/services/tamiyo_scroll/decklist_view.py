"""Structured Commander/Library decklist view.

Resolves each parsed card line against `mj_cards` (mana_cost/type_line/
text/keywords/scryfall_id), reusing `color_decklist`'s per-line status
rather than recomputing it. `color_decklist` itself stays untouched —
it also backs the PDF report path (`report.py::get_deck_period_report`).
"""

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mtgjson import Card
from app.models.tamiyo_scroll import TSCardTest
from app.schemas.responses_tamiyo_scroll import (
    ResponseDecklistCard,
    ResponseDecklistLine,
    ResponseDecklistTypeGroup,
    ResponseDecklistView,
)
from app.services.decklist_sort import decklist_sort_key, group_by_category
from app.services.scripture.card_resolver import resolve_card_name
from app.services.tamiyo_scroll.decklist_coloring import (
    LineStatus,
    color_decklist,
    commander_section_indices,
    parse_card_line,
)


async def _resolved_by_name(
    session: AsyncSession, names: Sequence[str]
) -> dict[str, Card | None]:
    """One resolver pass + one batched `mj_cards` query — mirrors
    `tolaria_news.decks._resolved_cards`, adapted for name-keyed (not
    row-id-keyed) lookup since there's no `bs_deck_cards` row here."""
    canonical_by_name: dict[str, str] = {}
    for name in names:
        canonical = await resolve_card_name(session, name)
        if canonical is not None:
            canonical_by_name[name] = canonical

    canonical_names = set(canonical_by_name.values())
    if not canonical_names:
        return dict.fromkeys(names)

    matches = (
        (
            await session.execute(
                select(Card).where(
                    or_(
                        Card.name.in_(canonical_names),
                        Card.face_name.in_(canonical_names),
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    card_by_name: dict[str, Card] = {}
    for match in matches:
        card_by_name.setdefault(match.name, match)
        if match.face_name:
            card_by_name.setdefault(match.face_name, match)

    return {name: card_by_name.get(canonical_by_name.get(name, "")) for name in names}


def _as_decklist_card(
    qty: int, name: str, status: LineStatus, resolved: Card | None
) -> ResponseDecklistCard:
    return ResponseDecklistCard(
        qty=qty,
        name=resolved.name if resolved is not None else name,
        status=status,
        mana_cost=resolved.mana_cost if resolved is not None else None,
        type_line=resolved.type_line if resolved is not None else None,
        text=resolved.text if resolved is not None else None,
        keywords=resolved.keywords if resolved is not None else [],
        scryfall_id=resolved.scryfall_id if resolved is not None else None,
    )


async def build_decklist_view(
    session: AsyncSession, content: str, card_tests: Sequence[TSCardTest]
) -> ResponseDecklistView:
    lines = content.splitlines()
    colored = color_decklist(content, card_tests)  # same order/length as `lines`
    commander_idx = commander_section_indices(lines)

    parsed: list[tuple[int, int, str, LineStatus]] = []  # (idx, qty, name, status)
    unparsed: list[ResponseDecklistLine] = []
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        status = colored[i]["status"]
        if not stripped or stripped.casefold() == "commander":
            continue  # blank lines / the header marker itself carry no card
        result = parse_card_line(raw)
        if result is None:
            unparsed.append(ResponseDecklistLine(line=raw, status=status))
            continue
        qty, name = result
        parsed.append((i, qty, name, status))

    resolved_by_name = await _resolved_by_name(session, [p[2] for p in parsed])

    commander_cards: list[tuple[ResponseDecklistCard, Card | None]] = []
    library_cards: list[tuple[ResponseDecklistCard, Card | None]] = []
    for i, qty, name, status in parsed:
        resolved = resolved_by_name.get(name)
        card = _as_decklist_card(qty, name, status, resolved)
        (commander_cards if i in commander_idx else library_cards).append(
            (card, resolved)
        )

    def _key(pair: tuple[ResponseDecklistCard, Card | None]) -> tuple[int, float, str]:
        card, resolved = pair
        mana_value = resolved.mana_value if resolved is not None else None
        return decklist_sort_key(card.type_line, mana_value, card.name)

    commander_cards.sort(key=_key)
    library_cards.sort(key=_key)

    library_groups = [
        ResponseDecklistTypeGroup(
            category=category,
            count=len(group),
            cards=[card for card, _ in group],
        )
        for category, group in group_by_category(
            library_cards, lambda pair: pair[0].type_line
        )
    ]

    return ResponseDecklistView(
        commander_cards=[card for card, _ in commander_cards],
        library_cards=library_groups,
        unparsed_lines=unparsed,
    )
