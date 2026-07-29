import re
from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag

from barrins_scripture.schemas import (
    FORMATS,
    CardEntry,
    Deck,
    Match,
    Round,
    Standing,
    Tournament,
)
from barrins_scripture.utils.date_parsing import parse_date
from barrins_scripture.utils.swiss_tournament import get_num_rounds


def tournament(soup: BeautifulSoup, tournament_url: str) -> Tournament | None:
    tournament_date = get_date(soup)
    if not tournament_date:
        return None

    return Tournament(
        date=tournament_date,
        name=get_name(soup),
        url=tournament_url,
        format=get_format(soup),
        players=get_player_qty(soup),
    )


def decks(soup: BeautifulSoup, tournament_url: str) -> list[Deck]:
    return [get_deck(deck, tournament_url) for deck in soup.select("section.decklist")]


def rounds(soup: BeautifulSoup) -> list[Round]:
    return [
        get_round(round_block) for round_block in soup.select(".decklist-bracket-round")
    ]


def standings(soup: BeautifulSoup) -> list[Standing]:
    standings_table = soup.select_one("#decklistStandings table.hidden-xs tbody")
    if not standings_table:
        return []

    nb_rounds = get_num_rounds(get_player_qty(soup))
    return [
        get_standing(row, nb_rounds)
        for row in standings_table.find_all("tr")
        if row and row.find_all("td")  # skip empty rows
    ]


def get_date(soup: BeautifulSoup) -> date | None:
    date_element = soup.select_one("p.decklist-posted-on")
    if not date_element:
        return None

    date_text = date_element.get_text(strip=True).replace("Posted on ", "")
    if not date_text:
        return None

    parsed_date = parse_date(date_text)
    return parsed_date - timedelta(days=1)


def get_name(soup: BeautifulSoup) -> str:
    title_element = soup.select_one("h1.decklist-title")
    return title_element.get_text(strip=True) if title_element else "Unknown Tournament"


def get_format(soup: BeautifulSoup) -> str:
    parsed_name = get_name(soup)
    for format_item in FORMATS:
        if format_item in parsed_name:
            return format_item
    return "Unknown Format"


def get_player_qty(soup: BeautifulSoup) -> int:
    players_element = soup.select_one("h2.decklist-player-count")
    if not players_element:
        return 0

    players_text = players_element.get_text(strip=True)
    match = re.search(r"(\d+)", players_text)
    return int(match.group(1)) if match else 0


def get_deck(deck_section: Tag, url: str) -> Deck:
    player_tag = deck_section.find("p", class_="decklist-player")
    player_info = player_tag.get_text(strip=True) if player_tag else ""
    player_name, position_text = player_info.rsplit(" (", 1)

    try:
        position_number: int | None = int(position_text.split("Place")[0].strip()[:-2])
    except ValueError:
        position_number = None

    date_tag = deck_section.find("p", class_="decklist-date")
    event_date = parse_date(date_tag.get_text(strip=True) if date_tag else "08/05/1993")

    mainboard = _get_cards(deck_section, ".decklist-sort-type .decklist-category")

    sideboard: list[CardEntry] | None = None
    sideboard_tag = deck_section.select_one(".decklist-sideboard")
    if sideboard_tag:
        sideboard = _get_cards(sideboard_tag)

    return Deck(
        date=event_date,
        player=player_name,
        result=position_number,
        anchor_uri=f"{url}#{deck_section['id']}",
        mainboard=mainboard,
        sideboard=sideboard,
    )


def _get_cards(container: Tag, category_selector: str | None = None) -> list[CardEntry]:
    scopes = container.select(category_selector) if category_selector else [container]
    entries: list[CardEntry] = []
    for scope in scopes:
        for card_tag in scope.select(".decklist-category-card"):
            card_line = card_tag.get_text(separator=" ", strip=True)
            match = re.match(r"(\d+)[xX]?\s+(.*)", card_line)
            if match:
                entries.append(
                    CardEntry(count=int(match.group(1)), name=match.group(2))
                )
    return entries


def get_round(round_block: Tag) -> Round:
    round_tag = round_block.select_one(".decklist-bracket-round-title")
    round_name = round_tag.get_text(strip=True) if round_tag else "Unknown Round"

    return Round(
        round_name=round_name,
        matches=[
            get_match(match_wrapper)
            for match_wrapper in round_block.select(".decklist-bracket-match-wrapper")
        ],
    )


def get_match(match_wrapper: Tag) -> Match:
    players = match_wrapper.select(".decklist-bracket-player")

    if len(players) != 2:
        return Match(
            player_1="Unknown Player", player_2="Unknown Player", result="0-0-0"
        )

    winner_text = players[0].get_text(strip=True)
    loser_text = players[1].get_text(strip=True)
    if "  " in winner_text:
        winner_name, score = winner_text.split("  ", 1)
        winner_name = winner_name.strip()
        score = score.strip()
    else:
        winner_name = winner_text
        score = ""

    return Match(player_1=winner_name, player_2=loser_text, result=score)


def get_standing(row: Tag, nb_rounds: int) -> Standing:
    cols = row.find_all("td")
    if len(cols) != 6:
        raise ValueError("Invalid standing row")

    points = int(cols[2].get_text(strip=True))
    wins = points // 3
    draws = points % 3
    losses = nb_rounds - wins - draws

    return Standing(
        rank=int(cols[0].get_text(strip=True)),
        player=cols[1].get_text(strip=True),
        points=points,
        wins=wins,
        losses=losses,
        draws=draws,
        omwp=float(cols[3].get_text(strip=True).rstrip("%")) / 100,
        gwp=float(cols[4].get_text(strip=True).rstrip("%")) / 100,
        ogwp=float(cols[5].get_text(strip=True).rstrip("%")) / 100,
    )
