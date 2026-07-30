"""Model/migration tests for the `bs_*` (Barrin's Scripture) domain.

Mirrors `tests/tamiyo_scroll/`'s structure: direct ORM round-trips against
the real (test) database, not HTTP routes -- there are no `bs_*` routes
yet (T3/T4 build the ingestion path and BFF on top of this schema).
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.scripture import (
    BSDeck,
    BSDeckBoard,
    BSDeckCard,
    BSRound,
    BSRoundMatch,
    BSSource,
    BSStanding,
    BSTournament,
)


@pytest.fixture()
async def tournament(db_session) -> BSTournament:
    t = BSTournament(
        source=BSSource.mtgtop8,
        date=date(2026, 4, 7),
        name="CDF DC 2026 Main Event",
        url="https://mtgtop8.com/event?e=87792&f=EDH",
        format="Duel Commander",
        players=391,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


class TestBSTournament:
    async def test_round_trip(self, db_session, tournament: BSTournament) -> None:
        fetched = await db_session.get(BSTournament, tournament.id)
        assert fetched is not None
        assert fetched.source == BSSource.mtgtop8
        assert fetched.url == "https://mtgtop8.com/event?e=87792&f=EDH"
        assert fetched.players == 391
        assert fetched.created_at is not None

    async def test_duplicate_url_rejected(
        self, db_session, tournament: BSTournament
    ) -> None:
        # Same url as the fixture tournament -- must violate uq_bs_tournaments_url,
        # the natural key an archive replay upserts on.
        dupe = BSTournament(
            source=BSSource.mtgtop8,
            date=tournament.date,
            name="CDF DC 2026 Main Event (re-scraped)",
            url=tournament.url,
            format="Duel Commander",
            players=391,
        )
        db_session.add(dupe)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestBSDeck:
    async def test_round_trip_with_range_result(
        self, db_session, tournament: BSTournament
    ) -> None:
        # "5-8" is a real MTGTop8 tie-bracket result (not a placeholder) --
        # see docs/project/v2.0.0-bump/t2-scraped-tournament-schema/index.md
        # and apps/barrins_scripture/tests/test_parsers.py::
        # TestMtgtop8TieBracketResults for the bug this schema was designed
        # against (Deck.result used to be int-only and silently truncated
        # ranges like this to their leading digit).
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Merliche",
            result="5-8",
            anchor_uri=f"{tournament.url}&d=866130",
        )
        db_session.add(deck)
        await db_session.commit()
        await db_session.refresh(deck)

        fetched = await db_session.get(BSDeck, deck.id)
        assert fetched is not None
        assert fetched.result == "5-8"

    async def test_nullable_result(self, db_session, tournament: BSTournament) -> None:
        # MTGO leagues don't rank decks -- result is NULL, not a placeholder.
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="wooop_orc",
            anchor_uri=f"{tournament.url}#deck_wooop_orc",
        )
        db_session.add(deck)
        await db_session.commit()
        await db_session.refresh(deck)
        assert deck.result is None

    async def test_duplicate_anchor_uri_in_same_tournament_rejected(
        self, db_session, tournament: BSTournament
    ) -> None:
        anchor = f"{tournament.url}&d=866125"
        first = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=anchor,
        )
        db_session.add(first)
        await db_session.commit()

        dupe = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=anchor,
        )
        db_session.add(dupe)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_cascade_delete_from_tournament(
        self, db_session, tournament: BSTournament
    ) -> None:
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=f"{tournament.url}&d=866125",
        )
        db_session.add(deck)
        await db_session.commit()
        deck_id = deck.id

        await db_session.delete(tournament)
        await db_session.commit()

        # Not db_session.get(): the session has expire_on_commit=False, so a
        # cached identity-map hit would mask a cascade that didn't happen.
        # select() always round-trips.
        row = (
            await db_session.execute(select(BSDeck).where(BSDeck.id == deck_id))
        ).scalar_one_or_none()
        assert row is None


class TestBSDeckCard:
    async def test_round_trip_and_unique_entry(
        self, db_session, tournament: BSTournament
    ) -> None:
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=f"{tournament.url}&d=866125",
        )
        db_session.add(deck)
        await db_session.commit()

        card = BSDeckCard(
            deck_id=deck.id,
            board=BSDeckBoard.mainboard,
            card_name="Sol Ring",
            count=1,
        )
        db_session.add(card)
        await db_session.commit()
        await db_session.refresh(card)
        assert card.board == BSDeckBoard.mainboard

        rows = (
            (
                await db_session.execute(
                    select(BSDeckCard).where(BSDeckCard.deck_id == deck.id)
                )
            )
            .scalars()
            .all()
        )
        assert [r.card_name for r in rows] == ["Sol Ring"]

    async def test_same_card_name_allowed_across_boards(
        self, db_session, tournament: BSTournament
    ) -> None:
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=f"{tournament.url}&d=866125",
        )
        db_session.add(deck)
        await db_session.commit()

        db_session.add_all(
            [
                BSDeckCard(
                    deck_id=deck.id,
                    board=BSDeckBoard.mainboard,
                    card_name="Negate",
                    count=1,
                ),
                BSDeckCard(
                    deck_id=deck.id,
                    board=BSDeckBoard.sideboard,
                    card_name="Negate",
                    count=1,
                ),
            ]
        )
        # Same card_name, different board -- (deck_id, board, card_name) is
        # the unique key, not (deck_id, card_name), so this must succeed.
        await db_session.commit()

    async def test_cascade_delete_from_deck(
        self, db_session, tournament: BSTournament
    ) -> None:
        deck = BSDeck(
            tournament_id=tournament.id,
            date=tournament.date,
            player="Xakuyer",
            result="1",
            anchor_uri=f"{tournament.url}&d=866125",
        )
        db_session.add(deck)
        await db_session.commit()

        card = BSDeckCard(
            deck_id=deck.id, board=BSDeckBoard.mainboard, card_name="Sol Ring", count=1
        )
        db_session.add(card)
        await db_session.commit()
        card_id = card.id

        await db_session.delete(deck)
        await db_session.commit()

        row = (
            await db_session.execute(select(BSDeckCard).where(BSDeckCard.id == card_id))
        ).scalar_one_or_none()
        assert row is None


class TestBSRoundAndMatch:
    async def test_round_trip(self, db_session, tournament: BSTournament) -> None:
        round_ = BSRound(tournament_id=tournament.id, round_name="Quarterfinals")
        db_session.add(round_)
        await db_session.commit()

        match = BSRoundMatch(
            round_id=round_.id,
            player_1="ashame",
            player_2="Thronhart",
            result="2-1",
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)
        assert match.result == "2-1"

    async def test_duplicate_pairing_in_same_round_rejected(
        self, db_session, tournament: BSTournament
    ) -> None:
        round_ = BSRound(tournament_id=tournament.id, round_name="Quarterfinals")
        db_session.add(round_)
        await db_session.commit()

        db_session.add(
            BSRoundMatch(
                round_id=round_.id,
                player_1="ashame",
                player_2="Thronhart",
                result="2-1",
            )
        )
        await db_session.commit()

        db_session.add(
            BSRoundMatch(
                round_id=round_.id,
                player_1="ashame",
                player_2="Thronhart",
                result="2-0",
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestBSStanding:
    async def test_round_trip(self, db_session, tournament: BSTournament) -> None:
        standing = BSStanding(
            tournament_id=tournament.id,
            rank=1,
            player="Lightspirit",
            points=18,
            wins=6,
            losses=1,
            draws=0,
            omwp=0.00615,
            gwp=0.007647,
            ogwp=0.005778999999999999,
        )
        db_session.add(standing)
        await db_session.commit()
        await db_session.refresh(standing)

        fetched = await db_session.get(BSStanding, standing.id)
        assert fetched is not None
        assert fetched.rank == 1
        assert fetched.omwp == pytest.approx(0.00615)

    async def test_duplicate_player_in_same_tournament_rejected(
        self, db_session, tournament: BSTournament
    ) -> None:
        db_session.add(
            BSStanding(
                tournament_id=tournament.id,
                rank=1,
                player="Lightspirit",
                points=18,
                wins=6,
                losses=1,
                draws=0,
                omwp=0.006,
                gwp=0.007,
                ogwp=0.005,
            )
        )
        await db_session.commit()

        db_session.add(
            BSStanding(
                tournament_id=tournament.id,
                rank=2,
                player="Lightspirit",
                points=15,
                wins=5,
                losses=2,
                draws=0,
                omwp=0.006,
                gwp=0.007,
                ogwp=0.005,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
