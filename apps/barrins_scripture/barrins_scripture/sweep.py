"""Sweep: reads the JSON archive and calls `barrins_api`'s ingestion route.

Standalone from the scrape CLI (`__main__.py`) — a separate concern
(ingestion, not scraping) with its own entry point
(`barrins-scripture-sweep`), scheduled on its own tick independent of the
scrape schedule (see
docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/index.md).

Recent-files mode (``--mode recent``, default) rescans the last
``--days`` days of tournament-dated archive files (default 7 — a safety
margin over MTGO's ~3-day post-publication edit window) on every
scheduled tick. Full-archive mode (``--mode full``) walks every JSON file
under the archive — the bulk-replay / disaster-recovery path: if the
``bs_*`` tables are ever dropped, this rebuilds them from the archive
alone with no scraping required.

Idempotent by construction: ``barrins_api``'s ingestion route upserts on
each table's natural key (T2), so re-submitting an already-ingested file
is a no-op, not a duplicate row. A failed POST (``barrins_api`` down, a
malformed file, ...) is logged and skipped, never retried within the same
run — the next scheduled sweep tick picks it up, per the 2026-08-07
decision superseding the original push+maintenance-gate+backoff design.

File *contents* are read and posted one ``--chunk-size`` slice at a time
rather than all at once — ``--mode full`` walks the entire archive, and
loading every JSON payload into memory up front OOMs once the archive
gets large. Only the (path, source) pairs for the whole selection are
held at once, which is cheap.
"""

import argparse
import concurrent.futures
import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

#: apps/barrins_scripture/scraped/ — same default root the scrape CLI
#: writes under (see utils/mtgo.py::BASE_PATH, utils/mtgtop8.py::BASE_PATH).
DEFAULT_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "scraped"
DEFAULT_RECENT_DAYS = 7
#: Matches `barrins_api`'s `pool_size=5` (`app/database/connection.py`) --
#: high enough to overlap files' DB round trips instead of paying them one
#: at a time, but capped at the pool's steady-state size rather than its
#: `max_overflow=10` ceiling, so a sweep tick doesn't starve other API
#: traffic of connections while it runs.
DEFAULT_CONCURRENCY = 5
#: Max archive files read + parsed into memory at once. Bounds `--mode
#: full`'s memory use to this many JSON payloads regardless of archive
#: size -- the whole point of chunking (the archive can hold far more
#: files than comfortably fit in memory at once).
DEFAULT_CHUNK_SIZE = 200


def _default_archive_dir() -> Path:
    env_dir = os.environ.get("BARRINS_SCRIPTURE_ARCHIVE_DIR")
    return Path(env_dir) if env_dir else DEFAULT_ARCHIVE_DIR


#: Archive top-level directory -> the `source` value the ingestion route
#: expects (`app.models.scripture.BSSource`). The JSON file itself never
#: records which site it came from -- only its directory does.
_SOURCE_DIRS: dict[str, str] = {"mtgo.com": "mtgo", "mtgtop8.com": "mtgtop8"}


def _is_recent(file_path: Path, base: Path, cutoff: datetime) -> bool:
    """True if `file_path`'s YYYY/MM/DD path segments are on/after `cutoff`.

    Uses the archive's own directory-encoded date (the tournament's scrape
    date), not filesystem mtime -- mtime isn't a reliable recency signal
    once the archive is a git-managed clone (a fresh checkout resets every
    file's mtime to "now").
    """
    try:
        year, month, day = file_path.relative_to(base).parts[:3]
        file_date = datetime(int(year), int(month), int(day))
    except ValueError, IndexError:
        # Malformed/unexpected path shape -- don't silently drop it, let
        # the ingestion route see (and reject) it instead. Logged (not just
        # silently included) because this makes the file match "recent" on
        # every future tick, not just once -- worth an operator noticing.
        logger.warning(
            "archive file %s has an unexpected path shape under %s; "
            "treating it as recent so it isn't silently dropped",
            file_path,
            base,
        )
        return True
    return file_date >= cutoff


def iter_archive_files(
    archive_dir: Path,
    mode: str,
    days: int,
    now: datetime | None = None,
) -> Iterator[tuple[Path, str]]:
    """Yields (file_path, source) for every JSON archive file `mode` selects."""
    now = now or datetime.now()
    # Normalized to midnight before subtracting `days` -- otherwise a file
    # dated exactly `days` days ago is excluded whenever the sweep runs
    # after 00:00:00 on the current day, quietly shrinking the lookback
    # window below the documented "--days days" safety margin.
    today = datetime(now.year, now.month, now.day)
    cutoff = today - timedelta(days=days)
    for source_dir, source in _SOURCE_DIRS.items():
        base = archive_dir / source_dir
        if not base.is_dir():
            continue
        for file_path in sorted(base.rglob("*.json")):
            if not file_path.is_file():
                continue
            if mode == "recent" and not _is_recent(file_path, base, cutoff):
                continue
            yield file_path, source


def _post_file(
    endpoint: str, headers: dict[str, str], file_path: Path, payload: dict
) -> bool:
    """POSTs one already-parsed payload. Returns True on success.

    Never raises -- a `RequestException` (connection error, timeout,
    `raise_for_status()`) is logged and reported as failure instead, so
    one bad file can't take down the whole worker pool.
    """
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("ingest failed for %s", file_path)
        return False
    return True


def _format_eta(seconds: float) -> str:
    """`H:MM:SS` (or `MM:SS` under an hour) -- `str(timedelta(...))`'s
    format, minus the microseconds it appends for a non-integer count."""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _render_progress(
    done: int,
    total: int,
    failed: int,
    elapsed: float,
    prefix: str = "",
    width: int = 30,
) -> str:
    """`\\r`-prefixed single-line bar -- overwrites in place, never scrolls.

    ETA is derived from the observed per-file rate so far (`elapsed /
    done` extrapolated over what's left) -- accurate once a handful of
    files have completed, meaningless (and hidden) before that.

    `prefix` distinguishes the chunk-advancement bar from the per-chunk
    sub-bar when both are on screen at once (see `sweep`).
    """
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    stats = f"{done}/{total} ({failed} failed)"
    if done:
        remaining = elapsed / done * (total - done)
        stats += f" eta {_format_eta(remaining)}"
    return f"\r{prefix}[{bar}] {stats}"


#: Clears the current terminal line and returns the cursor to its start,
#: and moves the cursor up one line -- used together to drop the finished
#: chunk's sub-bar and rewrite the chunk-advancement bar in its place, so
#: at most 2 progress lines are ever on screen (see `sweep`).
_CLEAR_LINE = "\x1b[2K\r"
_CURSOR_UP = "\x1b[1A"


def _chunked[T](items: list[T], size: int) -> Iterator[list[T]]:
    """Yields `items` sliced into consecutive lists of at most `size`."""
    for start in range(0, len(items), size):
        yield items[start : start + size]


def sweep(
    archive_dir: Path,
    api_url: str,
    token: str,
    mode: str = "recent",
    days: int = DEFAULT_RECENT_DAYS,
    now: datetime | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    progress: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[int, int]:
    """Posts every file `mode` selects to `POST /internal/scripture/ingest`.

    Returns (succeeded, failed). Never raises on a per-file failure --
    logs and moves on, per the no-retry/no-backoff decision (a failed
    tick is resolved by the next scheduled tick, not by retrying here).

    `now` is forwarded to `iter_archive_files` for `--mode recent`'s
    lookback window — defaults to the real current time, overridable for
    deterministic tests.

    Selection (`iter_archive_files`) is materialized up front -- cheap,
    it's just paths and a source string per file. File *contents* are
    read and posted `chunk_size` files at a time, so at most `chunk_size`
    parsed JSON payloads are ever in memory at once, regardless of how
    large `--mode full` makes the overall selection. Within a chunk,
    reading/parsing stays sequential (cheap local I/O, stable failure-log
    ordering); only the POSTs -- the actual bottleneck, one HTTP round
    trip that itself fans out into many DB round trips server-side --
    run concurrently, up to `concurrency` at a time.

    `progress`, when True, renders two live stderr lines: a
    chunk-advancement bar (chunks completed / total chunks) that persists
    across the whole run, and a sub-bar tracking POSTs completed within
    the *current* chunk. The sub-bar is cleared when its chunk finishes
    (replaced by the advanced chunk bar), so at most 2 progress lines are
    ever on screen at once rather than one line surviving per chunk.
    Off by default since a scheduled/cron invocation has no terminal to
    render it on and would otherwise fill logs with escape-code junk.
    """
    endpoint = api_url.rstrip("/") + "/internal/scripture/ingest"
    headers = {"X-Scripture-Token": token}
    succeeded = failed = 0

    selected = list(iter_archive_files(archive_dir, mode, days, now))
    if not selected:
        logger.info("sweep done (mode=%s): 0 succeeded, 0 failed", mode)
        return 0, 0

    chunks = list(_chunked(selected, chunk_size))
    total_chunks = len(chunks)
    start = time.monotonic()

    if progress:
        sys.stderr.write(
            _render_progress(0, total_chunks, 0, 0.0, prefix="chunks ") + "\n"
        )
        sys.stderr.flush()

    for chunk_index, chunk in enumerate(chunks, start=1):
        to_post: list[tuple[Path, dict]] = []
        chunk_total = len(chunk)
        chunk_done = chunk_failed = 0
        for file_path, source in chunk:
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    # A syntactically valid JSON file can still be a list,
                    # string, number, or null at the top level --
                    # `payload[...] = source` below would raise a
                    # TypeError that isn't a json.JSONDecodeError, so this
                    # file is caught here rather than being an assignment
                    # done outside the try below, where it would have
                    # crashed the whole run instead of just this one file.
                    raise TypeError(
                        f"expected a JSON object at the top level, got "
                        f"{type(payload).__name__}"
                    )
                payload["source"] = source
            except OSError, json.JSONDecodeError, TypeError:
                logger.exception("skipping unreadable archive file %s", file_path)
                failed += 1
                chunk_failed += 1
                chunk_done += 1
                continue
            to_post.append((file_path, payload))

        chunk_start = time.monotonic()
        if to_post:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [
                    pool.submit(_post_file, endpoint, headers, file_path, payload)
                    for file_path, payload in to_post
                ]
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        succeeded += 1
                    else:
                        failed += 1
                        chunk_failed += 1
                    chunk_done += 1
                    if progress:
                        elapsed = time.monotonic() - chunk_start
                        sys.stderr.write(
                            _render_progress(
                                chunk_done,
                                chunk_total,
                                chunk_failed,
                                elapsed,
                                prefix=f"  chunk {chunk_index}/{total_chunks} ",
                            )
                        )
                        sys.stderr.flush()

        if progress:
            # Drop the finished chunk's sub-bar and advance the chunk bar
            # in its place -- see the `progress` docstring above.
            sys.stderr.write(_CLEAR_LINE)
            sys.stderr.write(_CURSOR_UP)
            sys.stderr.write(_CLEAR_LINE)
            sys.stderr.write(
                _render_progress(
                    chunk_index,
                    total_chunks,
                    failed,
                    time.monotonic() - start,
                    prefix="chunks ",
                )
            )
            sys.stderr.write("\n")
            sys.stderr.flush()

    logger.info(
        "sweep done (mode=%s): %d succeeded, %d failed", mode, succeeded, failed
    )
    return succeeded, failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="barrins-scripture-sweep",
        description=(
            "Ingest the JSON archive into barrins_api's bs_* tables via "
            "POST /internal/scripture/ingest."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["recent", "full"],
        default="recent",
        help=(
            "recent: rescan the last --days days only (scheduled tick). "
            "full: walk the entire archive (bulk replay / disaster recovery)."
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_RECENT_DAYS,
        help=f"lookback window for --mode recent (default: {DEFAULT_RECENT_DAYS})",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=_default_archive_dir(),
        help="root of the JSON archive (default: apps/barrins_scripture/scraped/)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("BARRINS_API_URL"),
        help="barrins_api base URL (env: BARRINS_API_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("SCRIPTURE_INGEST_TOKEN"),
        help="shared ingestion secret (env: SCRIPTURE_INGEST_TOKEN)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=(
            "max concurrent POSTs to /internal/scripture/ingest "
            f"(default: {DEFAULT_CONCURRENCY}, matching barrins_api's DB pool_size)"
        ),
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help=(
            "show a live progress bar on stderr while posting files "
            "(default: off -- for interactive/manual runs, not cron)"
        ),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=(
            "max archive files read into memory at once "
            f"(default: {DEFAULT_CHUNK_SIZE} -- keeps --mode full bounded "
            "regardless of archive size)"
        ),
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # Local dev only -- CI (GitHub Actions) sets these as real env vars and
    # has no .env file, so this is a no-op there. Must run before
    # build_parser(), which reads os.environ.get(...) as argparse defaults.
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()
    if not args.api_url or not args.token:
        parser.error(
            "--api-url/BARRINS_API_URL and --token/SCRIPTURE_INGEST_TOKEN are required"
        )

    _succeeded, failed = sweep(
        args.archive_dir,
        args.api_url,
        args.token,
        args.mode,
        args.days,
        concurrency=args.concurrency,
        progress=args.progress,
        chunk_size=args.chunk_size,
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
