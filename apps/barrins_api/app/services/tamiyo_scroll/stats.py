"""Derived calculations for the Tamiyo Scroll domain — winrate, conversion, archetypes.

Pure functions: never touch the database, operate on sequences of
already-loaded ORM objects. All business logic lives here rather than
in the routes or on the frontend (constitution §4.1/§4.2).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Protocol, TypedDict
from uuid import UUID

from app.models.tamiyo_scroll import ArchetypeCategory, GameResult


class MatchLike(Protocol):
    """Structural type satisfied by `TSMatch` and `sharing_merge.EffectiveMatch`.

    Read-only (`@property`) so a frozen dataclass structurally satisfies
    it too — a plain attribute annotation implies a setter, which a
    frozen dataclass doesn't have.
    """

    @property
    def opponent_deck_id(self) -> UUID: ...
    @property
    def on_play(self) -> bool: ...
    @property
    def game1(self) -> GameResult | None: ...
    @property
    def game2(self) -> GameResult | None: ...
    @property
    def game3(self) -> GameResult | None: ...
    @property
    def is_readonly(self) -> bool: ...


class MetaDeckLike(Protocol):
    """Structural type satisfied by `TSMetaDeck` and `EffectiveMetaDeck`."""

    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...
    @property
    def category(self) -> ArchetypeCategory: ...


class DeckWinrate(TypedDict):
    id: UUID
    name: str
    winrate: float | None
    is_readonly: bool
    has_shared_data: bool


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
    is_readonly: bool
    has_shared_data: bool


def _tally_games(
    matches: Sequence[MatchLike], *, on_play: bool | None = None
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
    meta_decks: Sequence[MetaDeckLike],
    matches: Sequence[MatchLike],
    readonly_meta_deck_ids: frozenset[UUID] = frozenset(),
) -> list[ArchetypeSummary]:
    """Average winrate per archetype + individual winrate of the group's decks.

    Decks with no logged game are ignored in the average calculation
    (README: "average of winrates ... ignoring decks with no data"),
    but remain listed with `winrate=None`. All known categories are
    returned, even empty ones, for a stable display grid.

    `readonly_meta_deck_ids` flags decks merged in read-only from a
    sharer with no matching roster entry of the viewer's own (see
    `sharing_merge`) — informational only, doesn't affect the calculation.
    """
    matches_by_opponent: dict[UUID, list[MatchLike]] = defaultdict(list)
    for match in matches:
        matches_by_opponent[match.opponent_deck_id].append(match)

    decks_by_category: dict[ArchetypeCategory, list[MetaDeckLike]] = defaultdict(list)
    for deck in meta_decks:
        decks_by_category[deck.category].append(deck)

    summaries: list[ArchetypeSummary] = []
    for category in ArchetypeCategory:
        deck_winrates: list[DeckWinrate] = []
        for deck in decks_by_category.get(category, []):
            deck_matches = matches_by_opponent.get(deck.id, [])
            wins, losses, _ = _tally_games(deck_matches)
            deck_is_readonly = deck.id in readonly_meta_deck_ids
            deck_winrates.append(
                {
                    "id": deck.id,
                    "name": deck.name,
                    "winrate": _winrate(wins, losses),
                    "is_readonly": deck_is_readonly,
                    "has_shared_data": not deck_is_readonly
                    and any(m.is_readonly for m in deck_matches),
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
    matches: Sequence[MatchLike],
    meta_decks_by_id: Mapping[UUID, MetaDeckLike],
    readonly_meta_deck_ids: frozenset[UUID] = frozenset(),
) -> tuple[list[MatchupRow], float | None]:
    """Matchup summary: one row per opponent deck encountered + overall average.

    The overall average is computed across all games (not the average of
    per-matchup averages), consistent with a calculation "automatically
    derived from the match log".
    """
    matches_by_opponent: dict[UUID, list[MatchLike]] = defaultdict(list)
    for match in matches:
        matches_by_opponent[match.opponent_deck_id].append(match)

    rows: list[MatchupRow] = []
    for opponent_id, opponent_matches in matches_by_opponent.items():
        wins, losses, _ = _tally_games(opponent_matches)
        otp_wins, otp_losses, _ = _tally_games(opponent_matches, on_play=True)
        otd_wins, otd_losses, _ = _tally_games(opponent_matches, on_play=False)
        deck = meta_decks_by_id.get(opponent_id)
        row_is_readonly = opponent_id in readonly_meta_deck_ids
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
                "is_readonly": row_is_readonly,
                "has_shared_data": not row_is_readonly
                and any(m.is_readonly for m in opponent_matches),
            }
        )
    rows.sort(key=lambda r: r["opponent_deck_name"].lower())

    total_wins, total_losses, _ = _tally_games(matches)
    average_winrate = _winrate(total_wins, total_losses)
    return rows, average_winrate
