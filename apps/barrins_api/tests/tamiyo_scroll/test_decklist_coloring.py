"""Unit tests for app/services/tamiyo_scroll/decklist_coloring.py."""

import uuid

from app.models.tamiyo_scroll import TSCardTest
from app.services.tamiyo_scroll.decklist_coloring import (
    _line_status,
    color_decklist,
    commander_section_indices,
    parse_card_line,
)


def _card_test(card_name: str, rating: int) -> TSCardTest:
    return TSCardTest(
        owner_id=uuid.uuid4(), tester="Alice", card_name=card_name, rating=rating
    )


class TestLineStatus:
    def test_no_ratings_returns_in_test(self):
        assert _line_status([]) == "in_test"

    def test_majority_high_returns_validated(self):
        assert _line_status([4, 5, 4]) == "validated"

    def test_majority_low_returns_rejected(self):
        assert _line_status([1, 2, 2]) == "rejected"

    def test_no_majority_returns_in_test(self):
        assert _line_status([4, 2, 3]) == "in_test"

    def test_tied_high_and_low_returns_in_test(self):
        assert _line_status([5, 1]) == "in_test"


class TestColorDecklist:
    def test_line_without_matching_card_is_neutral(self):
        result = color_decklist("4 Lightning Bolt", [])
        assert result == [{"line": "4 Lightning Bolt", "status": "neutral"}]

    def test_matched_card_validated(self):
        tests = [_card_test("Lightning Bolt", 5), _card_test("Lightning Bolt", 4)]
        result = color_decklist("4 Lightning Bolt", tests)
        assert result == [{"line": "4 Lightning Bolt", "status": "validated"}]

    def test_matched_card_rejected(self):
        tests = [_card_test("Duress", 1), _card_test("Duress", 2)]
        result = color_decklist("2 Duress", tests)
        assert result == [{"line": "2 Duress", "status": "rejected"}]

    def test_matched_card_in_test_without_majority(self):
        tests = [_card_test("Duress", 4), _card_test("Duress", 2)]
        result = color_decklist("2 Duress", tests)
        assert result == [{"line": "2 Duress", "status": "in_test"}]

    def test_case_insensitive_matching(self):
        tests = [_card_test("lightning bolt", 5)]
        result = color_decklist("4 LIGHTNING BOLT", tests)
        assert result == [{"line": "4 LIGHTNING BOLT", "status": "validated"}]

    def test_longest_matching_card_name_wins(self):
        # "Duress" is a substring of "Extended Duress" — the line must
        # attach to the longest matching name, not the shortest.
        tests = [_card_test("Duress", 1), _card_test("Extended Duress", 5)]
        result = color_decklist("1 Extended Duress", tests)
        assert result == [{"line": "1 Extended Duress", "status": "validated"}]

    def test_multiple_lines_processed_independently(self):
        tests = [_card_test("Bolt", 5), _card_test("Doom Blade", 1)]
        content = "4 Bolt\n2 Doom Blade\n1 Unrelated Card"
        result = color_decklist(content, tests)
        assert result == [
            {"line": "4 Bolt", "status": "validated"},
            {"line": "2 Doom Blade", "status": "rejected"},
            {"line": "1 Unrelated Card", "status": "neutral"},
        ]

    def test_empty_content_returns_empty_list(self):
        assert color_decklist("", []) == []


class TestParseCardLine:
    def test_matches_qty_and_name(self):
        assert parse_card_line("4 Lightning Bolt") == (4, "Lightning Bolt")

    def test_matches_x_suffix_on_quantity(self):
        assert parse_card_line("4x Lightning Bolt") == (4, "Lightning Bolt")

    def test_strips_surrounding_whitespace(self):
        assert parse_card_line("  4 Lightning Bolt  ") == (4, "Lightning Bolt")

    def test_blank_line_returns_none(self):
        assert parse_card_line("   ") is None

    def test_line_without_leading_quantity_returns_none(self):
        assert parse_card_line("Commander") is None
        assert parse_card_line("some free-text note") is None


class TestCommanderSectionIndices:
    def test_no_header_returns_empty_set(self):
        lines = ["4 Lightning Bolt", "2 Duress"]
        assert commander_section_indices(lines) == set()

    def test_header_marks_following_lines_until_blank(self):
        lines = ["Commander", "1 Atraxa, Praetors' Voice", "", "1 Sol Ring"]
        assert commander_section_indices(lines) == {1}

    def test_header_is_case_insensitive(self):
        lines = ["commander", "1 Atraxa, Praetors' Voice"]
        assert commander_section_indices(lines) == {1}

    def test_header_runs_to_end_of_content_without_trailing_blank(self):
        lines = ["Commander", "1 Atraxa, Praetors' Voice", "1 Sol Ring"]
        assert commander_section_indices(lines) == {1, 2}
