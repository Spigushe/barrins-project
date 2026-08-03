from datetime import date

from pydantic import BaseModel


class CardEntry(BaseModel):
    count: int
    name: str


class Deck(BaseModel):
    date: date
    player: str
    result: str | None = None
    anchor_uri: str
    mainboard: list[CardEntry]
    sideboard: list[CardEntry] | None = None
    notes: str | None = None
