import logging
from collections import defaultdict
from queue import Queue
from threading import Lock, Thread

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


def scrape_gaps(
    max_missing: int = 2000,
    chunk_size: int = 100,
    batch_size: int = 10,
    num_threads: int = 4,
) -> None:
    missing_ids = get_gaps(max_missing)
    logger.info("found %d missing tournaments", len(missing_ids))
    if not missing_ids:
        return

    for chunk_start in range(0, len(missing_ids), chunk_size):
        chunk_ids = missing_ids[chunk_start : chunk_start + chunk_size]
        task_queue: Top8Queue = Queue()
        lock = Lock()
        retries: dict[str, int] = defaultdict(int)

        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i : i + batch_size]
            threads = [
                Thread(target=producer, args=(event_id, task_queue, lock))
                for event_id in batch
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        consumer_threads = [
            Thread(target=consumer, args=(task_queue, lock, i + 1, retries))
            for i in range(num_threads)
        ]
        for t in consumer_threads:
            t.start()
        for t in consumer_threads:
            t.join()

    still_missing = get_gaps(max_gaps=None)
    logger.info("still missing %d tournaments", len(still_missing))


if __name__ == "__main__":
    scrape_gaps()
