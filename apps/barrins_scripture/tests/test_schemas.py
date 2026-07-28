from datetime import date

import pytest
from pydantic import ValidationError

from barrins_scripture.schemas import (
    FORMATS,
    CardEntry,
    Deck,
    Formats,
    Match,
    MTGScrape,
    Round,
    Standing,
    Tournament,
)


class TestCardEntry:
    def test_construction(self) -> None:
        entry = CardEntry(count=4, name="Lightning Bolt")
        assert entry.count == 4
        assert entry.name == "Lightning Bolt"

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            CardEntry(count=4)  # type: ignore[call-arg]


class TestDeck:
    def test_construction_with_defaults(self) -> None:
        deck = Deck(
            date=date(2026, 3, 23),
            player="Spigushe",
            anchor_uri="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            mainboard=[CardEntry(count=4, name="Lightning Bolt")],
        )
        assert deck.result is None
        assert deck.sideboard is None
        assert deck.notes is None

    def test_construction_with_all_fields(self) -> None:
        deck = Deck(
            date=date(2026, 3, 23),
            player="Spigushe",
            result=1,
            anchor_uri="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            mainboard=[CardEntry(count=4, name="Lightning Bolt")],
            sideboard=[CardEntry(count=2, name="Pyroblast")],
            notes="Top 8",
        )
        assert deck.result == 1
        assert deck.sideboard == [CardEntry(count=2, name="Pyroblast")]
        assert deck.notes == "Top 8"

    def test_date_parsed_from_iso_string(self) -> None:
        deck = Deck(
            date="2026-03-23",  # type: ignore[arg-type]
            player="Spigushe",
            anchor_uri="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            mainboard=[],
        )
        assert deck.date == date(2026, 3, 23)

    def test_missing_mainboard_raises(self) -> None:
        with pytest.raises(ValidationError):
            Deck(
                date=date(2026, 3, 23),
                player="Spigushe",
                anchor_uri="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            )  # type: ignore[call-arg]


class TestFormats:
    def test_all_expected_formats_present(self) -> None:
        expected = {
            "Standard",
            "Pioneer",
            "Modern",
            "Legacy",
            "Vintage",
            "Duel Commander",
            "Pauper",
            "Premodern",
        }
        assert {f.value for f in Formats} == expected

    def test_formats_list_matches_enum_values(self) -> None:
        assert FORMATS == [f.value for f in Formats]

    def test_specific_members(self) -> None:
        assert Formats.MODERN.value == "Modern"
        assert Formats.DUEL_COMMANDER.value == "Duel Commander"


class TestMatchAndRound:
    def test_match_construction(self) -> None:
        match = Match(player_1="Spigushe", player_2="Opponent", result="2-1")
        assert match.result == "2-1"

    def test_round_defaults_to_empty_matches(self) -> None:
        round_ = Round(round_name="Round 1")
        assert round_.matches == []

    def test_round_with_matches(self) -> None:
        match = Match(player_1="Spigushe", player_2="Opponent", result="2-1")
        round_ = Round(round_name="Round 1", matches=[match])
        assert round_.matches == [match]


class TestStanding:
    def test_construction(self) -> None:
        standing = Standing(
            rank=1,
            player="Spigushe",
            points=9,
            wins=3,
            losses=0,
            draws=0,
            omwp=0.66,
            gwp=0.70,
            ogwp=0.55,
        )
        assert standing.rank == 1
        assert standing.omwp == pytest.approx(0.66)

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Standing(
                rank=1,
                player="Spigushe",
                points=9,
                wins=3,
                losses=0,
                draws=0,
                omwp=0.66,
                gwp=0.70,
            )  # type: ignore[call-arg]


class TestTournament:
    def test_construction(self) -> None:
        tournament = Tournament(
            date=date(2026, 3, 23),
            name="Legacy League 2026-03-23",
            url="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            format="Legacy",
            players=32,
        )
        assert tournament.players == 32
        assert tournament.format == "Legacy"


class TestMTGScrape:
    def test_construction_with_defaults(self) -> None:
        tournament = Tournament(
            date=date(2026, 3, 23),
            name="Legacy League 2026-03-23",
            url="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            format="Legacy",
            players=32,
        )
        scrape = MTGScrape(tournament=tournament)
        assert scrape.decks == []
        assert scrape.rounds == []
        assert scrape.standings == []

    def test_construction_with_nested_data(self) -> None:
        tournament = Tournament(
            date=date(2026, 3, 23),
            name="Legacy League 2026-03-23",
            url="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            format="Legacy",
            players=32,
        )
        deck = Deck(
            date=date(2026, 3, 23),
            player="Spigushe",
            anchor_uri="https://mtgo.com/decklist/legacy-league-2026-03-2310381",
            mainboard=[CardEntry(count=4, name="Lightning Bolt")],
        )
        standing = Standing(
            rank=1,
            player="Spigushe",
            points=9,
            wins=3,
            losses=0,
            draws=0,
            omwp=0.66,
            gwp=0.70,
            ogwp=0.55,
        )
        round_ = Round(round_name="Round 1")

        scrape = MTGScrape(
            tournament=tournament,
            decks=[deck],
            rounds=[round_],
            standings=[standing],
        )
        assert scrape.decks == [deck]
        assert scrape.rounds == [round_]
        assert scrape.standings == [standing]

    def test_missing_tournament_raises(self) -> None:
        with pytest.raises(ValidationError):
            MTGScrape()  # type: ignore[call-arg]
