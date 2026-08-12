"""Tests for the banlist-period boundary math -- the highest-risk part of
Karn Tablets' windowing (T6's own doc flags it explicitly: year rollover,
month-length edge cases). Expected values cross-checked against a real
Python date computation, not hand-derived.
"""

from datetime import date, timedelta

import pytest

from karn_tablets.windowing import (
    Window,
    WindowKind,
    banlist_period_containing,
    banlist_period_window,
    last_weekday_of_month,
    resolve_windows,
    rolling_30d_window,
)


class TestLastWeekdayOfMonth:
    @pytest.mark.parametrize(
        ("year", "month", "weekday", "expected"),
        [
            (2026, 1, 1, date(2026, 1, 27)),  # last Tuesday of Jan 2026
            (2026, 3, 1, date(2026, 3, 31)),  # last Tuesday IS the last day
            (2026, 5, 1, date(2026, 5, 26)),
            (2026, 7, 1, date(2026, 7, 28)),
            (2026, 9, 1, date(2026, 9, 29)),
            (2026, 11, 1, date(2026, 11, 24)),
            (2026, 1, 0, date(2026, 1, 26)),  # last Monday of Jan 2026
            (2026, 3, 0, date(2026, 3, 30)),
            (2026, 11, 0, date(2026, 11, 30)),  # last Monday IS the last day
            (2027, 1, 1, date(2027, 1, 26)),
            (2027, 1, 0, date(2027, 1, 25)),
            (2024, 2, 1, date(2024, 2, 27)),  # leap-year February
            (2024, 2, 0, date(2024, 2, 26)),
            (2028, 2, 1, date(2028, 2, 29)),  # leap-year Feb, Tuesday IS last day
        ],
    )
    def test_matches_reference_computation(self, year, month, weekday, expected):
        assert last_weekday_of_month(year, month, weekday) == expected

    def test_december_does_not_crash_on_year_rollover(self):
        # last Monday of December 2026 -- exercises the month == 12 branch
        result = last_weekday_of_month(2026, 12, 0)
        assert result.year == 2026
        assert result.month == 12
        assert result.weekday() == 0

    def test_rejects_invalid_weekday(self):
        with pytest.raises(ValueError, match="weekday must be 0-6"):
            last_weekday_of_month(2026, 1, 7)


class TestBanlistPeriodContaining:
    @pytest.mark.parametrize(
        ("reference", "expected_start", "expected_end"),
        [
            # Squarely inside the March->May period.
            (date(2026, 4, 15), date(2026, 3, 31), date(2026, 5, 25)),
            # Exactly on the end boundary of Jan->Mar -- belongs to that
            # period, not the next one (inclusive end).
            (date(2026, 3, 30), date(2026, 1, 27), date(2026, 3, 30)),
            # Exactly on the start boundary of Mar->May.
            (date(2026, 3, 31), date(2026, 3, 31), date(2026, 5, 25)),
            # Squarely inside Sep->Nov. End is Nov 23, not "last Monday of
            # Nov" (Nov 30) -- Nov 2026's last day is itself a Monday, so
            # the naive "last Monday" reading would fall *after* the next
            # period's start (last Tuesday of Nov = Nov 24), overlapping
            # it. The end is derived from the next period's start instead.
            (date(2026, 10, 1), date(2026, 9, 29), date(2026, 11, 23)),
        ],
    )
    def test_matches_reference_computation(
        self, reference, expected_start, expected_end
    ):
        assert banlist_period_containing(reference) == (expected_start, expected_end)

    def test_transition_month_ending_on_monday_does_not_overlap_the_next_period(self):
        # Nov 2026's last day is a Monday (Nov 30), so "last Monday of
        # Nov" (Nov 30) would fall after "last Tuesday of Nov" (Nov 24,
        # the next period's start) -- a real overlap if computed
        # independently. The Sep->Nov period must end before Nov 24.
        _start, end = banlist_period_containing(date(2026, 10, 1))
        assert end == date(2026, 11, 23)
        next_start, _next_end = banlist_period_containing(date(2026, 11, 24))
        assert next_start == date(2026, 11, 24)
        assert end < next_start

    def test_year_rollover_november_to_january(self):
        # December 15 falls inside the Nov(2026)->Jan(2027) period.
        start, end = banlist_period_containing(date(2026, 12, 15))
        assert start == date(2026, 11, 24)
        assert end == date(2027, 1, 25)

    def test_year_rollover_end_of_period_is_in_following_year(self):
        # The last day of the Nov->Jan period is itself in January.
        start, end = banlist_period_containing(date(2027, 1, 25))
        assert start == date(2026, 11, 24)
        assert end == date(2027, 1, 25)

    def test_day_after_year_rollover_period_starts_a_new_one(self):
        # 2027-01-26 is the last Tuesday of Jan 2027 -- the very next period
        # starts here, immediately after the Nov->Jan one ends.
        start, _end = banlist_period_containing(date(2027, 1, 26))
        assert start == date(2027, 1, 26)

    def test_every_day_of_a_full_year_resolves_with_no_gap_or_overlap(self):
        # Regression guard: walk a full calendar year day by day (including
        # the Dec->Jan boundary) and confirm every period transition is
        # contiguous -- the next period always starts the day after the
        # previous one ends, never a gap, never an overlap.
        day = date(2026, 1, 1)
        one_year_later = date(2027, 1, 1)
        previous_period: tuple[date, date] | None = None
        while day < one_year_later:
            period = banlist_period_containing(day)
            start, end = period
            assert start <= day <= end
            if previous_period is not None and period != previous_period:
                assert start == previous_period[1] + timedelta(days=1)
            previous_period = period
            day += timedelta(days=1)


class TestRolling30dWindow:
    def test_date_from_is_thirty_days_before_date_to(self):
        window = rolling_30d_window(date(2026, 6, 15))
        assert window.date_from == date(2026, 5, 16)
        assert window.date_to == date(2026, 6, 15)
        assert window.kind is WindowKind.rolling_30d

    def test_label_is_stable_for_the_same_date_to(self):
        a = rolling_30d_window(date(2026, 6, 15))
        b = rolling_30d_window(date(2026, 6, 15))
        assert a.label == b.label


class TestBanlistPeriodWindow:
    def test_wraps_banlist_period_containing(self):
        window = banlist_period_window(date(2026, 4, 15))
        assert window.date_from == date(2026, 3, 31)
        assert window.date_to == date(2026, 5, 25)
        assert window.kind is WindowKind.banlist_period

    def test_label_distinguishes_different_periods(self):
        a = banlist_period_window(date(2026, 4, 15))
        b = banlist_period_window(date(2026, 10, 1))
        assert a.label != b.label


class TestResolveWindows:
    def test_resolves_both_kinds(self):
        windows = resolve_windows(
            date(2026, 4, 15), (WindowKind.rolling_30d, WindowKind.banlist_period)
        )
        assert len(windows) == 2
        assert {w.kind for w in windows} == {
            WindowKind.rolling_30d,
            WindowKind.banlist_period,
        }

    def test_resolves_a_single_kind(self):
        windows = resolve_windows(date(2026, 4, 15), (WindowKind.rolling_30d,))
        assert len(windows) == 1
        assert windows[0].kind is WindowKind.rolling_30d


class TestWindowLabel:
    def test_rolling_and_banlist_labels_never_collide(self):
        rolling = Window(
            kind=WindowKind.rolling_30d,
            date_from=date(2026, 3, 31),
            date_to=date(2026, 5, 25),
        )
        banlist = Window(
            kind=WindowKind.banlist_period,
            date_from=date(2026, 3, 31),
            date_to=date(2026, 5, 25),
        )
        assert rolling.label != banlist.label
