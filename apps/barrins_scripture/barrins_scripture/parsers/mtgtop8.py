import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup, Tag

from barrins_scripture.schemas import FORMATS, CardEntry, Deck, Tournament

HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "3600",
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
    ),
}

_MTG_FIRST_RELEASE = datetime(1993, 8, 5).date()
_AI_DISCLAIMER = (
    '<div class="G12" style="margin-bottom:10px;">The following text was '
    "generated with ChatGPT, the results are usually useful, but can "
    "sometimes miss the mark. Use it at your own risk.</div>"
)


def get_tournament_soup(
    tournament_url: str, encoding: str = "iso-8859-1"
) -> BeautifulSoup:
    time.sleep(0.5)  # avoid being rate-limited by the server
    req = requests.get(tournament_url, headers=HEADERS, stream=True, timeout=10)
    req.encoding = encoding
    return BeautifulSoup(req.content, "html.parser", from_encoding=encoding)


def tournament(tournament_url: str, tournament_soup: BeautifulSoup) -> Tournament:
    tournament_format = get_format(tournament_soup)
    if tournament_format == "Unknown Format":
        raise ValueError("Unknown format for tournament")

    return Tournament(
        date=get_date(tournament_soup),
        name=get_name(tournament_soup),
        url=tournament_url,
        format=tournament_format,
        players=get_players_qty(tournament_soup),
    )


def decks(tournament_soup: BeautifulSoup) -> list[Deck]:
    decks_dict: dict[int, Deck] = {}

    top8_tags = tournament_soup.select(
        ".chosen_tr div.S14 a[href^='?e='], .hover_tr div.S14 a[href^='?e=']"
    )
    out_tags = tournament_soup.select("div.S14 input[type='radio']")

    for deck_tag in top8_tags:
        deck_id, deck_obj = get_deck_from_top8(deck_tag)
        decks_dict[deck_id] = deck_obj

    for deck_tag in out_tags:
        deck_id, deck_obj = get_deck_out_top8(deck_tag)
        decks_dict[deck_id] = deck_obj

    return list(decks_dict.values())


def get_date(tournament_soup: BeautifulSoup) -> date:
    meta_arch = tournament_soup.find("div", class_="meta_arch")
    if meta_arch and meta_arch.parent:
        for tag in meta_arch.parent.find_all("div"):
            line = tag.get_text(strip=True)
            date_match = re.search(r"(\d{2}/\d{2}/\d{2})", line)
            if date_match:
                day, month, year_str = date_match.group(1).split("/")
                year = int(year_str)
                if year + 2000 > datetime.now().year:
                    year -= 100
                return datetime(year + 2000, int(month), int(day)).date()

    return _MTG_FIRST_RELEASE


def get_name(tournament_soup: BeautifulSoup) -> str:
    event_title = tournament_soup.find("div", class_="event_title")
    if not event_title:
        return ""

    text = event_title.get_text(strip=True)
    return text.split("@")[0].strip() if "@" in text else text


def get_format(tournament_soup: BeautifulSoup) -> str:
    meta_arch = tournament_soup.find("div", class_="meta_arch")
    if meta_arch:
        meta_arch_text = meta_arch.get_text(strip=True)
        for format_name in FORMATS:
            if format_name in meta_arch_text:
                return format_name

    return "Unknown Format"


def get_players_qty(tournament_soup: BeautifulSoup) -> int:
    meta_arch = tournament_soup.find("div", class_="meta_arch")
    if meta_arch and meta_arch.parent:
        for tag in meta_arch.parent.find_all("div"):
            line = tag.get_text(strip=True)
            if "players" in line.lower():
                players_match = re.search(r"(\d+) players", line)
                if players_match:
                    return int(players_match.group(1))

    return 0


def get_deck_from_top8(deck_tag: Tag) -> tuple[int, Deck]:
    href = str(deck_tag.get("href", ""))
    id_match = re.search(r"d=(\d+)", href)
    if not id_match:
        raise ValueError(f"Deck ID not found in href: {href}")
    deck_id = int(id_match.group(1))

    container = _find_row_container(deck_tag)

    player_name = "Unknown Player"
    player_tag = container.find("a", class_="player")
    if player_tag:
        player_name = player_tag.get_text(strip=True)

    result = 0
    for div in container.find_all("div", class_="S14"):
        text = div.get_text(strip=True)
        result_match = re.match(r"^(\d+)(-\d+)?$", text)
        if result_match:
            result = int(result_match.group(1))
            break

    mainboard, sideboard = get_decklist(deck_id)
    if not mainboard:
        raise ValueError("Mainboard not found")

    return (
        deck_id,
        Deck(
            date=datetime.now().date(),
            player=player_name,
            result=result,
            anchor_uri=f"https://mtgtop8.com/event{href}",
            mainboard=mainboard,
            sideboard=sideboard,
            notes=get_notes(deck_id),
        ),
    )


def _find_row_container(deck_tag: Tag) -> Tag:
    current = deck_tag
    for _ in range(4):
        parent_div = current.find_parent("div")
        if not parent_div:
            raise ValueError("Container block with player info not found.")
        if parent_div.has_attr("class") and (
            "hover_tr" in parent_div["class"] or "chosen_tr" in parent_div["class"]
        ):
            return parent_div
        current = parent_div
    raise ValueError("Container block with player info not found.")


def get_deck_out_top8(deck_tag: Tag) -> tuple[int, Deck]:
    deck_parent = deck_tag.parent
    if not deck_parent:
        raise ValueError("Parent block not found")

    deck_id = int(str(deck_tag["value"]))
    player_name = re.split(" - ", str(deck_tag.contents[0]), maxsplit=1)[1].strip()
    result = int(re.split("#", str(deck_parent["label"]), maxsplit=1)[1])

    mainboard, sideboard = get_decklist(deck_id)
    if not mainboard:
        raise ValueError("Mainboard not found")

    return (
        deck_id,
        Deck(
            date=datetime.now().date(),
            player=player_name,
            result=result,
            anchor_uri="",
            mainboard=mainboard,
            sideboard=sideboard,
            notes=get_notes(deck_id),
        ),
    )


def get_decklist(deck_id: int) -> tuple[list[CardEntry], list[CardEntry]]:
    decklist_url = f"https://mtgtop8.com/mtgo?d={deck_id}"
    decklist_soup = str(get_tournament_soup(decklist_url).prettify())

    if "Sideboard" not in decklist_soup:
        mainboard_soup, sideboard_soup = decklist_soup, ""
    else:
        mainboard_soup, sideboard_soup = decklist_soup.split("Sideboard")

    return get_cardentries(mainboard_soup), get_cardentries(sideboard_soup)


def get_cardentries(decklist: str) -> list[CardEntry]:
    entries: list[CardEntry] = []
    for line in decklist.split("\n"):
        line = line.strip()
        if len(line.split(" ", maxsplit=1)) == 2:
            entries.append(handle_line(line))
    return entries


def handle_line(line: str) -> CardEntry:
    qty_text, name = line.split(" ", maxsplit=1)
    return CardEntry(count=int(qty_text), name=sanitize_cardname(name.strip()))


def sanitize_cardname(card_name: str) -> str:
    card_name = re.sub(r"^A-", "", card_name)  # drop Alchemy "A-" prefix
    return card_name.replace("&amp;", "&")


def get_notes(deck_id: int) -> str | None:
    deck_url = f"https://mtgtop8.com/event?e=1&d={deck_id}&explain_deck=Y"

    response = requests.get(deck_url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    notes_div = soup.find("div", class_="S16")
    if not isinstance(notes_div, Tag):
        return None

    card_span = r"<span[^>]*>.*?<a[^>]*>(.*?)</a>.*?</span>"
    inner_html = notes_div.decode_contents()
    return re.sub(card_span, r"\1", inner_html, flags=re.DOTALL).replace(
        _AI_DISCLAIMER, ""
    )
