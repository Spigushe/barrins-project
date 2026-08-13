import logging
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from queue import Queue
from threading import Lock, Thread

from selenium.webdriver.chrome.webdriver import WebDriver

from barrins_scripture.utils import mtgo as mtgo_utils
from barrins_scripture.utils import selenium_driver as driver_utils
from barrins_scripture.utils.date_parsing import get_month_range

logger = logging.getLogger(__name__)

MTGOQueue = Queue[str]


def scrape_mtgo(
    date_from: date,
    date_to: date,
    force: bool = False,
    num_threads: int = 4,
    output_dir: Path | None = None,
) -> None:
    """Scrapes month by month: detect a month's tournaments, scrape exactly
    those, then move on to the next month's detection.

    Kept sequential across months (rather than detecting the whole span
    upfront the way the old producer/consumer split did) so a large
    backfill starts saving tournaments almost immediately instead of only
    after every month has been detected, and so a month's retries never mix
    with another month's queue.
    """
    if output_dir is not None:
        # Overrides the module-level default (apps/barrins_scripture/scraped/
        # mtgo.com) — lets a deployment point at wherever it manages the JSON
        # archive itself, without requiring a git submodule at a fixed path.
        mtgo_utils.BASE_PATH = Path(output_dir) / "mtgo.com"

    lock = Lock()
    drivers = [driver_utils.init_driver() for _ in range(num_threads)]
    retries: dict[str, int] = defaultdict(int)

    try:
        for year, month in get_month_range(date_from, date_to):
            links = detect_month(drivers[0], year, month, force)
            if links:
                scrape_links(links, drivers, lock, retries)
    finally:
        for driver in drivers:
            driver.quit()


def detect_month(
    driver: WebDriver,
    year: int,
    month: int,
    force: bool = False,
) -> list[str]:
    """Detects one month's tournaments and returns the subset to scrape."""
    tournament_links = driver_utils.get_mtgo_tournaments(driver, year, month)
    to_scrape = [
        link
        for link in tournament_links
        if force or mtgo_utils.we_should_scrape_it(link)
    ]
    logger.info("%s-%02d: found %d tournaments to scrape", year, month, len(to_scrape))
    return to_scrape


def scrape_links(
    links: list[str],
    drivers: list[WebDriver],
    lock: Lock,
    retries: defaultdict[str, int],
) -> None:
    """Drains `links` through one consumer thread per driver, then returns
    once the batch is fully scraped (drivers are left open for reuse)."""
    task_queue: MTGOQueue = Queue()
    for link in links:
        task_queue.put(link)

    consumer_threads = [
        Thread(target=consumer, args=(driver, task_queue, lock, i + 1, retries))
        for i, driver in enumerate(drivers)
    ]
    for t in consumer_threads:
        t.start()
    for t in consumer_threads:
        t.join()


def consumer(
    driver: WebDriver,
    queue: MTGOQueue,
    lock: Lock,
    thread_id: int,
    retries: defaultdict[str, int],
) -> None:
    while True:
        with lock:
            if queue.empty():
                break
            url_task = queue.get()

        try:
            scrape = mtgo_utils.scrape_tournament(
                driver=driver,
                url=url_task,
                timeout=mtgo_utils.DEFAULT_RENDER_TIMEOUT + 10 * retries[url_task],
                page_load_timeout=mtgo_utils.PAGE_LOAD_TIMEOUT + 10 * retries[url_task],
            )
            if scrape:
                mtgo_utils.save_tournament_scrape(scrape)
                queue.task_done()
            else:
                with lock:
                    retries[url_task] += 1
                    if retries[url_task] < mtgo_utils.MAX_RETRIES:
                        queue.put(url_task)
                    else:
                        logger.warning(
                            "skipping %s after %d attempts",
                            url_task,
                            mtgo_utils.MAX_RETRIES,
                        )
                        queue.task_done()
        except Exception:
            logger.exception("thread-%d failed handling %s", thread_id, url_task)
            queue.task_done()
        finally:
            time.sleep(0.5)  # throttle: avoid hammering mtgo.com

    # Driver lifecycle belongs to the caller, not to consumer() -- scrape_mtgo
    # reuses the same drivers across every month's batch, so quitting here
    # would kill them after the first month.
