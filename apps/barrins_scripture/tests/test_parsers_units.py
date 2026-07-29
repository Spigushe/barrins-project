"""Unit tests for parser branches the two golden fixtures don't exercise
(bracket rounds/standings, the mtgtop8 "out of top8" radio-selector path,
error branches). These use small hand-built HTML snippets rather than real
fixtures — the golden-fixture tests in test_parsers.py are what proves this
port matches production; these fill in the remaining code paths.
"""

from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from barrins_scripture.parsers import mtgo, mtgtop8


class TestMtgoBracketAndStandings:
    def test_tournament_returns_none_without_a_date(self) -> None:
        soup = BeautifulSoup(
            "<html><h1 class='decklist-title'>No Date Here</h1></html>", "html.parser"
        )
        assert mtgo.tournament(soup, "https://example.test") is None

    def test_rounds_and_matches(self) -> None:
        html = """
        <div class="decklist-bracket-round">
          <div class="decklist-bracket-round-title">Quarterfinals</div>
          <div class="decklist-bracket-match-wrapper">
            <div class="decklist-bracket-player">Alice  2-1</div>
            <div class="decklist-bracket-player">Bob</div>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        rounds = mtgo.rounds(soup)
        assert len(rounds) == 1
        assert rounds[0].round_name == "Quarterfinals"
        assert rounds[0].matches == [
            mtgo.Match(player_1="Alice", player_2="Bob", result="2-1")
        ]

    def test_match_falls_back_when_not_exactly_two_players(self) -> None:
        html = '<div class="decklist-bracket-match-wrapper"></div>'
        wrapper = BeautifulSoup(html, "html.parser").select_one(
            ".decklist-bracket-match-wrapper"
        )
        assert wrapper is not None
        match = mtgo.get_match(wrapper)
        assert match.player_1 == "Unknown Player"
        assert match.result == "0-0-0"

    def test_standings_table(self) -> None:
        html = """
        <div id="decklistStandings">
          <table class="hidden-xs">
            <tbody>
              <tr><td>1</td><td>Alice</td><td>9</td><td>66.00%</td><td>70.00%</td><td>55.00%</td></tr>
              <tr></tr>
            </tbody>
          </table>
        </div>
        <h2 class="decklist-player-count">16 Players</h2>
        """
        soup = BeautifulSoup(html, "html.parser")
        standings = mtgo.standings(soup)
        assert len(standings) == 1
        standing = standings[0]
        assert standing.rank == 1
        assert standing.player == "Alice"
        assert standing.points == 9
        assert standing.wins == 3
        assert standing.omwp == pytest.approx(0.66)

    def test_standings_empty_without_a_table(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert mtgo.standings(soup) == []

    def test_get_standing_raises_on_malformed_row(self) -> None:
        html = "<tr><td>1</td></tr>"
        row = BeautifulSoup(html, "html.parser").select_one("tr")
        assert row is not None
        with pytest.raises(ValueError, match="Invalid standing row"):
            mtgo.get_standing(row, nb_rounds=5)

    def test_get_deck_position_parses_place_suffix(self) -> None:
        html = """
        <section class="decklist" id="deck_alice">
          <p class="decklist-player">Alice (1st Place)</p>
          <p class="decklist-date">06/27/2026</p>
        </section>
        """
        deck_section = BeautifulSoup(html, "html.parser").select_one("section.decklist")
        assert deck_section is not None
        deck = mtgo.get_deck(deck_section, "https://example.test")
        assert deck.player == "Alice"
        assert deck.result == 1


class TestMtgtop8Fallbacks:
    def test_get_tournament_soup_fetches_and_parses(self) -> None:
        response = Mock()
        response.content = b"<html><body>hi</body></html>"
        with patch.object(mtgtop8.requests, "get", return_value=response) as mock_get:
            soup = mtgtop8.get_tournament_soup("https://mtgtop8.com/event?e=1")
        mock_get.assert_called_once()
        assert soup.body is not None
        assert response.encoding == "iso-8859-1"

    def test_get_date_falls_back_without_a_date(self) -> None:
        soup = BeautifulSoup("<div class='meta_arch'></div>", "html.parser")
        assert mtgtop8.get_date(soup) == mtgtop8._MTG_FIRST_RELEASE

    def test_get_name_without_event_title(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert mtgtop8.get_name(soup) == ""

    def test_get_format_without_meta_arch(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert mtgtop8.get_format(soup) == "Unknown Format"

    def test_get_players_qty_without_meta_arch(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert mtgtop8.get_players_qty(soup) == 0

    def test_get_players_qty_without_a_players_line(self) -> None:
        html = "<div class='meta_arch'>Legacy</div><div>no count here</div>"
        soup = BeautifulSoup(html, "html.parser")
        assert mtgtop8.get_players_qty(soup) == 0

    def test_get_deck_from_top8_without_a_player_tag(self) -> None:
        html = """
        <div class="hover_tr">
          <div class="S14"><a href="?e=1&d=42">Deck Name</a></div>
        </div>
        """
        tag = BeautifulSoup(html, "html.parser").select_one("a")
        assert tag is not None
        with (
            patch.object(
                mtgtop8,
                "get_decklist",
                return_value=([mtgtop8.CardEntry(count=1, name="X")], []),
            ),
            patch.object(mtgtop8, "get_notes", return_value=None),
        ):
            _, deck = mtgtop8.get_deck_from_top8(tag)
        assert deck.player == "Unknown Player"

    def test_find_row_container_raises_when_none_found(self) -> None:
        html = "<span><a href='?e=1&d=1'>x</a></span>"
        tag = BeautifulSoup(html, "html.parser").select_one("a")
        assert tag is not None
        with pytest.raises(ValueError, match="Container block"):
            mtgtop8._find_row_container(tag)

    def test_get_deck_out_top8_raises_without_a_parent(self) -> None:
        tag = BeautifulSoup(
            "<input type='radio' value='1'/>", "html.parser"
        ).select_one("input")
        assert tag is not None
        tag.extract()  # detach so .parent is None
        with pytest.raises(ValueError, match="Parent block not found"):
            mtgtop8.get_deck_out_top8(tag)

    def test_get_decklist_without_a_sideboard(self) -> None:
        response = Mock()
        response.content = "4 Lightning Bolt\n1 Forest".encode("iso-8859-1")
        with patch.object(mtgtop8.requests, "get", return_value=response):
            mainboard, sideboard = mtgtop8.get_decklist(1)
        assert len(mainboard) == 2
        assert sideboard == []


class TestMtgtop8OutOfTop8AndErrors:
    def test_tournament_raises_on_unknown_format(self) -> None:
        soup = BeautifulSoup(
            "<div class='meta_arch'>Some Unknown Game</div>", "html.parser"
        )
        with pytest.raises(ValueError, match="Unknown format"):
            mtgtop8.tournament("https://example.test", soup)

    def test_get_deck_from_top8_raises_without_deck_id(self) -> None:
        tag = BeautifulSoup('<a href="nope">x</a>', "html.parser").select_one("a")
        assert tag is not None
        with pytest.raises(ValueError, match="Deck ID not found"):
            mtgtop8.get_deck_from_top8(tag)

    def test_get_deck_from_top8_raises_when_mainboard_missing(self) -> None:
        html = """
        <div class="hover_tr">
          <div class="S14"><a href="?e=1&d=42">Deck Name</a></div>
        </div>
        """
        tag = BeautifulSoup(html, "html.parser").select_one("a")
        assert tag is not None
        with (
            patch.object(mtgtop8, "get_decklist", return_value=([], [])),
            patch.object(mtgtop8, "get_notes", return_value=None),
        ):
            with pytest.raises(ValueError, match="Mainboard not found"):
                mtgtop8.get_deck_from_top8(tag)

    def test_get_deck_out_top8_reads_contents_of_a_void_element(self) -> None:
        # get_deck_out_top8 (the "beyond top 8" path, for large events that
        # list every deck via a <input type=radio> selector instead of
        # individual links) reads deck_tag.contents[0] — but <input> is a
        # void HTML element, so BeautifulSoup's html.parser (the same
        # backend get_tournament_soup uses) always gives it contents == [].
        # This is inherited unchanged from mtg_scraper's original code and
        # is NOT exercised by either golden fixture (the one Duel Commander
        # event tested uses the top8_tags/href path exclusively) — it may
        # be relying on real mtgtop8.com markup this synthetic snippet
        # doesn't reproduce. Documenting the failure rather than hiding it:
        # this path needs a real "large event" fixture before it can be
        # trusted, which is a gap to close before T1 ships, not here.
        html = '<label label="Deck #3"><input type="radio" value="99"/></label>'
        radio = BeautifulSoup(html, "html.parser").select_one("input")
        assert radio is not None
        with pytest.raises(IndexError):
            mtgtop8.get_deck_out_top8(radio)

    def test_sanitize_cardname_strips_alchemy_prefix_and_entities(self) -> None:
        assert mtgtop8.sanitize_cardname("A-Wandering Emperor") == "Wandering Emperor"
        assert mtgtop8.sanitize_cardname("Fire &amp; Ice") == "Fire & Ice"

    def test_handle_line_and_cardentries(self) -> None:
        assert mtgtop8.handle_line("4 Lightning Bolt") == mtgtop8.CardEntry(
            count=4, name="Lightning Bolt"
        )
        # Blank lines (no space at all once stripped) are the only lines
        # get_cardentries filters out — real decklist dumps never contain
        # a line with a space that isn't "<qty> <name>", so that weak
        # filter is sufficient in practice.
        entries = mtgtop8.get_cardentries("4 Lightning Bolt\n1 Forest\n\n")
        assert len(entries) == 2

    def test_get_notes_extracts_text_and_strips_disclaimer(self) -> None:
        response = Mock()
        response.raise_for_status = Mock()
        response.text = (
            '<div class="S16">Some analysis '
            '<span><a href="x">Lightning Bolt</a></span> text.'
            + mtgtop8._AI_DISCLAIMER
            + "</div>"
        )
        with patch.object(mtgtop8.requests, "get", return_value=response):
            notes = mtgtop8.get_notes(123)
        assert notes == "Some analysis Lightning Bolt text."

    def test_get_notes_returns_none_without_the_notes_div(self) -> None:
        response = Mock()
        response.raise_for_status = Mock()
        response.text = "<div>no notes here</div>"
        with patch.object(mtgtop8.requests, "get", return_value=response):
            assert mtgtop8.get_notes(123) is None
