"""Response schemas for the MTGJSON reference-data routes (S8)."""

import uuid
from datetime import date, datetime

from app.schemas.responses_base import BaseResponse


class ResponseSet(BaseResponse):
    code: str
    name: str
    release_date: date
    type: str
    block: str | None
    base_set_size: int
    total_set_size: int
    keyrune_code: str
    is_online_only: bool


class ResponseCard(BaseResponse):
    id: uuid.UUID
    set_code: str
    name: str
    face_name: str | None
    side: str | None
    layout: str
    other_face_ids: list[str]
    type_line: str
    types: list[str]
    supertypes: list[str]
    subtypes: list[str]
    mana_cost: str | None
    mana_value: float | None
    colors: list[str]
    color_identity: list[str]
    rarity: str
    number: str
    scryfall_id: str | None
    scryfall_oracle_id: str | None
    text: str | None
    keywords: list[str]
    power: str | None
    toughness: str | None
    loyalty: str | None


class ResponseImportResult(BaseResponse):
    sets_upserted: int
    cards_upserted: int


class ResponseImportStatus(BaseResponse):
    last_imported_at: datetime | None
    total_sets: int
    total_cards: int


class ResponseImportRun(BaseResponse):
    id: uuid.UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    sets_upserted: int
    cards_upserted: int
    error_message: str | None
