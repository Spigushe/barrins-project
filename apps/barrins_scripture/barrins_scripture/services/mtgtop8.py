import logging
import time
from collections import defaultdict
from pathlib import Path
from queue import Queue
from threading import Lock, Thread

from bs4 import BeautifulSoup

from barrins_scripture.parsers import mtgtop8 as parser
from barrins_scripture.utils import mtgtop8 as mtgtop8_utils

logger = logging.getLogger(__name__)

Top8Queue = Queue[tuple[str, BeautifulSoup]]


def scrape_mtgtop8(
    span: int = 1000,
    num_threads: int = 4,
    output_dir: Path | None = None,
    id_from: int | None = None,
) -> None:
    if output_dir is not None:
        # Overrides the module-level default (apps/barrins_scripture/scraped/
        # mtgtop8.com) — lets a deployment point at wherever it manages the
        # JSON archive itself, without requiring a git submodule at a fixed
        # path.
        mtgtop8_utils.BASE_PATH = Path(output_dir) / "mtgtop8.com"

    task_queue: Top8Queue = Queue()
    lock = Lock()
    retries: dict[str, int] = defaultdict(int)

    # first_id is already the next unscraped id (get_max_id_scraped() + 1)
    # by default, so this range starts at first_id + 0, not + 1 — the
    # original code's "+ j + 1" here skipped that very first id on every
    # run. id_from overrides this to backfill an arbitrary id range instead
    # of only ever resuming forward from the archive's current max.
    first_id = (
        id_from if id_from is not None else mtgtop8_utils.get_max_id_scraped() + 1
    )
    for i in range(span // 10):
        threads = [
            Thread(target=producer, args=(first_id + 10 * i + j, task_queue, lock))
            for j in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    logger.info("total tournaments queued: %d", task_queue.qsize())

    consumer_threads = [
        Thread(target=consumer, args=(task_queue, lock, i + 1, retries))
        for i in range(num_threads)
    ]
    for t in consumer_threads:
        t.start()
    for t in consumer_threads:
        t.join()


def producer(id_to_scrape: int, queue: Top8Queue, lock: Lock) -> None:
    try:
        tournament_url = mtgtop8_utils.get_tournament_url(id_to_scrape)
        tournament_soup = mtgtop8_utils.get_tournament_soup(tournament_url)

        if "No event could be found." in tournament_soup.text:
            return

        if not mtgtop8_utils.we_should_scrape_it(tournament_url):
            return

        if parser.get_format(tournament_soup) == "Unknown Format":
            return

        with lock:
            queue.put((tournament_url, tournament_soup))
    finally:
        time.sleep(0.5)  # throttle: avoid hammering mtgtop8.com


def consumer(
    queue: Top8Queue,
    lock: Lock,
    thread_id: int,
    retries: defaultdict[str, int],
    max_retries: int = 3,
) -> None:
    while True:
        with lock:
            if queue.empty():
                break
            url_task, soup_task = queue.get()

        try:
            scrape = mtgtop8_utils.scrape_tournament(url=url_task, soup=soup_task)
            if scrape:
                mtgtop8_utils.save_tournament_scrape(scrape)
                queue.task_done()
            else:
                with lock:
                    retries[url_task] += 1
                    if retries[url_task] < max_retries:
                        # Keep the same soup for the retry — this consumer
                        # never re-fetches, so re-queuing without it would
                        # crash the next `url_task, soup_task = queue.get()`
                        # unpack (a bug in the original mtg_scraper code).
                        queue.put((url_task, soup_task))
                    else:
                        logger.warning(
                            "skipping %s after %d attempts", url_task, max_retries
                        )
                        queue.task_done()
        except Exception:
            logger.exception("thread-%d failed handling %s", thread_id, url_task)
            queue.task_done()
        finally:
            time.sleep(0.5)
