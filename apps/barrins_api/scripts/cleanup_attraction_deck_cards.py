"""One-off cleanup — removes Attraction cards persisted in `bs_deck_cards`.

Scrapes ingested before the 2026-08-19 fix (`app/services/scripture/
ingester.py`'s `is_attraction` check) stored Attraction cards (Un-set
mechanic, `mj_cards.subtypes` contains "Attraction" -- MTGJSON files it
as a subtype, not a top-level type) as ordinary sideboard
lines — reported for deck `1989ca0f-a564-4866-94d1-94ba96e84d86`, but the
same scrapers could have written the same rows for any tournament deck.
The application must not treat Attractions at all, so this removes every
such row, not just the reported deck's.

Usage
-----
    python scripts/cleanup_attraction_deck_cards.py            # dry run
    python scripts/cleanup_attraction_deck_cards.py --apply    # deletes

Dry run by default: prints the affected decks and row count, deletes
nothing. Pass --apply to actually delete. Safe to re-run — a second run
with --apply finds nothing left to delete.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.database.connection import AsyncSessionLocal
from app.models.mtgjson import Card
from app.models.scripture import BSDeck, BSDeckCard


async def _attraction_names(session) -> set[str]:
    rows = (
        await session.execute(
            select(Card.name, Card.face_name).where(
                Card.subtypes.contains(["Attraction"])
            )
        )
    ).all()
    names: set[str] = set()
    for name, face_name in rows:
        names.add(name)
        if face_name:
            names.add(face_name)
    return names


async def _run(apply: bool) -> None:
    async with AsyncSessionLocal() as session:
        names = await _attraction_names(session)
        if not names:
            print("No Attraction cards found in mj_cards — nothing to do.")
            return

        affected = (
            await session.execute(
                select(
                    BSDeckCard.deck_id, BSDeckCard.card_name, BSDeckCard.count
                ).where(BSDeckCard.card_name.in_(names))
            )
        ).all()

        if not affected:
            print("No bs_deck_cards rows reference an Attraction — nothing to do.")
            return

        by_deck: dict[object, list[str]] = {}
        for deck_id, card_name, count in affected:
            by_deck.setdefault(deck_id, []).append(f"{card_name} x{count}")

        deck_players = {  # noqa: C416 -- Row isn't a plain tuple for ty's dict() overload
            deck_id: player
            for deck_id, player in (
                await session.execute(
                    select(BSDeck.id, BSDeck.player).where(
                        BSDeck.id.in_(by_deck.keys())
                    )
                )
            ).all()
        }

        print(f"{len(affected)} bs_deck_cards row(s) across {len(by_deck)} deck(s):")
        for deck_id, entries in by_deck.items():
            player = deck_players.get(deck_id, "?")
            print(f"  deck {deck_id} ({player}): {', '.join(entries)}")

        if not apply:
            print("\nDry run — no rows deleted. Re-run with --apply to delete.")
            return

        await session.execute(delete(BSDeckCard).where(BSDeckCard.card_name.in_(names)))
        await session.commit()
        print(f"\nDeleted {len(affected)} row(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete the rows (default: dry run, prints only).",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.apply))


if __name__ == "__main__":
    main()
