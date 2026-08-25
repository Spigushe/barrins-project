"""Unit tests for app/services/tamiyo_scroll/decklist_diff.py."""

from app.services.tamiyo_scroll.decklist_diff import (
    diff_decklist_cards,
    diff_decklist_unparsed_lines,
)


class TestDiffDecklistCards:
    def test_identical_content_is_all_unchanged(self):
        content = "4 Lightning Bolt\n2 Duress"
        result = diff_decklist_cards(content, content)
        assert {(d.name, d.status, d.old_qty, d.new_qty) for d in result} == {
            ("Lightning Bolt", "unchanged", 4, 4),
            ("Duress", "unchanged", 2, 2),
        }

    def test_new_card_is_added(self):
        result = diff_decklist_cards("4 Lightning Bolt", "4 Lightning Bolt\n2 Duress")
        added = next(d for d in result if d.name == "Duress")
        assert (added.status, added.old_qty, added.new_qty) == ("added", None, 2)

    def test_dropped_card_is_removed(self):
        result = diff_decklist_cards("4 Lightning Bolt\n2 Duress", "4 Lightning Bolt")
        removed = next(d for d in result if d.name == "Duress")
        assert (removed.status, removed.old_qty, removed.new_qty) == (
            "removed",
            2,
            None,
        )

    def test_quantity_change_is_quantity_changed(self):
        result = diff_decklist_cards("2 Duress", "4 Duress")
        changed = next(d for d in result if d.name == "Duress")
        assert (changed.status, changed.old_qty, changed.new_qty) == (
            "quantity_changed",
            2,
            4,
        )

    def test_reordering_is_not_added_or_removed(self):
        """Card-aware matching (vs. line-level) is the point of this
        diff: the same two cards in a different order must both come
        back unchanged, not as a removed+added pair."""
        result = diff_decklist_cards(
            "4 Lightning Bolt\n2 Duress", "2 Duress\n4 Lightning Bolt"
        )
        assert {d.status for d in result} == {"unchanged"}

    def test_commander_flag_from_new_version(self):
        old = "4 Lightning Bolt"
        new = "Commander\n1 Atraxa, Praetors' Voice\n\n4 Lightning Bolt"
        result = diff_decklist_cards(old, new)
        atraxa = next(d for d in result if d.name == "Atraxa, Praetors' Voice")
        assert atraxa.is_commander is True
        bolt = next(d for d in result if d.name == "Lightning Bolt")
        assert bolt.is_commander is False

    def test_removed_commander_keeps_is_commander_from_old_version(self):
        old = "Commander\n1 Atraxa, Praetors' Voice\n\n4 Lightning Bolt"
        new = "4 Lightning Bolt"
        result = diff_decklist_cards(old, new)
        atraxa = next(d for d in result if d.name == "Atraxa, Praetors' Voice")
        assert (atraxa.status, atraxa.is_commander) == ("removed", True)

    def test_sorted_commander_first_then_alphabetical(self):
        old = ""
        new = "Commander\n1 Zeta Commander\n\n2 Alpha Card\n1 Beta Card"
        result = diff_decklist_cards(old, new)
        assert [d.name for d in result] == ["Zeta Commander", "Alpha Card", "Beta Card"]

    def test_multiple_lines_for_same_card_are_summed(self):
        result = diff_decklist_cards("1 Forest", "1 Forest\n1 Forest")
        forest = next(d for d in result if d.name == "Forest")
        assert (forest.status, forest.old_qty, forest.new_qty) == (
            "quantity_changed",
            1,
            2,
        )

    def test_empty_versions_produce_no_diffs(self):
        assert diff_decklist_cards("", "") == []


class TestDiffDecklistUnparsedLines:
    def test_identical_unparsed_lines_are_unchanged(self):
        note = "some free-text note"
        result = diff_decklist_unparsed_lines(note, note)
        assert [(line.line, line.status) for line in result] == [(note, "unchanged")]

    def test_added_and_removed_lines(self):
        result = diff_decklist_unparsed_lines("old note", "new note")
        statuses = {(line.line, line.status) for line in result}
        assert statuses == {("old note", "removed"), ("new note", "added")}

    def test_card_lines_are_excluded(self):
        old_content = "4 Lightning Bolt\nnote here"
        result = diff_decklist_unparsed_lines(old_content, "note here")
        assert [line.line for line in result] == ["note here"]

    def test_blank_and_commander_header_lines_are_excluded(self):
        result = diff_decklist_unparsed_lines("Commander\n\nsome note", "some note")
        assert [line.line for line in result] == ["some note"]

    def test_empty_versions_produce_no_diffs(self):
        assert diff_decklist_unparsed_lines("", "") == []
