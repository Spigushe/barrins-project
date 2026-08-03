from pydantic import BaseModel


class Match(BaseModel):
    player_1: str
    player_2: str
    result: str


class Round(BaseModel):
    round_name: str
    matches: list[Match] = []
