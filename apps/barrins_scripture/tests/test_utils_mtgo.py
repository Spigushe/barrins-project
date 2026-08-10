import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from selenium.common.exceptions import TimeoutException

from barrins_scripture.utils import mtgo


class TestSanitizeFilename:
    def test_lowercases_and_dashes(self) -> None:
        assert mtgo.sanitize_filename("Duel Commander League 2026-06-27") == (
            "duel-commander-league-2026-06-27"
        )

    def test_collapses_repeated_separators(self) -> None:
        assert mtgo.sanitize_filename("a___b---c") == "a-b-c"

    def test_strips_leading_and_trailing_dashes(self) -> None:
        assert mtgo.sanitize_filename("--hello--") == "hello"


class TestWeShouldScrapeIt:
    def test_true_when_never_scraped(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mtgo, "BASE_PATH", tmp_path)
        url = "https://www.mtgo.com/decklist/duel-commander-league-2026-06-2710716"
        assert mtgo.we_should_scrape_it(url) is True

    def test_false_when_already_scraped_and_old(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgo, "BASE_PATH", tmp_path)
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        url = f"https://www.mtgo.com/decklist/duel-commander-league-{old_date}10716"
        filename = mtgo.sanitize_filename(url[mtgo._URL_PREFIX_LEN :]) + ".json"
        (tmp_path / filename).write_text("{}", encoding="utf-8")

        assert mtgo.we_should_scrape_it(url, max_days_to_be_recent=3) is False

    def test_true_when_already_scraped_but_recent(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgo, "BASE_PATH", tmp_path)
        recent_date = datetime.now().strftime("%Y-%m-%d")
        url = f"https://www.mtgo.com/decklist/duel-commander-league-{recent_date}10716"
        filename = mtgo.sanitize_filename(url[mtgo._URL_PREFIX_LEN :]) + ".json"
        (tmp_path / filename).write_text("{}", encoding="utf-8")

        assert mtgo.we_should_scrape_it(url, max_days_to_be_recent=3) is True


class TestScrapeTournament:
    def test_returns_none_on_render_timeout(self) -> None:
        driver = Mock()
        with patch.object(mtgo, "WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()
            result = mtgo.scrape_tournament(driver, "https://example.test", timeout=1)
        assert result is None
        driver.get.assert_called_once_with("https://example.test")

    def test_returns_none_when_driver_get_itself_times_out(self) -> None:
        # driver.get() raises TimeoutException when set_page_load_timeout is
        # exceeded (a hung navigation), distinct from WebDriverWait timing out
        # on a page that loaded but never rendered the expected element.
        driver = Mock()
        driver.get.side_effect = TimeoutException()
        result = mtgo.scrape_tournament(driver, "https://example.test", timeout=1)
        assert result is None

    def test_returns_none_when_tournament_unparseable(self) -> None:
        driver = Mock()
        driver.page_source = "<html><h1 class='decklist-title'>No Date</h1></html>"
        with patch.object(mtgo, "WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = mtgo.scrape_tournament(driver, "https://example.test")
        assert result is None

    def test_returns_a_full_scrape_on_success(self) -> None:
        driver = Mock()
        driver.page_source = """
        <h1 class="decklist-title">Duel Commander League</h1>
        <p class="decklist-posted-on">Posted on June 27, 2026</p>
        """
        with patch.object(mtgo, "WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = mtgo.scrape_tournament(driver, "https://example.test")
        assert result is not None
        assert result.tournament.name == "Duel Commander League"
        assert result.decks == []
        assert result.rounds == []
        assert result.standings == []


class TestSaveTournamentScrape:
    def _make_scrape(self, url: str):
        from barrins_scripture.schemas import MTGScrape, Tournament

        return MTGScrape(
            tournament=Tournament(
                date=datetime(2026, 6, 26).date(),
                name="Duel Commander League",
                url=url,
                format="Duel Commander",
                players=0,
            )
        )

    def test_writes_json_under_a_date_path_parsed_from_the_url(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgo, "BASE_PATH", tmp_path)
        url = "https://www.mtgo.com/decklist/duel-commander-league-2026-06-2710716"
        scrape = self._make_scrape(url)

        file_path = mtgo.save_tournament_scrape(scrape)

        assert (
            file_path
            == tmp_path
            / "2026"
            / "06"
            / "27"
            / "duel-commander-league-2026-06-2710716.json"
        )
        assert file_path.is_file()
        saved = json.loads(file_path.read_text(encoding="utf-8"))
        assert saved["tournament"]["name"] == "Duel Commander League"

    def test_falls_back_to_tournament_date_without_a_url_date(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgo, "BASE_PATH", tmp_path)
        url = "https://www.mtgo.com/decklist/no-date-in-this-slug"
        scrape = self._make_scrape(url)

        file_path = mtgo.save_tournament_scrape(scrape)

        assert file_path.parent == tmp_path / "2026" / "06" / "26"
