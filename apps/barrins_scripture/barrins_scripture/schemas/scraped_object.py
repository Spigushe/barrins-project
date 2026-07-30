from pydantic import BaseModel

from barrins_scripture.schemas.deck import Deck
from barrins_scripture.schemas.round import Round
from barrins_scripture.schemas.standing import Standing
from barrins_scripture.schemas.tournament import Tournament


class MTGScrape(BaseModel):
    tournament: Tournament
    decks: list[Deck] = []
    rounds: list[Round] = []
    standings: list[Standing] = []
