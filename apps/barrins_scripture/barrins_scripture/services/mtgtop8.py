import logging
import time
from collections import defaultdict
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread

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

    # Bounded: producers block once the queue is full instead of piling up
    # unbounded parsed BeautifulSoup trees in memory. A large --span backfill
    # used to queue every candidate's full DOM tree before a single consumer
    # started draining it (consumers only started after every producer batch
    # had finished) - that OOM'd the host on a span=70000 run.
    task_queue: Top8Queue = Queue(maxsize=num_threads * 10)
    lock = Lock()  # guards the shared `retries` dict only
    retries: dict[str, int] = defaultdict(int)
    producers_done = Event()

    # Walked once and reused by every producer below (see
    # mtgtop8_utils.we_should_scrape_it) instead of each one re-walking the
    # archive tree from scratch - safe because it's only ever read, never
    # mutated, while producers and consumers are running.
    scraped_ids = mtgtop8_utils.get_scraped_ids()

    # first_id is already the next unscraped id (max(scraped_ids) + 1) by
    # default, so this range starts at first_id + 0, not + 1 — the original
    # code's "+ j + 1" here skipped that very first id on every run. id_from
    # overrides this to backfill an arbitrary id range instead of only ever
    # resuming forward from the archive's current max.
    first_id = id_from if id_from is not None else max(scraped_ids, default=0) + 1

    # Consumers start before producers so the queue actually drains while
    # candidates are still being produced, instead of every candidate's soup
    # sitting in memory until the last producer batch finishes.
    consumer_threads = [
        Thread(target=consumer, args=(task_queue, lock, i + 1, retries, producers_done))
        for i in range(num_threads)
    ]
    for t in consumer_threads:
        t.start()

    for i in range(span // 10):
        threads = [
            Thread(
                target=producer,
                args=(first_id + 10 * i + j, task_queue, scraped_ids),
            )
            for j in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    producers_done.set()
    logger.info(
        "finished queuing candidates; %d still pending in queue",
        task_queue.qsize(),
    )

    for t in consumer_threads:
        t.join()


def producer(id_to_scrape: int, queue: Top8Queue, scraped_ids: set[int]) -> None:
    try:
        tournament_url = mtgtop8_utils.get_tournament_url(id_to_scrape)
        tournament_soup = mtgtop8_utils.get_tournament_soup(tournament_url)

        if "No event could be found." in tournament_soup.text:
            return

        if not mtgtop8_utils.we_should_scrape_it(tournament_url, scraped_ids):
            return

        if parser.get_format(tournament_soup) == "Unknown Format":
            return

        # Blocks once the queue is full (see maxsize in scrape_mtgtop8) -
        # backpressure instead of unbounded memory growth.
        queue.put((tournament_url, tournament_soup))
    finally:
        time.sleep(0.5)  # throttle: avoid hammering mtgtop8.com


def consumer(
    queue: Top8Queue,
    lock: Lock,
    thread_id: int,
    retries: defaultdict[str, int],
    producers_done: Event,
    max_retries: int = 3,
    poll_interval: float = 0.5,
) -> None:
    while True:
        try:
            url_task, soup_task = queue.get(timeout=poll_interval)
        except Empty:
            # The queue being momentarily empty doesn't mean it's done -
            # producers may still be fetching the next batch. Only stop once
            # they've signaled there's nothing left to come.
            if producers_done.is_set():
                break
            continue

        try:
            scrape = mtgtop8_utils.scrape_tournament(url=url_task, soup=soup_task)
            if scrape:
                mtgtop8_utils.save_tournament_scrape(scrape)
                queue.task_done()
            else:
                with lock:
                    retries[url_task] += 1
                    should_retry = retries[url_task] < max_retries
                if should_retry:
                    # Keep the same soup for the retry — this consumer never
                    # re-fetches, so re-queuing without it would crash the
                    # next `url_task, soup_task = queue.get()` unpack (a bug
                    # in the original mtg_scraper code). put() is called
                    # outside the lock: since the queue is now bounded, a
                    # full queue would otherwise block this thread while it
                    # held the retries-dict lock, stalling every other
                    # consumer's retry accounting too.
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
