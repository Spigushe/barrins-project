"""Routes /decks/{id} -- deck detail, public, no auth."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.database.session import DatabaseSession
from app.schemas.responses_tolaria_news import DeckDetail, Envelope, Meta
from app.services.tolaria_news import decks as service
from app.services.tolaria_news import tournaments as tournaments_service

router = APIRouter()


@router.get("/decks/{deck_id}", response_model=Envelope[DeckDetail])
async def get_deck(
    deck_id: uuid.UUID, session: DatabaseSession
) -> Envelope[DeckDetail]:
    deck = await service.get_deck(session, deck_id)
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found."
        )
    meta = Meta(
        generated_at=datetime.now(UTC),
        source_synced_at=await tournaments_service.latest_sync(session),
    )
    return Envelope(data=deck, meta=meta)
