import re
from pathlib import Path

from bs4 import BeautifulSoup

from barrins_scripture.parsers import mtgtop8 as parser
from barrins_scripture.parsers.mtgtop8 import get_tournament_soup as get_tournament_soup
from barrins_scripture.schemas import MTGScrape

BASE_PATH = Path(__file__).resolve().parent.parent.parent / "scraped" / "mtgtop8.com"


def get_max_id_scraped() -> int:
    max_id = 0
    for file in BASE_PATH.rglob("*.json"):
        try:
            max_id = max(max_id, get_id_from_filepath(file))
        except ValueError:
            continue
    return max_id


def get_id_from_filepath(filepath: Path) -> int:
    return int(filepath.stem.split("_")[0])


def get_tournament_url(tournament_id: int) -> str:
    return f"https://mtgtop8.com/event?e={tournament_id}"


def we_should_scrape_it(tournament_url: str) -> bool:
    tournament_query = tournament_url.split("e=")[1]
    if "&" in tournament_query:
        tournament_query = tournament_query.split("&")[0]
    tournament_id = int(tournament_query)

    # rglob, not glob: archived files live nested under BASE_PATH/YYYY/MM/DD/,
    # never directly in BASE_PATH itself (see save_tournament_scrape below) —
    # a non-recursive glob would never match anything, making this dedup
    # check a permanent no-op.
    scraped_ids: set[int] = set()
    for f in BASE_PATH.rglob("*.json"):
        if not f.is_file():
            continue
        try:
            scraped_ids.add(get_id_from_filepath(f))
        except ValueError:
            continue
    return tournament_id not in scraped_ids


def scrape_tournament(url: str, soup: BeautifulSoup) -> MTGScrape | None:
    tournament = parser.tournament(url, soup)
    if not tournament:
        return None

    decks = parser.decks(soup)
    for deck in decks:
        deck.date = tournament.date

    return MTGScrape(
        tournament=tournament,
        decks=decks,
        rounds=[],  # mtgtop8 doesn't provide round/standings data
        standings=[],
    )


def save_tournament_scrape(scrape: MTGScrape) -> Path:
    tournament_id = scrape.tournament.url.split("e=")[1]
    if "&" in tournament_id:
        tournament_id = tournament_id.split("&")[0]

    filename = f"{tournament_id}_{scrape.tournament.format}_{scrape.tournament.name}"
    filename = f"{sanitize_string(filename)}.json"

    tournament_date = scrape.tournament.date
    dir_path = (
        BASE_PATH
        / str(tournament_date.year)
        / f"{tournament_date.month:02}"
        / f"{tournament_date.day:02}"
    )
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename

    file_path.write_text(
        scrape.model_dump_json(indent=4),
        encoding="utf-8",
    )
    return file_path


def sanitize_string(string: str) -> str:
    string = string.lower()
    string = re.sub(r"[^a-z0-9_.]+", "-", string)
    string = re.sub(r"-+", "-", string)
    return string.strip("-")
