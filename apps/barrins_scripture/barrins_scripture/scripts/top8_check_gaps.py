import argparse
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread

from barrins_scripture.services.mtgtop8 import Top8Queue, consumer, producer
from barrins_scripture.utils import mtgtop8 as mtgtop8_utils
from barrins_scripture.utils.progress import CLEAR_LINE, chunked, render_progress

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

    chunks = list(chunked(missing_ids, chunk_size))
    total_chunks = len(chunks)
    start = time.monotonic()

    if progress:
        sys.stderr.write(
            render_progress(0, total_chunks, 0.0, prefix="chunks ", suffix="chunks")
            + "\n"
        )
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
            sys.stderr.write(CLEAR_LINE)
            sys.stderr.write(
                render_progress(
                    chunk_index,
                    total_chunks,
                    time.monotonic() - start,
                    prefix="chunks ",
                    suffix="chunks",
                )
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
