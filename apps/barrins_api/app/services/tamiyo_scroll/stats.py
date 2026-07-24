"""Derived calculations for the Tamiyo Scroll domain — winrate, conversion, archetypes.

Pure functions: never touch the database, operate on sequences of
already-loaded ORM objects. All business logic lives here rather than
in the routes or on the frontend (constitution §4.1/§4.2).
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import TypedDict
from uuid import UUID

from app.models.tamiyo_scroll import ArchetypeCategory, GameResult, TSMatch, TSMetaDeck


class DeckWinrate(TypedDict):
    id: UUID
    name: str
    winrate: float | None


class ArchetypeSummary(TypedDict):
    category: ArchetypeCategory
    average_winrate: float | None
    decks: list[DeckWinrate]


class MatchupRow(TypedDict):
    opponent_deck_id: UUID
    opponent_deck_name: str
    winrate_global: float | None
    winrate_otp: float | None
    winrate_otd: float | None
    ratio_otp: str
    ratio_otd: str
    match_count: int


def _tally_games(
    matches: Sequence[TSMatch], *, on_play: bool | None = None
) -> tuple[int, int, int]:
    """Count wins/losses/draws across games (game1/game2/game3).

    Winrate is computed at the game level, not the match level — cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option C.
    """
    wins = losses = draws = 0
    for match in matches:
        if on_play is not None and match.on_play != on_play:
            continue
        for game in (match.game1, match.game2, match.game3):
            if game == GameResult.win:
                wins += 1
            elif game == GameResult.loss:
                losses += 1
            elif game == GameResult.draw:
                draws += 1
    return wins, losses, draws


def _winrate(wins: int, losses: int) -> float | None:
    """Winrate in % (draws excluded); None if no decisive game."""
    decisive = wins + losses
    if decisive == 0:
        return None
    return round(wins / decisive * 100, 2)


def _ratio(wins: int, losses: int) -> str:
    return f"{wins}-{losses}"


def compute_archetype_summary(
    meta_decks: Sequence[TSMetaDeck], matches: Sequence[TSMatch]
) -> list[ArchetypeSummary]:
    """Average winrate per archetype + individual winrate of the group's decks.

    Decks with no logged game are ignored in the average calculation
    (README: "average of winrates ... ignoring decks with no data"),
    but remain listed with `winrate=None`. All known categories are
    returned, even empty ones, for a stable display grid.
    """
    matches_by_opponent: dict[UUID, list[TSMatch]] = defaultdict(list)
    for match in matches:
        matches_by_opponent[match.opponent_deck_id].append(match)

    decks_by_category: dict[ArchetypeCategory, list[TSMetaDeck]] = defaultdict(list)
    for deck in meta_decks:
        decks_by_category[deck.category].append(deck)

    summaries: list[ArchetypeSummary] = []
    for category in ArchetypeCategory:
        deck_winrates: list[DeckWinrate] = []
        for deck in decks_by_category.get(category, []):
            wins, losses, _ = _tally_games(matches_by_opponent.get(deck.id, []))
            deck_winrates.append(
                {
                    "id": deck.id,
                    "name": deck.name,
                    "winrate": _winrate(wins, losses),
                }
            )
        deck_winrates.sort(key=lambda d: d["name"].lower())

        rated = [d["winrate"] for d in deck_winrates if d["winrate"] is not None]
        average = round(sum(rated) / len(rated), 2) if rated else None

        summaries.append(
            {
                "category": category,
                "average_winrate": average,
                "decks": deck_winrates,
            }
        )
    return summaries


def compute_matchup_summary(
    matches: Sequence[TSMatch], meta_decks_by_id: dict[UUID, TSMetaDeck]
) -> tuple[list[MatchupRow], float | None]:
    """Matchup summary: one row per opponent deck encountered + overall average.

    The overall average is computed across all games (not the average of
    per-matchup averages), consistent with a calculation "automatically
    derived from the match log".
    """
    matches_by_opponent: dict[UUID, list[TSMatch]] = defaultdict(list)
    for match in matches:
        matches_by_opponent[match.opponent_deck_id].append(match)

    rows: list[MatchupRow] = []
    for opponent_id, opponent_matches in matches_by_opponent.items():
        wins, losses, _ = _tally_games(opponent_matches)
        otp_wins, otp_losses, _ = _tally_games(opponent_matches, on_play=True)
        otd_wins, otd_losses, _ = _tally_games(opponent_matches, on_play=False)
        deck = meta_decks_by_id.get(opponent_id)
        rows.append(
            {
                "opponent_deck_id": opponent_id,
                "opponent_deck_name": deck.name if deck is not None else "?",
                "winrate_global": _winrate(wins, losses),
                "winrate_otp": _winrate(otp_wins, otp_losses),
                "winrate_otd": _winrate(otd_wins, otd_losses),
                "ratio_otp": _ratio(otp_wins, otp_losses),
                "ratio_otd": _ratio(otd_wins, otd_losses),
                "match_count": len(opponent_matches),
            }
        )
    rows.sort(key=lambda r: r["opponent_deck_name"].lower())

    total_wins, total_losses, _ = _tally_games(matches)
    average_winrate = _winrate(total_wins, total_losses)
    return rows, average_winrate
