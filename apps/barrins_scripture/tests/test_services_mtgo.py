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


class TestDetectMonth:
    def test_returns_links_that_should_be_scraped(self) -> None:
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
            links = service.detect_month(driver, 2026, 6)

        assert links == ["https://example.test/a"]

    def test_force_returns_everything_regardless_of_we_should_scrape_it(self) -> None:
        driver = Mock()
        with (
            patch.object(
                service.driver_utils,
                "get_mtgo_tournaments",
                return_value=["https://example.test/a"],
            ),
            patch.object(service.mtgo_utils, "we_should_scrape_it", return_value=False),
        ):
            links = service.detect_month(driver, 2026, 6, force=True)

        assert links == ["https://example.test/a"]


class TestScrapeLinks:
    def test_wires_one_consumer_thread_per_driver(self) -> None:
        drivers = [Mock(), Mock()]
        retries: defaultdict[str, int] = defaultdict(int)

        with patch.object(service, "consumer") as mock_consumer:
            service.scrape_links(["https://example.test/a"], drivers, Lock(), retries)

        assert mock_consumer.call_count == 2
        called_drivers = [c.args[0] for c in mock_consumer.call_args_list]
        assert called_drivers == drivers


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
        driver.quit.assert_not_called()  # driver lifecycle belongs to the caller

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


class TestScrapeMtgo:
    def test_detects_and_scrapes_each_month_in_turn(self) -> None:
        drivers = [Mock()]
        calls: list[str] = []

        def fake_detect(driver, year, month, force=False):
            calls.append(f"detect-{year}-{month:02}")
            return [f"https://example.test/{year}-{month:02}"]

        def fake_scrape_links(links, drivers, lock, retries):
            calls.append(f"scrape-{links[0]}")

        with (
            patch.object(service.driver_utils, "init_driver", side_effect=drivers),
            patch.object(service, "detect_month", side_effect=fake_detect),
            patch.object(service, "scrape_links", side_effect=fake_scrape_links),
        ):
            service.scrape_mtgo(date(2026, 5, 1), date(2026, 6, 30), num_threads=1)

        assert calls == [
            "detect-2026-05",
            "scrape-https://example.test/2026-05",
            "detect-2026-06",
            "scrape-https://example.test/2026-06",
        ]
        drivers[0].quit.assert_called_once()

    def test_skips_scrape_links_when_a_month_has_nothing_to_scrape(self) -> None:
        with (
            patch.object(service.driver_utils, "init_driver", return_value=Mock()),
            patch.object(service, "detect_month", return_value=[]),
            patch.object(service, "scrape_links") as mock_scrape_links,
        ):
            service.scrape_mtgo(date(2026, 6, 1), date(2026, 6, 30), num_threads=1)

        mock_scrape_links.assert_not_called()

    def test_quits_drivers_even_if_scraping_raises(self) -> None:
        driver = Mock()
        with (
            patch.object(service.driver_utils, "init_driver", return_value=driver),
            patch.object(
                service, "detect_month", return_value=["https://example.test/a"]
            ),
            patch.object(service, "scrape_links", side_effect=RuntimeError("boom")),
        ):
            try:
                service.scrape_mtgo(date(2026, 6, 1), date(2026, 6, 30), num_threads=1)
            except RuntimeError:
                pass

        driver.quit.assert_called_once()

    def test_output_dir_overrides_the_default_base_path(self, tmp_path: Path) -> None:
        with (
            patch.object(service.driver_utils, "init_driver", return_value=Mock()),
            patch.object(service, "detect_month", return_value=[]),
            patch.object(service, "scrape_links"),
        ):
            service.scrape_mtgo(
                date(2026, 6, 1), date(2026, 6, 1), num_threads=1, output_dir=tmp_path
            )

        assert service.mtgo_utils.BASE_PATH == tmp_path / "mtgo.com"
