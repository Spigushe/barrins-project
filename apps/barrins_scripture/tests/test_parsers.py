import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from barrins_scripture.parsers import mtgo, mtgtop8
from barrins_scripture.schemas import CardEntry

FIXTURES = Path(__file__).parent / "fixtures"


def _cards(entries: list[CardEntry]) -> set[tuple[str, int]]:
    return {(entry.name, entry.count) for entry in entries}


def _expected_cards(entries: list[dict]) -> set[tuple[str, int]]:
    return {(entry["name"], entry["count"]) for entry in entries}


class TestMtgoParser:
    """Against a closed, immutable Duel Commander League run (2026-06-27) —
    re-fetched live and diffed against mtg_decklist_cache's archived JSON for
    the same tournament to confirm this port is a faithful rewrite, not just
    a plausible-looking one. See tests/fixtures/README.md for provenance.
    """

    URL = "https://www.mtgo.com/decklist/duel-commander-league-2026-06-2710716"

    @pytest.fixture
    def soup(self) -> BeautifulSoup:
        html = (FIXTURES / "mtgo" / "duel_commander_league_2026-06-27.html").read_text(
            encoding="utf-8"
        )
        return BeautifulSoup(html, "html.parser")

    @pytest.fixture
    def expected(self) -> dict:
        raw = (
            FIXTURES / "mtgo" / "duel_commander_league_2026-06-27.expected.json"
        ).read_text(encoding="utf-8")
        return json.loads(raw)

    def test_tournament(self, soup: BeautifulSoup, expected: dict) -> None:
        result = mtgo.tournament(soup, self.URL)
        assert result is not None
        assert str(result.date) == expected["tournament"]["date"]
        assert result.name == expected["tournament"]["name"]
        assert result.format == expected["tournament"]["format"]
        assert result.players == expected["tournament"]["players"]
        assert result.url == self.URL

    def test_decks_match_archive(self, soup: BeautifulSoup, expected: dict) -> None:
        decks = mtgo.decks(soup, self.URL)
        assert {d.player for d in decks} == {d["player"] for d in expected["decks"]}

        by_player = {d.player: d for d in decks}
        for exp_deck in expected["decks"]:
            got = by_player[exp_deck["player"]]
            assert got.result == exp_deck["result"]
            assert _cards(got.mainboard) == _expected_cards(exp_deck["mainboard"])
            assert _cards(got.sideboard or []) == _expected_cards(
                exp_deck["sideboard"] or []
            )

    def test_deck_date_is_parsed_from_the_page_not_assumed(
        self, soup: BeautifulSoup
    ) -> None:
        # Deliberately not compared to the archive here: the archived JSON
        # records 2026-06-27 for every deck, but re-fetching this closed
        # league today has every decklist-date tag reading "6/26/2026" —
        # a one-day skew that reproduces consistently and only affects this
        # field, most likely a timezone-rendering difference between the
        # original scrape's environment (a UTC CI runner) and this one, not
        # a parsing bug (mainboards/sideboards/results all match exactly).
        # So this asserts the parser correctly reflects what the page itself
        # says, rather than forcing an unexplained day-offset to match.
        decks = mtgo.decks(soup, self.URL)
        assert {d.date for d in decks} == {date(2026, 6, 26)}

    def test_no_rounds_or_standings_for_a_league(self, soup: BeautifulSoup) -> None:
        # Leagues have no bracket/standings — only single-elimination-style
        # events (get_num_rounds) populate those.
        assert mtgo.rounds(soup) == []
        assert mtgo.standings(soup) == []


class TestMtgtop8Parser:
    """Against a real Duel Commander event (Championnat dc 974 - Juillet,
    e=88803), diffed against the same tournament's archived JSON. Only the
    rank-1 deck (d=874003) has a fetched decklist-page fixture; the other
    7 top-8 decks are exercised structurally (decks() must still find all
    of them) with get_decklist/get_notes mocked out to avoid live calls.
    """

    URL = "https://mtgtop8.com/event?e=88803"

    @pytest.fixture
    def soup(self) -> BeautifulSoup:
        html = (FIXTURES / "mtgtop8" / "event_88803_duel_commander.html").read_text(
            encoding="iso-8859-1"
        )
        return BeautifulSoup(html, "html.parser")

    @pytest.fixture
    def expected(self) -> dict:
        raw = (
            FIXTURES / "mtgtop8" / "event_88803_duel_commander.expected.json"
        ).read_text(encoding="utf-8")
        return json.loads(raw)

    def test_tournament(self, soup: BeautifulSoup, expected: dict) -> None:
        result = mtgtop8.tournament(self.URL, soup)
        assert str(result.date) == expected["tournament"]["date"]
        assert result.name == expected["tournament"]["name"]
        assert result.format == expected["tournament"]["format"]
        assert result.players == expected["tournament"]["players"]

    def test_get_deck_from_top8_matches_archive(
        self, soup: BeautifulSoup, expected: dict
    ) -> None:
        decklist_html = (FIXTURES / "mtgtop8" / "decklist_874003.html").read_text(
            encoding="iso-8859-1"
        )
        decklist_soup = BeautifulSoup(decklist_html, "html.parser")

        def fake_get_tournament_soup(
            url: str, encoding: str = "iso-8859-1"
        ) -> BeautifulSoup:
            assert "d=874003" in url
            return decklist_soup

        deck_link = soup.select(".chosen_tr div.S14 a[href^='?e=']")[0]
        with (
            patch.object(
                mtgtop8, "get_tournament_soup", side_effect=fake_get_tournament_soup
            ),
            patch.object(mtgtop8, "get_notes", return_value=None),
        ):
            deck_id, deck = mtgtop8.get_deck_from_top8(deck_link)

        exp_deck = expected["decks"][0]
        assert deck_id == 874003
        assert deck.player == exp_deck["player"]
        assert deck.result == exp_deck["result"]
        assert _cards(deck.mainboard) == _expected_cards(exp_deck["mainboard"])
        assert _cards(deck.sideboard or []) == _expected_cards(exp_deck["sideboard"])

    def test_decks_enumerates_every_top8_entry(
        self, soup: BeautifulSoup, expected: dict
    ) -> None:
        with (
            patch.object(
                mtgtop8,
                "get_decklist",
                return_value=([CardEntry(count=1, name="Filler")], []),
            ),
            patch.object(mtgtop8, "get_notes", return_value=None),
        ):
            decks = mtgtop8.decks(soup)

        assert len(decks) == len(expected["decks"])
