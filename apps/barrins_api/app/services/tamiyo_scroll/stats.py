"""Derived calculations for the Tamiyo Scroll domain — winrate, conversion, archetypes.

Pure functions: never touch the database, operate on sequences of
already-loaded ORM objects. All business logic lives here rather than
in the routes or on the frontend (constitution §4.1/§4.2).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypedDict
from uuid import UUID

from app.models.tamiyo_scroll import ArchetypeCategory, GameResult


class GameLike(Protocol):
    """Structural type satisfied by `TSMatchGame` and
    `sharing_merge.EffectiveGame` — one played game within a `MatchLike`
    (#123/#124, replaces the old flat `game1`/`game2`/`game3`/`on_play`
    match-level fields)."""

    @property
    def game_number(self) -> int: ...
    @property
    def on_play(self) -> bool | None: ...
    @property
    def result(self) -> GameResult | None: ...
    @property
    def player_mulligans(self) -> int | None: ...
    @property
    def opponent_mulligans(self) -> int | None: ...
    @property
    def player_misplays(self) -> int | None: ...
    @property
    def opponent_misplays(self) -> int | None: ...


class MatchLike(Protocol):
    """Structural type satisfied by `TSMatch` and `sharing_merge.EffectiveMatch`.

    Read-only (`@property`) so a frozen dataclass structurally satisfies
    it too — a plain attribute annotation implies a setter, which a
    frozen dataclass doesn't have.
    """

    @property
    def opponent_deck_id(self) -> UUID: ...
    @property
    def decklist_version_id(self) -> UUID | None: ...
    @property
    def games(self) -> Sequence[GameLike]: ...
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
    @property
    def archived_at(self) -> datetime | None: ...


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
    """Count wins/losses/draws across every match's games.

    Winrate is computed at the game level, not the match level — cf.
    docs/tamiyo_scroll_tracker/00_plan_general.md, Option C.

    `on_play` now filters per *game* (#123/#124's per-game `on_play`), not
    per match — a historical (pre-#123/#124) game's `on_play` is `NULL`
    for game 2/3 (only game 1 could be backfilled from the old
    match-level column, see `TSMatchGame`'s docstring), so those games
    simply never match either `on_play=True` or `on_play=False` here,
    same as any other "not entered" field (D8).
    """
    wins = losses = draws = 0
    for match in matches:
        for game in match.games:
            if on_play is not None and game.on_play != on_play:
                continue
            if game.result == GameResult.win:
                wins += 1
            elif game.result == GameResult.loss:
                losses += 1
            elif game.result == GameResult.draw:
                draws += 1
    return wins, losses, draws


def _average(values: Sequence[int | None]) -> float | None:
    """Mean of the non-`None` values, or `None` if there are none.

    `None` ("not entered") is excluded, never treated as `0` — D8.
    """
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 2)


class HandSizeAndMisplayAverages(TypedDict):
    avg_hand_size: float | None
    avg_player_misplays: float | None
    avg_opponent_misplays: float | None


def compute_hand_size_and_misplay_averages(
    matches: Sequence[MatchLike],
) -> HandSizeAndMisplayAverages:
    """Derived period metrics for #123 (`avg_hand_size`) and #124
    (`avg_*_misplays`) — D4/D5/D6.

    London mulligan (Duel Commander, D4): `hand_size = 7 - mulligans`, so
    `avg_hand_size = 7 - avg(player_mulligans)`. Only the player's own
    mulligans feed hand size (it's the player's own hand); misplays are
    tracked, and averaged, per side.
    """
    games = [game for match in matches for game in match.games]
    avg_player_mulligans = _average([g.player_mulligans for g in games])
    avg_hand_size = (
        None if avg_player_mulligans is None else round(7 - avg_player_mulligans, 2)
    )
    return {
        "avg_hand_size": avg_hand_size,
        "avg_player_misplays": _average([g.player_misplays for g in games]),
        "avg_opponent_misplays": _average([g.opponent_misplays for g in games]),
    }


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


@dataclass
class PeriodStats:
    """Winrate/matchup summary of a reported period vs. its baseline.

    Shared shape between two distinct "current period" concepts (S5):
    a specific `TSSession` (its own explicitly-logged matches) and a
    rolling window like "the last 30 days" (matches selected by
    timestamp instead). Both compute the same numbers the same way —
    only *which* matches count as "current" vs. "baseline" differs
    between the two callers.
    """

    current_matches: Sequence[MatchLike]
    baseline_matches: Sequence[MatchLike]
    current_archetype: list[ArchetypeSummary]
    baseline_archetype: list[ArchetypeSummary]
    current_matchup_rows: list[MatchupRow]
    current_avg: float | None
    baseline_matchup_rows: list[MatchupRow]
    baseline_avg: float | None
    current_wins: int
    current_losses: int
    baseline_wins: int
    baseline_losses: int
    # #123/#124 (D5/D6) — derived period metrics, `None` when the period
    # has no game with a non-null value to average (D8).
    current_avg_hand_size: float | None
    current_avg_player_misplays: float | None
    current_avg_opponent_misplays: float | None
    baseline_avg_hand_size: float | None
    baseline_avg_player_misplays: float | None
    baseline_avg_opponent_misplays: float | None


def compute_period_stats(
    meta_decks: Sequence[MetaDeckLike],
    current_matches: Sequence[MatchLike],
    baseline_matches: Sequence[MatchLike],
    readonly_meta_deck_ids: frozenset[UUID] = frozenset(),
) -> PeriodStats:
    """Compute every number needed for a period-vs-baseline comparison.

    `meta_decks` should be the caller's *entire* roster, archived decks
    included — this function does its own archived filtering rather than
    receiving an already-filtered list. Matches against an archived
    opponent are dropped entirely (not just hidden from a table): the
    deck's own name/category no longer exists to attribute them to,
    which otherwise surfaced as a bare "?" row (archived decks used to
    be filtered by the caller before this function ever saw the match
    list, silently orphaning those matches instead of excluding them).

    No parallel calculation path (Constitution §4.2): reuses
    `compute_archetype_summary`/`compute_matchup_summary`/`_tally_games`.
    `readonly_meta_deck_ids` passes through unchanged — same meaning as
    those functions' own parameter (a merged-in sharer's roster entry,
    `sharing_merge.MergedView.readonly_meta_deck_ids`).
    """
    active_meta_decks = [d for d in meta_decks if d.archived_at is None]
    active_deck_ids = {d.id for d in active_meta_decks}
    current_matches = [
        m for m in current_matches if m.opponent_deck_id in active_deck_ids
    ]
    baseline_matches = [
        m for m in baseline_matches if m.opponent_deck_id in active_deck_ids
    ]
    meta_decks_by_id = {d.id: d for d in active_meta_decks}

    current_archetype = compute_archetype_summary(
        active_meta_decks, current_matches, readonly_meta_deck_ids
    )
    baseline_archetype = compute_archetype_summary(
        active_meta_decks, baseline_matches, readonly_meta_deck_ids
    )
    current_matchup_rows, current_avg = compute_matchup_summary(
        current_matches, meta_decks_by_id, readonly_meta_deck_ids
    )
    baseline_matchup_rows, baseline_avg = compute_matchup_summary(
        baseline_matches, meta_decks_by_id, readonly_meta_deck_ids
    )
    current_wins, current_losses, _ = _tally_games(current_matches)
    baseline_wins, baseline_losses, _ = _tally_games(baseline_matches)
    current_averages = compute_hand_size_and_misplay_averages(current_matches)
    baseline_averages = compute_hand_size_and_misplay_averages(baseline_matches)

    return PeriodStats(
        current_matches,
        baseline_matches,
        current_archetype,
        baseline_archetype,
        current_matchup_rows,
        current_avg,
        baseline_matchup_rows,
        baseline_avg,
        current_wins,
        current_losses,
        baseline_wins,
        baseline_losses,
        current_averages["avg_hand_size"],
        current_averages["avg_player_misplays"],
        current_averages["avg_opponent_misplays"],
        baseline_averages["avg_hand_size"],
        baseline_averages["avg_player_misplays"],
        baseline_averages["avg_opponent_misplays"],
    )
