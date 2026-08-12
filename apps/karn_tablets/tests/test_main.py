from datetime import date

import pytest

from karn_tablets import __main__ as cli
from karn_tablets.pipeline import ClusteringRunResult
from karn_tablets.windowing import Window, WindowKind


def _empty_result(window: Window) -> ClusteringRunResult:
    return ClusteringRunResult(window=window, algorithm="kmeans", total_decks=0)


class TestBuildParser:
    def test_defaults(self):
        args = cli.build_parser().parse_args([])
        assert args.window == "both"
        assert args.algorithm == "kmeans"
        assert args.dry_run is False

    def test_rejects_unknown_window_choice(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["--window", "bogus"])


class TestWindowKinds:
    def test_both_resolves_to_two_kinds(self):
        assert cli._window_kinds("both") == (
            WindowKind.rolling_30d,
            WindowKind.banlist_period,
        )

    def test_single_kind_resolves_to_one(self):
        assert cli._window_kinds("rolling_30d") == (WindowKind.rolling_30d,)


class TestRun:
    def test_dry_run_never_calls_push(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            cli.pipeline, "run", lambda window, algorithm: _empty_result(window)
        )
        called = []
        monkeypatch.setattr(
            cli.push, "push", lambda *_a, **_kw: called.append(1) or True
        )

        ok = cli.run(
            date(2026, 5, 15), "rolling_30d", "kmeans", None, None, dry_run=True
        )
        assert ok is True
        assert called == []

    def test_missing_credentials_fails_without_pushing(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            cli.pipeline, "run", lambda window, algorithm: _empty_result(window)
        )
        ok = cli.run(
            date(2026, 5, 15), "rolling_30d", "kmeans", None, None, dry_run=False
        )
        assert ok is False

    def test_successful_push_for_every_window(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            cli.pipeline, "run", lambda window, algorithm: _empty_result(window)
        )
        monkeypatch.setattr(cli.push, "push", lambda *_a, **_kw: True)

        ok = cli.run(
            date(2026, 5, 15), "both", "kmeans", "https://api.example.com", "tok", False
        )
        assert ok is True

    def test_one_failed_push_marks_the_whole_run_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            cli.pipeline, "run", lambda window, algorithm: _empty_result(window)
        )
        results = iter([True, False])
        monkeypatch.setattr(cli.push, "push", lambda *_a, **_kw: next(results))

        ok = cli.run(
            date(2026, 5, 15), "both", "kmeans", "https://api.example.com", "tok", False
        )
        assert ok is False
