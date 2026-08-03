from datetime import date

from pydantic import BaseModel


class Tournament(BaseModel):
    date: date
    name: str
    url: str
    format: str
    players: int
