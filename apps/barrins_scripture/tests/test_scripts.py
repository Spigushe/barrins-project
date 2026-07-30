from pathlib import Path
from queue import Queue
from threading import Lock
from unittest.mock import Mock, patch

from barrins_scripture.scripts import mtgo_empty_decks, top8_check_gaps


class TestGetGaps:
    def test_empty_when_nothing_scraped(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(top8_check_gaps.mtgtop8_utils, "BASE_PATH", tmp_path)
        assert top8_check_gaps.get_gaps() == []

    def test_finds_missing_ids_below_the_max(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(top8_check_gaps.mtgtop8_utils, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "1_duel-commander_a.json").write_text("{}", encoding="utf-8")
        (d / "5_duel-commander_b.json").write_text("{}", encoding="utf-8")

        assert top8_check_gaps.get_gaps() == [4, 3, 2]

    def test_respects_max_gaps(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(top8_check_gaps.mtgtop8_utils, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "10_x_a.json").write_text("{}", encoding="utf-8")

        assert top8_check_gaps.get_gaps(max_gaps=2) == [9, 8]
        assert len(top8_check_gaps.get_gaps(max_gaps=None)) == 9


class TestScrapeGaps:
    def test_returns_early_when_nothing_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(top8_check_gaps.mtgtop8_utils, "BASE_PATH", tmp_path)
        with patch.object(top8_check_gaps, "producer") as mock_producer:
            top8_check_gaps.scrape_gaps()
        mock_producer.assert_not_called()

    def test_queues_producers_for_each_missing_id(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(top8_check_gaps.mtgtop8_utils, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "5_x_a.json").write_text("{}", encoding="utf-8")

        with (
            patch.object(top8_check_gaps, "producer") as mock_producer,
            patch.object(top8_check_gaps, "consumer"),
        ):
            top8_check_gaps.scrape_gaps(chunk_size=10, batch_size=10, num_threads=1)

        assert mock_producer.call_count == 4  # ids 1-4 are missing before 5


class TestFindAndClearEmptyDecks:
    def test_queues_and_deletes_empty_deck_archives(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgo_empty_decks.mtgo_utils, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        empty_file = d / "empty.json"
        empty_file.write_text(
            '{"tournament": {"url": "https://example.test/a"}, "decks": []}',
            encoding="utf-8",
        )
        full_file = d / "full.json"
        full_file.write_text(
            '{"tournament": {"url": "https://example.test/b"}, "decks": [{}]}',
            encoding="utf-8",
        )

        queue: Queue[str] = Queue()
        mtgo_empty_decks.find_and_clear_empty_decks(queue, Lock())

        assert queue.qsize() == 1
        assert queue.get() == "https://example.test/a"
        assert not empty_file.exists()
        assert full_file.exists()

    def test_skips_unreadable_files(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mtgo_empty_decks.mtgo_utils, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "corrupt.json").write_text("not json", encoding="utf-8")

        queue: Queue[str] = Queue()
        mtgo_empty_decks.find_and_clear_empty_decks(queue, Lock())

        assert queue.empty()


class TestScrapeTournamentsWithoutDecks:
    def test_wires_producer_and_consumer_threads(self) -> None:
        with (
            patch.object(
                mtgo_empty_decks.driver_utils, "init_driver", return_value=Mock()
            ) as mock_init,
            patch.object(
                mtgo_empty_decks, "find_and_clear_empty_decks"
            ) as mock_producer,
            patch.object(mtgo_empty_decks, "consumer") as mock_consumer,
        ):
            mtgo_empty_decks.scrape_tournaments_without_decks(num_threads=2)

        assert mock_init.call_count == 2
        mock_producer.assert_called_once()
        assert mock_consumer.call_count == 2
