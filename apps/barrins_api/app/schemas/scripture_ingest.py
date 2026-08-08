"""Request/response contracts for `POST /internal/scripture/ingest` (T3).

The request body mirrors `barrins_scripture.schemas.scraped_object.MTGScrape`
(`apps/barrins_scripture/barrins_scripture/schemas/`) field-for-field — it
*is* the JSON archive file's own shape (`save_tournament_scrape` writes
`MTGScrape.model_dump_json()` verbatim) — plus a `source` field the
archive's directory structure (`mtgo.com`/`mtgtop8.com`) encodes but the
JSON file itself doesn't; the sweep, which knows the file's directory,
supplies it explicitly. Defined independently here rather than imported
from `barrins_scripture` (Constitution §4.3 — API contracts are
first-class, owned by the API that exposes them, not borrowed from a
caller's internal schema).
"""

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.models.scripture import BSSource
from app.schemas.responses_base import BaseResponse

#: `bs_decks.result` / `bs_round_matches.result` are `String(16)` (T2) — a
#: bracket-range like "5-8" or a score like "2-0" easily fits; anything
#: longer than that is not a value this schema expects, and should 422
#: at the request boundary rather than raise an uncaught DB error deep
#: inside `ingest_scrape`.
_RESULT_MAX_LENGTH = 16
#: `bs_tournaments.format`, `bs_rounds.round_name` are `String(120)` (T2).
_SHORT_LABEL_MAX_LENGTH = 120
#: `bs_tournaments.name`, `bs_decks.player`, `bs_round_matches.player_1`/
#: `player_2`, `bs_standings.player` are all `String(255)` (T2).
_NAME_MAX_LENGTH = 255


class RequestCardEntry(BaseModel):
    count: int
    name: str


class RequestDeck(BaseModel):
    date: date
    player: str = Field(max_length=_NAME_MAX_LENGTH)
    result: str | None = Field(default=None, max_length=_RESULT_MAX_LENGTH)
    anchor_uri: str
    mainboard: list[RequestCardEntry]
    sideboard: list[RequestCardEntry] | None = None
    notes: str | None = None


class RequestMatch(BaseModel):
    player_1: str = Field(max_length=_NAME_MAX_LENGTH)
    player_2: str = Field(max_length=_NAME_MAX_LENGTH)
    result: str = Field(max_length=_RESULT_MAX_LENGTH)


class RequestRound(BaseModel):
    round_name: str = Field(max_length=_SHORT_LABEL_MAX_LENGTH)
    matches: list[RequestMatch] = []


class RequestStanding(BaseModel):
    rank: int
    player: str = Field(max_length=_NAME_MAX_LENGTH)
    points: int
    wins: int
    losses: int
    draws: int
    omwp: float
    gwp: float
    ogwp: float


class RequestTournament(BaseModel):
    date: date
    name: str = Field(max_length=_NAME_MAX_LENGTH)
    url: str
    format: str = Field(max_length=_SHORT_LABEL_MAX_LENGTH)
    players: int


class ScriptureIngestRequest(BaseModel):
    source: BSSource
    tournament: RequestTournament
    decks: list[RequestDeck] = []
    rounds: list[RequestRound] = []
    standings: list[RequestStanding] = []


class ResponseScriptureIngest(BaseResponse):
    tournament_id: uuid.UUID
    decks_upserted: int
    deck_cards_upserted: int
    rounds_upserted: int
    round_matches_upserted: int
    standings_upserted: int
    #: Distinct raw scraped names that didn't resolve against `cards`
    #: (S8) and were therefore skipped, not stored — see
    #: app/services/scripture/card_resolver.py.
    skipped_card_names: list[str]
