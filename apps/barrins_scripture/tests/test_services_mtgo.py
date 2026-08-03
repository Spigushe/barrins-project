import importlib
from collections import defaultdict
from datetime import date
from pathlib import Path
from queue import Queue
from threading import Lock
from unittest.mock import Mock, patch

# barrins_scripture.services' own __init__.py rebinds the name "mtgo" to the
# scrape_mtgo function (`from .mtgo import scrape_mtgo as mtgo`), shadowing
# the submodule of the same name on the package object — so `import
# barrins_scripture.services.mtgo` resolves to that function, not the
# module, once the package has been initialized. importlib.import_module
# reads straight from sys.modules and isn't affected by that shadowing.
service = importlib.import_module("barrins_scripture.services.mtgo")


class TestProducer:
    def test_queues_links_that_should_be_scraped(self) -> None:
        queue: Queue[str] = Queue()
        driver = Mock()
        with (
            patch.object(
                service.driver_utils,
                "get_mtgo_tournaments",
                return_value=["https://example.test/a", "https://example.test/b"],
            ),
            patch.object(
                service.mtgo_utils, "we_should_scrape_it", side_effect=[True, False]
            ),
        ):
            service.producer(queue, date(2026, 6, 1), date(2026, 6, 30), driver, Lock())

        assert queue.qsize() == 1
        assert queue.get() == "https://example.test/a"

    def test_force_queues_everything_regardless_of_we_should_scrape_it(self) -> None:
        queue: Queue[str] = Queue()
        driver = Mock()
        with (
            patch.object(
                service.driver_utils,
                "get_mtgo_tournaments",
                return_value=["https://example.test/a"],
            ),
            patch.object(service.mtgo_utils, "we_should_scrape_it", return_value=False),
        ):
            service.producer(
                queue, date(2026, 6, 1), date(2026, 6, 1), driver, Lock(), force=True
            )

        assert queue.qsize() == 1


class TestConsumer:
    def test_saves_a_successful_scrape_and_stops_when_queue_empties(self) -> None:
        queue: Queue[str] = Queue()
        queue.put("https://example.test/a")
        driver = Mock()
        scrape = Mock()

        with (
            patch.object(
                service.mtgo_utils, "scrape_tournament", return_value=scrape
            ) as mock_scrape,
            patch.object(service.mtgo_utils, "save_tournament_scrape") as mock_save,
            patch.object(service.time, "sleep"),
        ):
            service.consumer(driver, queue, Lock(), 1, defaultdict(int))

        mock_scrape.assert_called_once()
        mock_save.assert_called_once_with(scrape)
        driver.quit.assert_called_once()

    def test_retries_then_gives_up_after_max_retries(self) -> None:
        queue: Queue[str] = Queue()
        queue.put("https://example.test/a")
        driver = Mock()
        retries: defaultdict[str, int] = defaultdict(int)

        with (
            patch.object(service.mtgo_utils, "scrape_tournament", return_value=None),
            patch.object(service.mtgo_utils, "MAX_RETRIES", 2),
            patch.object(service.time, "sleep"),
        ):
            service.consumer(driver, queue, Lock(), 1, retries)

        # Requeued twice (retries 1 and 2 are both < MAX_RETRIES=2... only
        # retry 1 is < 2, so it's requeued once, then given up on retry 2.
        assert retries["https://example.test/a"] == 2
        driver.quit.assert_called_once()

    def test_an_unexpected_exception_marks_the_task_done_and_continues(self) -> None:
        queue: Queue[str] = Queue()
        queue.put("https://example.test/a")
        driver = Mock()

        with (
            patch.object(
                service.mtgo_utils,
                "scrape_tournament",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(service.time, "sleep"),
        ):
            service.consumer(driver, queue, Lock(), 1, defaultdict(int))

        assert queue.empty()
        driver.quit.assert_called_once()


class TestScrapeMtgo:
    def test_wires_producer_and_consumer_threads(self) -> None:
        with (
            patch.object(
                service.driver_utils, "init_driver", return_value=Mock()
            ) as mock_init,
            patch.object(service, "producer") as mock_producer,
            patch.object(service, "consumer") as mock_consumer,
        ):
            service.scrape_mtgo(date(2026, 6, 1), date(2026, 6, 1), num_threads=2)

        assert mock_init.call_count == 2
        mock_producer.assert_called_once()
        assert mock_consumer.call_count == 2

    def test_output_dir_overrides_the_default_base_path(self, tmp_path: Path) -> None:
        with (
            patch.object(service.driver_utils, "init_driver", return_value=Mock()),
            patch.object(service, "producer"),
            patch.object(service, "consumer"),
        ):
            service.scrape_mtgo(
                date(2026, 6, 1), date(2026, 6, 1), num_threads=1, output_dir=tmp_path
            )

        assert service.mtgo_utils.BASE_PATH == tmp_path / "mtgo.com"
