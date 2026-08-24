import argparse
import logging
import sys
import time
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread

from barrins_scripture.services.mtgtop8 import Top8Queue, consumer, producer
from barrins_scripture.utils import mtgtop8 as mtgtop8_utils

logger = logging.getLogger(__name__)


def get_gaps(max_gaps: int | None = 2000) -> list[int]:
    scraped_ids = [
        int(file.stem.split("_")[0]) for file in mtgtop8_utils.BASE_PATH.rglob("*.json")
    ]
    if not scraped_ids:
        return []

    missing = sorted(
        set(range(1, max(scraped_ids) + 1)) - set(scraped_ids), reverse=True
    )
    return missing[:max_gaps] if max_gaps is not None else missing


def _format_eta(seconds: float) -> str:
    """`H:MM:SS` (or `MM:SS` under an hour) -- same format as sweep.py's
    `_format_eta`, duplicated here rather than shared since these two CLI
    scripts have no other coupling."""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _render_progress(done: int, total: int, elapsed: float, width: int = 30) -> str:
    """`\\r`-prefixed single-line bar -- overwrites in place, never scrolls.

    Unlike sweep.py's `_render_progress`, there's no per-chunk sub-bar: a
    chunk here is produced (batches of threads, joined synchronously) and
    then consumed (retried internally, nothing returned to the caller), so
    there's no future/result to count success/failure by -- only "chunks
    completed" is observable from this function's perspective.
    """
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    stats = f"{done}/{total} chunks"
    if done:
        remaining = elapsed / done * (total - done)
        stats += f" eta {_format_eta(remaining)}"
    return f"\rchunks [{bar}] {stats}"


#: Clears the current terminal line and returns the cursor to its start --
#: same escape code as sweep.py's `_CLEAR_LINE`.
_CLEAR_LINE = "\x1b[2K\r"


def _chunked[T](items: list[T], size: int) -> Iterator[list[T]]:
    """Yields `items` sliced into consecutive lists of at most `size`."""
    for start in range(0, len(items), size):
        yield items[start : start + size]


def scrape_gaps(
    max_missing: int = 2000,
    chunk_size: int = 100,
    batch_size: int = 10,
    num_threads: int = 4,
    output_dir: Path | None = None,
    progress: bool = False,
) -> None:
    if output_dir is not None:
        # Same override as services.mtgtop8.scrape_mtgtop8's output_dir --
        # the JSON archive is stored outside this monorepo (a plain clone
        # managed by the deployment, see ops/.../scripture_scraper), so the
        # module-level default (apps/barrins_scripture/scraped/mtgtop8.com)
        # only ever applies to a from-repo local run.
        mtgtop8_utils.BASE_PATH = Path(output_dir) / "mtgtop8.com"

    missing_ids = get_gaps(max_missing)
    logger.info("found %d missing tournaments", len(missing_ids))
    if not missing_ids:
        return

    # Walked once and reused by every producer call below (see
    # scrape_mtgtop8's identical rationale) instead of each candidate
    # re-walking the whole archive tree from scratch.
    scraped_ids = mtgtop8_utils.get_scraped_ids()

    chunks = list(_chunked(missing_ids, chunk_size))
    total_chunks = len(chunks)
    start = time.monotonic()

    if progress:
        sys.stderr.write(_render_progress(0, total_chunks, 0.0) + "\n")
        sys.stderr.flush()

    for chunk_index, chunk_ids in enumerate(chunks, start=1):
        task_queue: Top8Queue = Queue()
        lock = Lock()
        retries: dict[str, int] = defaultdict(int)

        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i : i + batch_size]
            threads = [
                Thread(target=producer, args=(event_id, task_queue, scraped_ids))
                for event_id in batch
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Every producer batch above already ran to completion (joined
        # before this point), so the queue is done filling before any
        # consumer starts -- unlike scrape_mtgtop8's fully async design,
        # producers_done is set up front rather than signaled concurrently.
        producers_done = Event()
        producers_done.set()
        consumer_threads = [
            Thread(
                target=consumer,
                args=(task_queue, lock, i + 1, retries, producers_done),
            )
            for i in range(num_threads)
        ]
        for t in consumer_threads:
            t.start()
        for t in consumer_threads:
            t.join()

        if progress:
            sys.stderr.write(_CLEAR_LINE)
            sys.stderr.write(
                _render_progress(chunk_index, total_chunks, time.monotonic() - start)
            )
            sys.stderr.flush()

    if progress:
        sys.stderr.write("\n")
        sys.stderr.flush()

    still_missing = get_gaps(max_gaps=None)
    logger.info("still missing %d tournaments", len(still_missing))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find and backfill gaps in the mtgtop8.com JSON archive."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "directory the JSON archive lives under (reads/writes "
            "<output-dir>/mtgtop8.com) - same meaning as `scrape "
            "--output-dir`. Defaults to apps/barrins_scripture/scraped/ if "
            "not given."
        ),
    )
    parser.add_argument("--max-missing", type=int, default=2000)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument(
        "--progress",
        action="store_true",
        help=(
            "show a live progress bar on stderr while backfilling "
            "(default: off -- for interactive/manual runs, not cron)"
        ),
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = build_parser().parse_args()
    scrape_gaps(
        max_missing=args.max_missing,
        chunk_size=args.chunk_size,
        batch_size=args.batch_size,
        num_threads=args.num_threads,
        output_dir=args.output_dir,
        progress=args.progress,
    )


if __name__ == "__main__":
    main()
