from unittest.mock import Mock, patch

from selenium.common.exceptions import TimeoutException

from barrins_scripture.utils import selenium_driver


class TestInitDriver:
    def test_builds_a_headless_chrome_driver(self) -> None:
        with patch.object(selenium_driver.webdriver, "Chrome") as mock_chrome:
            selenium_driver.init_driver()

        mock_chrome.assert_called_once()
        _, kwargs = mock_chrome.call_args
        assert "--headless=new" in kwargs["options"].arguments

    def test_sets_a_page_load_timeout(self) -> None:
        with patch.object(selenium_driver.webdriver, "Chrome"):
            driver = selenium_driver.init_driver()

        driver.set_page_load_timeout.assert_called_once_with(
            selenium_driver.PAGE_LOAD_TIMEOUT
        )


class TestGetMtgoTournaments:
    def test_returns_absolute_and_already_absolute_links(self) -> None:
        driver = Mock()
        driver.page_source = """
        <div id="decklists">
          <div class="site-content">
            <div class="container-page-fluid decklists-page">
              <ul>
                <li><a href="/decklist/duel-commander-league-2026-06-2710716">A</a></li>
                <li><a href="https://www.mtgo.com/decklist/other-12345">B</a></li>
              </ul>
            </div>
          </div>
        </div>
        """
        with patch.object(selenium_driver, "WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True
            links = selenium_driver.get_mtgo_tournaments(driver, 2026, 6)

        assert links == [
            "https://www.mtgo.com/decklist/duel-commander-league-2026-06-2710716",
            "https://www.mtgo.com/decklist/other-12345",
        ]
        driver.get.assert_called_with(selenium_driver.BASE_URL + "2026/06")

    def test_retries_on_timeout_then_gives_up(self) -> None:
        driver = Mock()
        driver.page_source = "<html></html>"
        with patch.object(selenium_driver, "WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()
            links = selenium_driver.get_mtgo_tournaments(driver, 2026, 6, timeout=1)

        assert links == []
        assert driver.get.call_count == selenium_driver.MAX_RETRIES + 1

    def test_retries_when_driver_get_itself_times_out(self) -> None:
        # driver.get() raises TimeoutException when set_page_load_timeout is
        # exceeded (a hung navigation), distinct from WebDriverWait timing out
        # on a page that loaded but never rendered the expected element.
        driver = Mock()
        driver.get.side_effect = TimeoutException()
        links = selenium_driver.get_mtgo_tournaments(driver, 2026, 6, timeout=1)

        assert links == []
        assert driver.get.call_count == selenium_driver.MAX_RETRIES + 1
