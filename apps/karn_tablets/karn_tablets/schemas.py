"""Pydantic models shared across the clustering/aggregation pipeline.

Ported from the prior attempt at this
(`barrins-archive/barrins_api/app/schemas/ml.py`) -- unchanged shape,
`deck_id` narrowed from `uuid.UUID` to `str` since `BSDeck.id` is read
here as a plain string key throughout the pandas pipeline, not re-parsed
into a UUID until push time.
"""

from pydantic import BaseModel, Field


class Decklist(BaseModel):
    """A deck as {card_name: count} per zone."""

    mainboard: dict[str, int]
    sideboard: dict[str, int] = Field(default_factory=dict)


class AggregatedDecklist(BaseModel):
    """The result of aggregating multiple decklists into one representative list."""

    decklist: Decklist
    decks: list[Decklist]
    order: int
    frequency_threshold: int  # -1 = unfiltered (frequency-based aggregate_decks)


class DeckCoordinates(BaseModel):
    """A deck's cluster assignment and 2D visualization position."""

    deck_id: str
    cluster: int  # 1-indexed; 0 = DBSCAN noise
    x_coord: float
    y_coord: float
