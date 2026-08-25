"""Match `TSCardTest` entries against decklist version diffs (S16).

Distinct from `decklist_diff.py`'s pure content-vs-content diffing --
this module is the card-test x decklist-diff crossover, kept separate so
`decklist_diff.py` stays unaware of card tests.
"""

import itertools
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tamiyo_scroll import TSCardTest, TSPersonalDecklistVersion
from app.schemas.responses_tamiyo_scroll import ResponseDecklistCardDiff
from app.services.scripture.card_resolver import resolve_card_name_or_raw
from app.services.tamiyo_scroll.decklist_diff import diff_decklist_cards


async def annotate_diff_cards_with_card_tests(
    session: AsyncSession,
    cards: list[ResponseDecklistCardDiff],
    card_tests: Sequence[TSCardTest],
) -> tuple[list[ResponseDecklistCardDiff], set[uuid.UUID]]:
    """Attach matching card-test notes to each removed/added diff line.

    A `removed` line is matched against every card test's
    `removed_card_name`; an `added` line against `added_card_name` --
    names compared after canonicalizing both sides through
    `resolve_card_name_or_raw`. `unchanged`/`quantity_changed` lines
    never match (a card test means "X removed, Y added", not a same-card
    quantity change). Returns the annotated cards plus the ids of every
    card test that matched at least one line here.
    """
    matched_ids: set[uuid.UUID] = set()
    annotated: list[ResponseDecklistCardDiff] = []
    for card in cards:
        notes: list[str] = []
        if card.status == "removed":
            canonical_card = await resolve_card_name_or_raw(session, card.name)
            for test in card_tests:
                canonical_test = await resolve_card_name_or_raw(
                    session, test.removed_card_name
                )
                if canonical_test == canonical_card:
                    matched_ids.add(test.id)
                    if test.notes:
                        notes.append(test.notes)
        elif card.status == "added":
            canonical_card = await resolve_card_name_or_raw(session, card.name)
            for test in card_tests:
                canonical_test = await resolve_card_name_or_raw(
                    session, test.added_card_name
                )
                if canonical_test == canonical_card:
                    matched_ids.add(test.id)
                    if test.notes:
                        notes.append(test.notes)
        annotated.append(card.model_copy(update={"card_test_notes": notes}))
    return annotated, matched_ids


async def compute_matched_card_test_ids(
    session: AsyncSession, personal_deck_id: uuid.UUID
) -> set[uuid.UUID]:
    """Union of matched card-test ids across every consecutive version
    pair in this deck's history -- a card test counts as matched if it
    lines up with *any* real decklist change, anywhere."""
    versions_result = await session.execute(
        select(TSPersonalDecklistVersion)
        .where(TSPersonalDecklistVersion.personal_deck_id == personal_deck_id)
        .order_by(TSPersonalDecklistVersion.version)
    )
    versions = versions_result.scalars().all()

    tests_result = await session.execute(
        select(TSCardTest).where(TSCardTest.personal_deck_id == personal_deck_id)
    )
    card_tests = tests_result.scalars().all()

    matched_ids: set[uuid.UUID] = set()
    for prior, current in itertools.pairwise(versions):
        cards = diff_decklist_cards(prior.content, current.content)
        _, matched = await annotate_diff_cards_with_card_tests(
            session, cards, card_tests
        )
        matched_ids |= matched
    return matched_ids
