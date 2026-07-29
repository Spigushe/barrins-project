from datetime import date, datetime

import pytest

from barrins_scripture.utils.date_parsing import get_month_range, parse_date
from barrins_scripture.utils.swiss_tournament import get_num_rounds


class TestParseDate:
    def test_parses_slash_format(self) -> None:
        assert parse_date("06/27/2026") == date(2026, 6, 27)

    def test_parses_month_name_format(self) -> None:
        assert parse_date("June 27, 2026") == date(2026, 6, 27)

    def test_passes_through_a_date(self) -> None:
        assert parse_date(date(2026, 6, 27)) == date(2026, 6, 27)

    def test_passes_through_a_datetime(self) -> None:
        assert parse_date(datetime(2026, 6, 27, 10, 30)) == date(2026, 6, 27)

    def test_unparseable_string_falls_back_to_mtg_release_date(self) -> None:
        assert parse_date("not a date") == date(1993, 8, 5)

    def test_custom_formats(self) -> None:
        assert parse_date("2026-06-27", formats=["%Y-%m-%d"]) == date(2026, 6, 27)


class TestGetMonthRange:
    def test_within_a_single_year(self) -> None:
        assert get_month_range(date(2026, 3, 1), date(2026, 6, 1)) == [
            (2026, 3),
            (2026, 4),
            (2026, 5),
            (2026, 6),
        ]

    def test_across_a_year_boundary(self) -> None:
        assert get_month_range(date(2025, 11, 1), date(2026, 2, 1)) == [
            (2025, 11),
            (2025, 12),
            (2026, 1),
            (2026, 2),
        ]

    def test_single_month(self) -> None:
        assert get_month_range(date(2026, 6, 1), date(2026, 6, 30)) == [(2026, 6)]


class TestGetNumRounds:
    @pytest.mark.parametrize(
        ("players", "expected_rounds"),
        [
            (8, 0),
            (16, 5),
            (32, 5),
            (64, 6),
            (128, 7),
            (226, 8),
            (409, 9),
            (410, 10),
        ],
    )
    def test_bracket_sizes(self, players: int, expected_rounds: int) -> None:
        assert get_num_rounds(players) == expected_rounds
