from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from barrins_scripture import __main__ as cli


class TestBuildParser:
    def test_defaults_to_mtgo(self) -> None:
        args = cli.build_parser().parse_args([])
        assert args.source == "mtgo"
        assert args.span == 1000
        assert args.force_mtgo is False

    def test_accepts_mtgtop8_with_a_span(self) -> None:
        args = cli.build_parser().parse_args(["--source", "mtgtop8", "--span", "50"])
        assert args.source == "mtgtop8"
        assert args.span == 50

    def test_rejects_unknown_source(self) -> None:
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["--source", "mtgprime"])


class TestMain:
    def test_mtgo_source_calls_services_mtgo(self) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "scrape",
                    "--source",
                    "mtgo",
                    "--date-from",
                    "2026-06",
                    "--date-to",
                    "2026-07",
                ],
            ),
            patch.object(cli.services, "mtgo") as mock_mtgo,
        ):
            cli.main()
        mock_mtgo.assert_called_once_with(
            datetime(2026, 6, 1), datetime(2026, 7, 1), False, output_dir=None
        )

    def test_mtgtop8_source_calls_services_mtgtop8(self) -> None:
        with (
            patch("sys.argv", ["scrape", "--source", "mtgtop8", "--span", "42"]),
            patch.object(cli.services, "mtgtop8") as mock_mtgtop8,
        ):
            cli.main()
        mock_mtgtop8.assert_called_once_with(42, output_dir=None)

    def test_output_dir_is_forwarded(self, tmp_path: Path) -> None:
        with (
            patch(
                "sys.argv",
                ["scrape", "--source", "mtgtop8", "--output-dir", str(tmp_path)],
            ),
            patch.object(cli.services, "mtgtop8") as mock_mtgtop8,
        ):
            cli.main()
        mock_mtgtop8.assert_called_once_with(1000, output_dir=tmp_path)

    def test_bad_date_format_exits_with_an_error(self) -> None:
        with (
            patch("sys.argv", ["scrape", "--date-from", "not-a-date"]),
            patch.object(cli.services, "mtgo") as mock_mtgo,
            pytest.raises(SystemExit),
        ):
            cli.main()
        mock_mtgo.assert_not_called()
