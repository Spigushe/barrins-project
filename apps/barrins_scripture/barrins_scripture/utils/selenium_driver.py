import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from barrins_scripture.utils.mtgo import BASE_URL, MAX_RETRIES, PAGE_LOAD_TIMEOUT

TOURNAMENT_LINKS_SELECTOR = (
    "#decklists > div.site-content > div.container-page-fluid.decklists-page "
    "> ul > li > a"
)


def init_driver() -> webdriver.Chrome:
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # silence TensorFlow logs, if present

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    # "normal" (the default) blocks driver.get() until the browser's `load`
    # event fires, i.e. every subresource (ads, trackers, analytics beacons)
    # has finished — one stuck subresource on a heavy page (e.g. mtgo.com's
    # decklists pages) means `load` never fires and every call times out
    # regardless of how large page_load_timeout is. "eager" returns once the
    # DOM is parsed; the WebDriverWait calls in get_mtgo_tournaments()/
    # scrape_tournament() already wait for the specific selector they need,
    # so this doesn't weaken what we actually check for.
    options.page_load_strategy = "eager"

    # CHROME_BINARY_PATH/CHROMEDRIVER_PATH point at the apt-installed
    # chromium/chromium-driver on the VPS (see
    # ops/my-server/roles/scripture_scraper), so headless Chrome starts from
    # a version-matched local pair with no outbound network call. Left unset
    # for local development: Selenium Manager (bundled since Selenium 4.6)
    # then resolves and downloads a matching Chrome + driver itself.
    chrome_binary_path = os.environ.get("CHROME_BINARY_PATH")
    if chrome_binary_path:
        options.binary_location = chrome_binary_path

    service = Service(
        executable_path=os.environ.get("CHROMEDRIVER_PATH"),
        log_output=os.devnull,
    )

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def get_mtgo_tournaments(
    driver: WebDriver,
    year: int,
    month: int,
    timeout: int = 15,
) -> list[str]:
    tournaments: list[str] = []
    page_load_timeout = PAGE_LOAD_TIMEOUT

    for _ in range(MAX_RETRIES + 1):
        try:
            driver.set_page_load_timeout(page_load_timeout)
            driver.get(BASE_URL + f"{year}/{month:02}")
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, TOURNAMENT_LINKS_SELECTOR)
                )
            )
        except WebDriverException:
            # Broader than TimeoutException on purpose: a hung navigation
            # raises TimeoutException, but a reset/dropped connection (e.g.
            # net::ERR_CONNECTION_RESET) raises the plain base
            # WebDriverException, which previously wasn't caught here and
            # crashed the run instead of retrying like a timeout does.
            timeout += 10
            page_load_timeout += 10
            continue

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for link in soup.select(TOURNAMENT_LINKS_SELECTOR):
            href = str(link.get("href"))
            tournaments.append(
                f"https://www.mtgo.com{href}" if href.startswith("/") else href
            )

        if tournaments:
            break

        timeout += 10
        page_load_timeout += 10

    return tournaments
