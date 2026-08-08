"""Tests for T3: `POST /internal/scripture/ingest` and its supporting services.

Covers the route (auth gate, idempotency, delete-and-reinsert deck cards)
and the card-name resolver (`app/services/scripture/card_resolver.py`) —
exact match, case/accent normalization, Unicode compatibility folding,
face-name matching, and skip-on-no-match behavior.
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import func, select

from app.config import settings
from app.models.mtgjson import Card, MTGSet
from app.models.scripture import (
    BSDeck,
    BSDeckBoard,
    BSDeckCard,
    BSRoundMatch,
    BSStanding,
    BSTournament,
)

_TOKEN = "test-scripture-token"  # noqa: S105


@pytest.fixture(autouse=True)
def _configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.base, "scripture_ingest_token", SecretStr(_TOKEN))


@pytest.fixture()
async def seeded_cards(db_session) -> None:
    """Real-shaped `cards`/`sets` rows exercising the resolver's cases:

    - "Sol Ring": plain exact-name match.
    - "Bonecrusher Giant // Stomp": adventure card, two face rows — a
      scraped line naming just the front face ("Bonecrusher Giant")
      must resolve via `face_name`, not the combined `name`.
    - a card whose canonical name uses U+A789 MODIFIER LETTER COLON (the
      real Unicode compatibility character some MTG card names use) — a
      scraped line typing a plain ASCII colon instead must still match.
    """
    mtg_set = MTGSet(
        code="TST",
        name="Test Set",
        release_date=date(2026, 1, 1),
        type="expansion",
        base_set_size=10,
        total_set_size=10,
        keyrune_code="tst",
    )
    db_session.add(mtg_set)
    await db_session.flush()

    db_session.add_all(
        [
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Sol Ring",
                type_line="Artifact",
                rarity="uncommon",
                number="1",
            ),
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Bonecrusher Giant // Stomp",
                face_name="Bonecrusher Giant",
                side="a",
                layout="adventure",
                type_line="Creature — Giant",
                rarity="rare",
                number="2",
            ),
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Bonecrusher Giant // Stomp",
                face_name="Stomp",
                side="b",
                layout="adventure",
                type_line="Sorcery — Adventure",
                rarity="rare",
                number="2",
            ),
            Card(
                id=uuid.uuid4(),
                set_code="TST",
                name="Ratonhnhaké꞉ton",  # noqa: RUF001
                type_line="Legendary Creature",
                rarity="mythic",
                number="3",
            ),
        ]
    )
    await db_session.commit()


def _payload(anchor_suffix: str = "1", mainboard: list[dict] | None = None) -> dict:
    return {
        "source": "mtgtop8",
        "tournament": {
            "date": "2026-04-07",
            "name": "Test Cup",
            "url": "https://mtgtop8.com/event?e=99999",
            "format": "Legacy",
            "players": 32,
        },
        "decks": [
            {
                "date": "2026-04-07",
                "player": "Alice",
                "result": "1",
                "anchor_uri": f"https://mtgtop8.com/event?e=99999&d={anchor_suffix}",
                "mainboard": mainboard
                if mainboard is not None
                else [
                    {"count": 1, "name": "Sol Ring"},
                    {"count": 1, "name": "sol ring"},
                    {"count": 1, "name": "Bonecrusher Giant"},
                    {"count": 1, "name": "Totally Fake Card XYZ"},
                ],
                "sideboard": [
                    {"count": 1, "name": "Ratonhnhake:ton"},
                ],
            }
        ],
        "rounds": [
            {
                "round_name": "Round 1",
                "matches": [{"player_1": "Alice", "player_2": "Bob", "result": "2-0"}],
            }
        ],
        "standings": [
            {
                "rank": 1,
                "player": "Alice",
                "points": 9,
                "wins": 3,
                "losses": 0,
                "draws": 0,
                "omwp": 0.6,
                "gwp": 0.7,
                "ogwp": 0.55,
            }
        ],
    }


class TestIngestAuth:
    async def test_missing_token_is_401(self, client: AsyncClient, seeded_cards):
        resp = await client.post("/internal/scripture/ingest", json=_payload())
        assert resp.status_code == 401

    async def test_wrong_token_is_401(self, client: AsyncClient, seeded_cards):
        resp = await client.post(
            "/internal/scripture/ingest",
            json=_payload(),
            headers={"X-Scripture-Token": "wrong-token"},
        )
        assert resp.status_code == 401

    async def test_unconfigured_token_is_503(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(settings.base, "scripture_ingest_token", None)
        resp = await client.post(
            "/internal/scripture/ingest",
            json=_payload(),
            headers={"X-Scripture-Token": _TOKEN},
        )
        assert resp.status_code == 503


class TestIngestRoute:
    async def test_ingest_upserts_everything_and_resolves_card_names(
        self, client: AsyncClient, db_session, seeded_cards
    ):
        resp = await client.post(
            "/internal/scripture/ingest",
            json=_payload(),
            headers={"X-Scripture-Token": _TOKEN},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decks_upserted"] == 1
        # Sol Ring + "sol ring" merge into one row (count 2), Bonecrusher
        # Giant resolves via face_name, Totally Fake Card XYZ is skipped —
        # mainboard contributes 2 rows, sideboard 1 (the special-colon card).
        assert body["deck_cards_upserted"] == 3
        assert body["rounds_upserted"] == 1
        assert body["round_matches_upserted"] == 1
        assert body["standings_upserted"] == 1
        assert body["skipped_card_names"] == ["Totally Fake Card XYZ"]

        tournament_id = uuid.UUID(body["tournament_id"])
        tournament = await db_session.get(BSTournament, tournament_id)
        assert tournament is not None
        assert tournament.name == "Test Cup"

        deck = (
            await db_session.execute(
                select(BSDeck).where(BSDeck.tournament_id == tournament.id)
            )
        ).scalar_one()

        cards = (
            (
                await db_session.execute(
                    select(BSDeckCard).where(BSDeckCard.deck_id == deck.id)
                )
            )
            .scalars()
            .all()
        )
        by_name = {c.card_name: c for c in cards}
        assert by_name["Sol Ring"].count == 2
        assert by_name["Sol Ring"].board == BSDeckBoard.mainboard
        assert by_name["Bonecrusher Giant"].board == BSDeckBoard.mainboard
        # Canonical spelling stored, not the scraper's plain-ASCII input.
        assert by_name["Ratonhnhaké꞉ton"].board == BSDeckBoard.sideboard  # noqa: RUF001

        match = (await db_session.execute(select(BSRoundMatch))).scalar_one()
        assert match.result == "2-0"

        standing = (await db_session.execute(select(BSStanding))).scalar_one()
        assert standing.player == "Alice"

    async def test_ingest_is_idempotent(
        self, client: AsyncClient, db_session, seeded_cards
    ):
        payload = _payload()
        first = await client.post(
            "/internal/scripture/ingest",
            json=payload,
            headers={"X-Scripture-Token": _TOKEN},
        )
        second = await client.post(
            "/internal/scripture/ingest",
            json=payload,
            headers={"X-Scripture-Token": _TOKEN},
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["tournament_id"] == second.json()["tournament_id"]

        tournament_count = (
            await db_session.execute(select(func.count()).select_from(BSTournament))
        ).scalar_one()
        assert tournament_count == 1

        deck_count = (
            await db_session.execute(select(func.count()).select_from(BSDeck))
        ).scalar_one()
        assert deck_count == 1

        card_count = (
            await db_session.execute(select(func.count()).select_from(BSDeckCard))
        ).scalar_one()
        assert card_count == 3

    async def test_resweep_replaces_deck_cards(
        self, client: AsyncClient, db_session, seeded_cards
    ):
        """A re-ingest with a changed decklist (MTGO's ~3-day edit window)
        must replace the old card lines, not accumulate alongside them."""
        first = await client.post(
            "/internal/scripture/ingest",
            json=_payload(mainboard=[{"count": 1, "name": "Sol Ring"}]),
            headers={"X-Scripture-Token": _TOKEN},
        )
        assert first.status_code == 200

        second = await client.post(
            "/internal/scripture/ingest",
            json=_payload(mainboard=[{"count": 1, "name": "Bonecrusher Giant"}]),
            headers={"X-Scripture-Token": _TOKEN},
        )
        assert second.status_code == 200

        deck = (await db_session.execute(select(BSDeck))).scalar_one()
        cards = (
            (
                await db_session.execute(
                    select(BSDeckCard).where(
                        BSDeckCard.deck_id == deck.id,
                        BSDeckCard.board == BSDeckBoard.mainboard,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert [c.card_name for c in cards] == ["Bonecrusher Giant"]
