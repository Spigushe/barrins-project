from pydantic import BaseModel


class Standing(BaseModel):
    rank: int
    player: str
    points: int
    wins: int
    losses: int
    draws: int
    omwp: float
    gwp: float
    ogwp: float
