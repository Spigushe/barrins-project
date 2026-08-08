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
"""

import argparse
import json
import logging
import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

#: apps/barrins_scripture/scraped/ — same default root the scrape CLI
#: writes under (see utils/mtgo.py::BASE_PATH, utils/mtgtop8.py::BASE_PATH).
DEFAULT_ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "scraped"
DEFAULT_RECENT_DAYS = 7


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


def sweep(
    archive_dir: Path,
    api_url: str,
    token: str,
    mode: str = "recent",
    days: int = DEFAULT_RECENT_DAYS,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Posts every file `mode` selects to `POST /internal/scripture/ingest`.

    Returns (succeeded, failed). Never raises on a per-file failure --
    logs and moves on, per the no-retry/no-backoff decision (a failed
    tick is resolved by the next scheduled tick, not by retrying here).

    `now` is forwarded to `iter_archive_files` for `--mode recent`'s
    lookback window — defaults to the real current time, overridable for
    deterministic tests.
    """
    endpoint = api_url.rstrip("/") + "/internal/scripture/ingest"
    headers = {"X-Scripture-Token": token}
    succeeded = failed = 0

    for file_path, source in iter_archive_files(archive_dir, mode, days, now):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                # A syntactically valid JSON file can still be a list,
                # string, number, or null at the top level -- `payload[...]
                # = source` below would raise a TypeError that isn't a
                # json.JSONDecodeError, so this file is caught here rather
                # than being an assignment done outside the try below,
                # where it would have crashed the whole run instead of
                # just this one file.
                raise TypeError(
                    f"expected a JSON object at the top level, got "
                    f"{type(payload).__name__}"
                )
            payload["source"] = source
        except OSError, json.JSONDecodeError, TypeError:
            logger.exception("skipping unreadable archive file %s", file_path)
            failed += 1
            continue

        try:
            response = requests.post(
                endpoint, json=payload, headers=headers, timeout=30
            )
            response.raise_for_status()
            succeeded += 1
        except requests.RequestException:
            logger.exception("ingest failed for %s", file_path)
            failed += 1

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
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    parser = build_parser()
    args = parser.parse_args()
    if not args.api_url or not args.token:
        parser.error(
            "--api-url/BARRINS_API_URL and --token/SCRIPTURE_INGEST_TOKEN are required"
        )

    _succeeded, failed = sweep(
        args.archive_dir, args.api_url, args.token, args.mode, args.days
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
