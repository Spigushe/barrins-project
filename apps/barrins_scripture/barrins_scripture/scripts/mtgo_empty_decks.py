import json
import logging
from collections import defaultdict
from pathlib import Path
from queue import Queue
from threading import Lock, Thread

from barrins_scripture.services.mtgo import MTGOQueue, consumer
from barrins_scripture.utils import mtgo as mtgo_utils
from barrins_scripture.utils import selenium_driver as driver_utils

logger = logging.getLogger(__name__)


def find_and_clear_empty_decks(queue: MTGOQueue, lock: Lock) -> None:
    empty_files: list[Path] = []

    for path in mtgo_utils.BASE_PATH.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            logger.exception("failed reading %s", path)
            continue

        if data.get("decks") == []:
            empty_files.append(path)
            with lock:
                queue.put(data["tournament"]["url"])

    logger.info("found %d archived tournament(s) with no decks", len(empty_files))
    for file in empty_files:
        file.unlink()


def scrape_tournaments_without_decks(num_threads: int = 4) -> None:
    task_queue: MTGOQueue = Queue()
    lock = Lock()
    drivers = [driver_utils.init_driver() for _ in range(num_threads)]
    retries: dict[str, int] = defaultdict(int)

    producer_thread = Thread(target=find_and_clear_empty_decks, args=(task_queue, lock))

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

    # consumer() no longer quits its own driver (barrins_scripture.services.mtgo
    # reuses drivers across scrape batches), so ownership is here instead.
    for driver in drivers:
        driver.quit()


if __name__ == "__main__":
    scrape_tournaments_without_decks()
