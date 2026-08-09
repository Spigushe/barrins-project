import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from barrins_scripture.utils.mtgo import BASE_URL, MAX_RETRIES

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

    return webdriver.Chrome(service=service, options=options)


def get_mtgo_tournaments(
    driver: WebDriver,
    year: int,
    month: int,
    timeout: int = 15,
) -> list[str]:
    tournaments: list[str] = []

    for _ in range(MAX_RETRIES + 1):
        driver.get(BASE_URL + f"{year}/{month:02}")

        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, TOURNAMENT_LINKS_SELECTOR)
                )
            )
        except TimeoutException:
            timeout += 10
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

    return tournaments
