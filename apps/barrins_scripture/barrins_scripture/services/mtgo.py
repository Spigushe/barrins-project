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
    if output_dir is not None:
        # Overrides the module-level default (apps/barrins_scripture/scraped/
        # mtgo.com) — lets a deployment point at wherever it manages the JSON
        # archive itself, without requiring a git submodule at a fixed path.
        mtgo_utils.BASE_PATH = Path(output_dir) / "mtgo.com"

    task_queue: MTGOQueue = Queue()
    lock = Lock()
    drivers = [driver_utils.init_driver() for _ in range(num_threads)]
    retries: dict[str, int] = defaultdict(int)

    producer_thread = Thread(
        target=producer,
        args=(task_queue, date_from, date_to, drivers[0], lock, force),
    )

    consumer_threads = [
        Thread(target=consumer, args=(drivers[i], task_queue, lock, i + 1, retries))
        for i in range(num_threads)
    ]

    producer_thread.start()
    producer_thread.join()
    for t in consumer_threads:
        t.start()
    for t in consumer_threads:
        t.join()


def producer(
    queue: MTGOQueue,
    date_from: date,
    date_to: date,
    driver: WebDriver,
    lock: Lock,
    force: bool = False,
) -> None:
    for year, month in get_month_range(date_from, date_to):
        tournament_links = driver_utils.get_mtgo_tournaments(driver, year, month)
        to_scrape = 0
        for link in tournament_links:
            if force or mtgo_utils.we_should_scrape_it(link):
                to_scrape += 1
                with lock:
                    queue.put(link)
        logger.info("%s-%02d: found %d tournaments to scrape", year, month, to_scrape)


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

    driver.quit()
