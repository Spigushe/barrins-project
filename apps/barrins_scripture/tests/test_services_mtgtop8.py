import importlib
from collections import defaultdict
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

# Same package-shadowing situation as test_services_mtgo.py — see that
# file's comment for why importlib.import_module is used here.
service = importlib.import_module("barrins_scripture.services.mtgtop8")


class TestProducer:
    def test_queues_a_scrapable_tournament(self) -> None:
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        soup = BeautifulSoup(
            "<div class='meta_arch'>Duel Commander</div>", "html.parser"
        )
        with (
            patch.object(
                service.mtgtop8_utils, "get_tournament_soup", return_value=soup
            ),
            patch.object(
                service.mtgtop8_utils, "we_should_scrape_it", return_value=True
            ),
            patch.object(service.time, "sleep"),
        ):
            service.producer(88803, queue, set())

        assert queue.qsize() == 1
        url, queued_soup = queue.get()
        assert url == "https://mtgtop8.com/event?e=88803"
        assert queued_soup is soup

    def test_skips_a_missing_event(self) -> None:
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        soup = BeautifulSoup("No event could be found.", "html.parser")
        with (
            patch.object(
                service.mtgtop8_utils, "get_tournament_soup", return_value=soup
            ),
            patch.object(service.time, "sleep"),
        ):
            service.producer(1, queue, set())
        assert queue.empty()

    def test_skips_an_already_scraped_tournament(self) -> None:
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        soup = BeautifulSoup(
            "<div class='meta_arch'>Duel Commander</div>", "html.parser"
        )
        with (
            patch.object(
                service.mtgtop8_utils, "get_tournament_soup", return_value=soup
            ),
            patch.object(
                service.mtgtop8_utils, "we_should_scrape_it", return_value=False
            ),
            patch.object(service.time, "sleep"),
        ):
            service.producer(1, queue, set())
        assert queue.empty()

    def test_skips_a_tournament_on_network_error(self) -> None:
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        with (
            patch.object(
                service.mtgtop8_utils,
                "get_tournament_soup",
                side_effect=requests.exceptions.ConnectionError("No route to host"),
            ),
            patch.object(service.time, "sleep"),
        ):
            service.producer(1, queue, set())
        assert queue.empty()

    def test_skips_an_unknown_format(self) -> None:
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        soup = BeautifulSoup("<div class='meta_arch'>Chess</div>", "html.parser")
        with (
            patch.object(
                service.mtgtop8_utils, "get_tournament_soup", return_value=soup
            ),
            patch.object(
                service.mtgtop8_utils, "we_should_scrape_it", return_value=True
            ),
            patch.object(service.time, "sleep"),
        ):
            service.producer(1, queue, set())
        assert queue.empty()


class TestConsumer:
    def test_saves_a_successful_scrape(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        queue.put(("https://mtgtop8.com/event?e=1", soup))
        scrape = Mock()

        with (
            patch.object(
                service.mtgtop8_utils, "scrape_tournament", return_value=scrape
            ) as mock_scrape,
            patch.object(service.mtgtop8_utils, "save_tournament_scrape") as mock_save,
            patch.object(service.time, "sleep"),
        ):
            producers_done = Event()
            producers_done.set()
            service.consumer(
                queue, Lock(), 1, defaultdict(int), producers_done, poll_interval=0.01
            )

        mock_scrape.assert_called_once()
        mock_save.assert_called_once_with(scrape)

    def test_retries_keep_the_same_soup_then_give_up(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        queue.put(("https://mtgtop8.com/event?e=1", soup))
        retries: defaultdict[str, int] = defaultdict(int)

        with (
            patch.object(service.mtgtop8_utils, "scrape_tournament", return_value=None),
            patch.object(service.time, "sleep"),
        ):
            producers_done = Event()
            producers_done.set()
            service.consumer(
                queue,
                Lock(),
                1,
                retries,
                producers_done,
                max_retries=2,
                poll_interval=0.01,
            )

        assert retries["https://mtgtop8.com/event?e=1"] == 2
        assert queue.empty()

    def test_an_unexpected_exception_marks_the_task_done(self) -> None:
        soup = BeautifulSoup("<html></html>", "html.parser")
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        queue.put(("https://mtgtop8.com/event?e=1", soup))

        with (
            patch.object(
                service.mtgtop8_utils,
                "scrape_tournament",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(service.time, "sleep"),
        ):
            producers_done = Event()
            producers_done.set()
            service.consumer(
                queue, Lock(), 1, defaultdict(int), producers_done, poll_interval=0.01
            )

        assert queue.empty()

    def test_does_not_exit_while_queue_is_empty_but_producers_are_still_running(
        self,
    ) -> None:
        # This is the pipelining fix itself: a consumer must keep polling an
        # empty queue rather than treating "empty" as "done", since a slow
        # producer batch can leave the queue momentarily empty mid-run.
        queue: Queue[tuple[str, BeautifulSoup]] = Queue()
        producers_done = Event()
        thread = Thread(
            target=service.consumer,
            args=(queue, Lock(), 1, defaultdict(int), producers_done),
            kwargs={"poll_interval": 0.01},
        )
        thread.start()
        try:
            thread.join(timeout=0.2)
            assert thread.is_alive(), "consumer exited despite producers not done"
        finally:
            producers_done.set()
            thread.join(timeout=1)
            assert not thread.is_alive()


class TestScrapeMtgtop8:
    def test_wires_producers_and_consumers(self) -> None:
        with (
            patch.object(service.mtgtop8_utils, "get_scraped_ids", return_value=set()),
            patch.object(service, "producer") as mock_producer,
            patch.object(service, "consumer") as mock_consumer,
        ):
            service.scrape_mtgtop8(span=10, num_threads=2)

        assert mock_producer.call_count == 10
        assert mock_consumer.call_count == 2
        # The queue must stay bounded: an unbounded queue is what let a large
        # --span backfill pile up unbounded parsed BeautifulSoup trees in
        # memory and OOM the host (see scrape_mtgtop8's comment on maxsize).
        queue_arg = mock_consumer.call_args_list[0].args[0]
        assert queue_arg.maxsize == 2 * 10

    def test_output_dir_overrides_the_default_base_path(self, tmp_path: Path) -> None:
        with (
            patch.object(service.mtgtop8_utils, "get_scraped_ids", return_value=set()),
            patch.object(service, "producer"),
            patch.object(service, "consumer"),
        ):
            service.scrape_mtgtop8(span=10, num_threads=1, output_dir=tmp_path)

        assert service.mtgtop8_utils.BASE_PATH == tmp_path / "mtgtop8.com"

    def test_id_from_overrides_resuming_from_the_archive_max(self) -> None:
        with (
            patch.object(service.mtgtop8_utils, "get_scraped_ids", return_value={999}),
            patch.object(service, "producer") as mock_producer,
            patch.object(service, "consumer"),
        ):
            service.scrape_mtgtop8(span=10, num_threads=1, id_from=1)

        called_ids = sorted(call.args[0] for call in mock_producer.call_args_list)
        assert called_ids == list(range(1, 11))

    def test_id_from_defaults_to_resuming_from_the_archive_max(self) -> None:
        with (
            patch.object(service.mtgtop8_utils, "get_scraped_ids", return_value={999}),
            patch.object(service, "producer") as mock_producer,
            patch.object(service, "consumer"),
        ):
            service.scrape_mtgtop8(span=10, num_threads=1)

        called_ids = sorted(call.args[0] for call in mock_producer.call_args_list)
        assert called_ids == list(range(1000, 1010))
