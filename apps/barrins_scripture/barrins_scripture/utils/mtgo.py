import json
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from barrins_scripture.parsers import mtgo as parser
from barrins_scripture.schemas import MTGScrape

BASE_URL = "https://www.mtgo.com/decklists/"
BASE_PATH = Path(__file__).resolve().parent.parent.parent / "scraped" / "mtgo.com"
MAX_RETRIES = 3
DEFAULT_RENDER_TIMEOUT = 15  # seconds to wait for the decklist page to render

# Hard ceiling on driver.get() itself, distinct from the WebDriverWait render
# timeout above. Without this, a hung navigation (dead network, chromedriver
# wedged) blocks on the client's raw socket read timeout (~120s) and raises
# urllib3.exceptions.ReadTimeoutError instead of a catchable Selenium
# TimeoutException, killing the calling thread outright. Grown alongside the
# render-wait timeout on each retry in get_mtgo_tournaments()/
# scrape_tournament() — a fixed ceiling that never scales leaves later
# retries no better off than the first if the VPS's link to mtgo.com is
# just slow that day, not hung.
PAGE_LOAD_TIMEOUT = 45

_URL_PREFIX_LEN = len("https://www.mtgo.com/decklist/")


def we_should_scrape_it(tournament_url: str, max_days_to_be_recent: int = 3) -> bool:
    filename = sanitize_filename(tournament_url[_URL_PREFIX_LEN:]) + ".json"

    already_scraped = False
    recent_scrape = False
    for path in BASE_PATH.rglob(filename):
        if not path.is_file():
            continue
        already_scraped = True
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", tournament_url)
        if match:
            year, month, day = map(int, match.groups())
            age = datetime.now() - datetime(year, month, day)
            recent_scrape = age.days < max_days_to_be_recent

    return not (already_scraped and not recent_scrape)


def sanitize_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


def scrape_tournament(
    driver: WebDriver,
    url: str,
    timeout: int = DEFAULT_RENDER_TIMEOUT,
    page_load_timeout: int = PAGE_LOAD_TIMEOUT,
) -> MTGScrape | None:
    try:
        driver.set_page_load_timeout(page_load_timeout)
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.decklist-posted-on"))
        )
    except TimeoutException:
        return None

    soup = BeautifulSoup(driver.page_source, "html.parser")
    tournament = parser.tournament(soup, url)
    if not tournament:
        return None

    return MTGScrape(
        tournament=tournament,
        decks=parser.decks(soup, url),
        rounds=parser.rounds(soup),
        standings=parser.standings(soup),
    )


def save_tournament_scrape(scrape: MTGScrape) -> Path:
    tournament_url = scrape.tournament.url
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", tournament_url)
    if match:
        year, month, day = match.groups()
    else:
        tournament_date = scrape.tournament.date
        year = str(tournament_date.year)
        month = f"{tournament_date.month:02}"
        day = f"{tournament_date.day:02}"

    dir_path = BASE_PATH / year / month / day
    dir_path.mkdir(parents=True, exist_ok=True)

    filename = sanitize_filename(tournament_url[_URL_PREFIX_LEN:]) + ".json"
    file_path = dir_path / filename

    file_path.write_text(
        json.dumps(scrape.model_dump(mode="json"), ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return file_path
