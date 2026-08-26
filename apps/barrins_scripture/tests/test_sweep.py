"""Tests for `barrins_scripture.sweep` (T3): archive selection + posting.

Mirrors `test_main.py`'s style (`patch.object`/`patch("sys.argv", ...)`)
rather than a live HTTP server — `sweep()`'s only external dependency is
`requests.post`, mocked here the same way `mtgtop8_utils.requests.get` is
mocked in `test_parsers_units.py`.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from barrins_scripture import sweep


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def archive(tmp_path: Path) -> Path:
    """Two source dirs, each with one file inside and one outside a 7-day
    window measured from `now=2026-08-10` (cutoff `2026-08-03`)."""
    _write(
        tmp_path / "mtgo.com" / "2026" / "08" / "01" / "old.json",
        {"tournament": {"name": "old mtgo"}},
    )
    _write(
        tmp_path / "mtgo.com" / "2026" / "08" / "05" / "recent.json",
        {"tournament": {"name": "recent mtgo"}},
    )
    _write(
        tmp_path / "mtgtop8.com" / "2026" / "07" / "15" / "old_top8.json",
        {"tournament": {"name": "old top8"}},
    )
    _write(
        tmp_path / "mtgtop8.com" / "2026" / "08" / "09" / "recent_top8.json",
        {"tournament": {"name": "recent top8"}},
    )
    return tmp_path


_NOW = datetime(2026, 8, 10)


class TestIterArchiveFiles:
    def test_full_mode_lists_every_file(self, archive: Path) -> None:
        found = list(sweep.iter_archive_files(archive, mode="full", days=7, now=_NOW))
        assert len(found) == 4

    def test_recent_mode_filters_by_directory_encoded_date(self, archive: Path) -> None:
        found = sorted(
            (path.name, source)
            for path, source in sweep.iter_archive_files(
                archive, mode="recent", days=7, now=_NOW
            )
        )
        assert found == [
            ("recent.json", "mtgo"),
            ("recent_top8.json", "mtgtop8"),
        ]

    def test_source_is_derived_from_directory(self, archive: Path) -> None:
        by_name = {
            path.name: source
            for path, source in sweep.iter_archive_files(
                archive, mode="full", days=7, now=_NOW
            )
        }
        assert by_name["old.json"] == "mtgo"
        assert by_name["old_top8.json"] == "mtgtop8"

    def test_missing_source_dir_is_skipped(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "mtgo.com" / "2026" / "08" / "05" / "only.json",
            {"tournament": {"name": "only"}},
        )
        # mtgtop8.com never created — must not raise.
        found = list(sweep.iter_archive_files(tmp_path, mode="full", days=7, now=_NOW))
        assert len(found) == 1


class TestSweep:
    def test_posts_every_selected_file_with_source_and_token(
        self, archive: Path
    ) -> None:
        mock_response = Mock()
        with patch.object(sweep.requests, "post", return_value=mock_response) as post:
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
            )

        assert (succeeded, failed) == (4, 0)
        assert post.call_count == 4
        for call in post.call_args_list:
            assert call.args[0] == "https://api.example.com/internal/scripture/ingest"
            assert call.kwargs["headers"] == {"X-Scripture-Token": "secret-token"}
            assert "source" in call.kwargs["json"]
            assert call.kwargs["json"]["source"] in ("mtgo", "mtgtop8")

    def test_recent_mode_only_posts_recent_files(self, archive: Path) -> None:
        mock_response = Mock()
        with patch.object(sweep.requests, "post", return_value=mock_response) as post:
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
            )
        assert (succeeded, failed) == (2, 0)
        assert post.call_count == 2

    def test_continues_after_a_failed_post(self, archive: Path) -> None:
        # concurrency=1 pins execution order to submission order, so the
        # side_effect list below lines up with the two "recent" files --
        # otherwise which file gets which side effect is a race.
        with patch.object(
            sweep.requests,
            "post",
            side_effect=[requests.ConnectionError("down"), Mock()],
        ) as post:
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
                concurrency=1,
            )
        assert (succeeded, failed) == (1, 1)
        assert post.call_count == 2

    def test_raise_for_status_failure_counts_as_failed(self, archive: Path) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("503")
        with patch.object(sweep.requests, "post", return_value=mock_response):
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
            )
        assert (succeeded, failed) == (0, 2)

    def test_skips_malformed_json_without_posting(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "mtgo.com" / "2026" / "08" / "05" / "broken.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{not valid json", encoding="utf-8")

        with patch.object(sweep.requests, "post") as post:
            succeeded, failed = sweep.sweep(
                tmp_path,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
            )
        assert (succeeded, failed) == (0, 1)
        post.assert_not_called()

    def test_skips_valid_json_that_is_not_an_object_without_crashing(
        self, tmp_path: Path
    ) -> None:
        """A syntactically valid JSON array/scalar can't take payload["source"]
        = source; that must be a per-file skip, not a run-aborting crash."""
        bad_path = tmp_path / "mtgo.com" / "2026" / "08" / "05" / "not_an_object.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("[]", encoding="utf-8")
        good_path = tmp_path / "mtgo.com" / "2026" / "08" / "06" / "good.json"
        good_path.parent.mkdir(parents=True, exist_ok=True)
        good_path.write_text(
            json.dumps({"tournament": {"name": "good"}}), encoding="utf-8"
        )

        mock_response = Mock()
        with patch.object(sweep.requests, "post", return_value=mock_response) as post:
            succeeded, failed = sweep.sweep(
                tmp_path,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
            )
        # The bad file is skipped (counted as failed); the good file is
        # still posted -- the run must not abort partway through.
        assert (succeeded, failed) == (1, 1)
        assert post.call_count == 1

    def test_concurrency_is_forwarded_to_the_thread_pool(self, archive: Path) -> None:
        with (
            patch.object(sweep.requests, "post", return_value=Mock()),
            patch.object(
                sweep.concurrent.futures,
                "ThreadPoolExecutor",
                wraps=sweep.concurrent.futures.ThreadPoolExecutor,
            ) as pool_cls,
        ):
            sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
                concurrency=3,
            )
        pool_cls.assert_called_once_with(max_workers=3)

    def test_no_files_selected_does_not_touch_the_thread_pool(
        self, tmp_path: Path
    ) -> None:
        with patch.object(sweep.concurrent.futures, "ThreadPoolExecutor") as pool_cls:
            succeeded, failed = sweep.sweep(
                tmp_path,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
            )
        assert (succeeded, failed) == (0, 0)
        pool_cls.assert_not_called()

    def test_chunk_size_splits_selection_across_multiple_pools(
        self, archive: Path
    ) -> None:
        """4 files with chunk_size=1 must yield 4 separate thread pools --
        the whole point of chunking is that a chunk's payloads are read,
        posted, and dropped before the next chunk's are read, so at most
        chunk_size payloads are ever in memory at once."""
        with (
            patch.object(sweep.requests, "post", return_value=Mock()),
            patch.object(
                sweep.concurrent.futures,
                "ThreadPoolExecutor",
                wraps=sweep.concurrent.futures.ThreadPoolExecutor,
            ) as pool_cls,
        ):
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
                chunk_size=1,
            )
        assert (succeeded, failed) == (4, 0)
        assert pool_cls.call_count == 4

    def test_chunk_size_larger_than_selection_uses_one_pool(
        self, archive: Path
    ) -> None:
        with (
            patch.object(sweep.requests, "post", return_value=Mock()),
            patch.object(
                sweep.concurrent.futures,
                "ThreadPoolExecutor",
                wraps=sweep.concurrent.futures.ThreadPoolExecutor,
            ) as pool_cls,
        ):
            succeeded, failed = sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
                chunk_size=sweep.DEFAULT_CHUNK_SIZE,
            )
        assert (succeeded, failed) == (4, 0)
        assert pool_cls.call_count == 1

    def test_endpoint_trailing_slash_is_normalized(self, archive: Path) -> None:
        mock_response = Mock()
        with patch.object(sweep.requests, "post", return_value=mock_response) as post:
            sweep.sweep(
                archive,
                api_url="https://api.example.com/",
                token="secret-token",  # noqa: S106
                mode="recent",
                days=7,
                now=_NOW,
            )
        assert (
            post.call_args.args[0]
            == "https://api.example.com/internal/scripture/ingest"
        )


class TestBuildParser:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BARRINS_API_URL", raising=False)
        monkeypatch.delenv("SCRIPTURE_INGEST_TOKEN", raising=False)
        args = sweep.build_parser().parse_args([])
        assert args.mode == "recent"
        assert args.days == sweep.DEFAULT_RECENT_DAYS
        assert args.api_url is None
        assert args.token is None
        assert args.concurrency == sweep.DEFAULT_CONCURRENCY
        assert args.progress is False
        assert args.chunk_size == sweep.DEFAULT_CHUNK_SIZE
        assert args.fast_forward is False

    def test_reads_fast_forward_flag(self) -> None:
        args = sweep.build_parser().parse_args(["--fast-forward"])
        assert args.fast_forward is True

    def test_reads_concurrency_flag(self) -> None:
        args = sweep.build_parser().parse_args(["--concurrency", "12"])
        assert args.concurrency == 12

    def test_reads_progress_flag(self) -> None:
        args = sweep.build_parser().parse_args(["--progress"])
        assert args.progress is True

    def test_reads_chunk_size_flag(self) -> None:
        args = sweep.build_parser().parse_args(["--chunk-size", "50"])
        assert args.chunk_size == 50

    def test_rejects_unknown_mode(self) -> None:
        with pytest.raises(SystemExit):
            sweep.build_parser().parse_args(["--mode", "partial"])

    def test_reads_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BARRINS_API_URL", "https://api.example.com")
        monkeypatch.setenv("SCRIPTURE_INGEST_TOKEN", "env-token")
        args = sweep.build_parser().parse_args([])
        assert args.api_url == "https://api.example.com"
        assert args.token == "env-token"  # noqa: S105

    def test_reads_archive_dir_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("BARRINS_SCRIPTURE_ARCHIVE_DIR", str(tmp_path / "archive"))
        args = sweep.build_parser().parse_args([])
        assert args.archive_dir == tmp_path / "archive"


class TestMain:
    def test_missing_api_url_and_token_exits_with_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BARRINS_API_URL", raising=False)
        monkeypatch.delenv("SCRIPTURE_INGEST_TOKEN", raising=False)
        with (
            patch("sys.argv", ["sweep"]),
            # Without this, main()'s load_dotenv() call reads the real
            # apps/barrins_scripture/.env off disk (local dev only -- CI
            # has no such file) and silently repopulates the two vars
            # this test just deleted, defeating the "missing" scenario.
            patch.object(sweep, "load_dotenv"),
            patch.object(sweep, "sweep") as mock_sweep,
            pytest.raises(SystemExit),
        ):
            sweep.main()
        mock_sweep.assert_not_called()

    def test_forwards_args_and_exits_zero_on_full_success(self, tmp_path: Path) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "sweep",
                    "--mode",
                    "full",
                    "--days",
                    "3",
                    "--archive-dir",
                    str(tmp_path),
                    "--api-url",
                    "https://api.example.com",
                    "--token",
                    "tok",
                ],
            ),
            patch.object(sweep, "sweep", return_value=(2, 0)) as mock_sweep,
        ):
            sweep.main()  # must not raise
        mock_sweep.assert_called_once_with(
            tmp_path,
            "https://api.example.com",
            "tok",
            "full",
            3,
            concurrency=sweep.DEFAULT_CONCURRENCY,
            progress=False,
            chunk_size=sweep.DEFAULT_CHUNK_SIZE,
            fast_forward=False,
        )

    def test_exits_nonzero_when_any_file_failed(self, tmp_path: Path) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "sweep",
                    "--archive-dir",
                    str(tmp_path),
                    "--api-url",
                    "https://api.example.com",
                    "--token",
                    "tok",
                ],
            ),
            patch.object(sweep, "sweep", return_value=(1, 1)),
            pytest.raises(SystemExit) as exc_info,
        ):
            sweep.main()
        assert exc_info.value.code == 1

    def test_fast_forward_with_recent_mode_exits_with_error(
        self, tmp_path: Path
    ) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "sweep",
                    "--fast-forward",
                    "--archive-dir",
                    str(tmp_path),
                    "--api-url",
                    "https://api.example.com",
                    "--token",
                    "tok",
                ],
            ),
            patch.object(sweep, "sweep") as mock_sweep,
            pytest.raises(SystemExit),
        ):
            sweep.main()
        mock_sweep.assert_not_called()

    def test_fast_forward_with_full_mode_is_forwarded(self, tmp_path: Path) -> None:
        with (
            patch(
                "sys.argv",
                [
                    "sweep",
                    "--mode",
                    "full",
                    "--fast-forward",
                    "--archive-dir",
                    str(tmp_path),
                    "--api-url",
                    "https://api.example.com",
                    "--token",
                    "tok",
                ],
            ),
            patch.object(sweep, "sweep", return_value=(0, 0)) as mock_sweep,
        ):
            sweep.main()
        assert mock_sweep.call_args.kwargs["fast_forward"] is True


class TestFastForwardSweep:
    def test_skips_files_with_already_ingested_urls(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "mtgo.com" / "2026" / "08" / "01" / "known.json",
            {"tournament": {"name": "known", "url": "https://mtgo.com/known"}},
        )
        _write(
            tmp_path / "mtgo.com" / "2026" / "08" / "02" / "new.json",
            {"tournament": {"name": "new", "url": "https://mtgo.com/new"}},
        )
        mock_get_response = Mock()
        mock_get_response.json.return_value = {"urls": ["https://mtgo.com/known"]}
        with (
            patch.object(sweep.requests, "get", return_value=mock_get_response) as get,
            patch.object(sweep.requests, "post", return_value=Mock()) as post,
        ):
            succeeded, failed = sweep.sweep(
                tmp_path,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
                fast_forward=True,
            )
        assert (succeeded, failed) == (1, 0)
        assert post.call_count == 1
        assert (
            post.call_args.kwargs["json"]["tournament"]["url"] == "https://mtgo.com/new"
        )
        get.assert_called_once_with(
            "https://api.example.com/internal/scripture/ingested-urls",
            headers={"X-Scripture-Token": "secret-token"},
            timeout=30,
        )

    def test_fetch_failure_falls_back_to_posting_everything(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path / "mtgo.com" / "2026" / "08" / "01" / "only.json",
            {"tournament": {"name": "only", "url": "https://mtgo.com/only"}},
        )
        with (
            patch.object(
                sweep.requests, "get", side_effect=requests.ConnectionError("down")
            ),
            patch.object(sweep.requests, "post", return_value=Mock()) as post,
        ):
            succeeded, failed = sweep.sweep(
                tmp_path,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
                fast_forward=True,
            )
        assert (succeeded, failed) == (1, 0)
        post.assert_called_once()

    def test_fast_forward_off_never_calls_get(self, archive: Path) -> None:
        with (
            patch.object(sweep.requests, "get") as get,
            patch.object(sweep.requests, "post", return_value=Mock()),
        ):
            sweep.sweep(
                archive,
                api_url="https://api.example.com",
                token="secret-token",  # noqa: S106
                mode="full",
                days=7,
            )
        get.assert_not_called()
