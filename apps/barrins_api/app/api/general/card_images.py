"""Route /cards/{scryfall_id}/image — Scryfall image proxy with a disk cache.

Keyed by `scryfall_id` (already carried on `DeckCardOut`/the structured
Tamiyo Scroll decklist-card shape), not `mj_cards.id` — no DB lookup
needed here, this is a pure proxy in front of Scryfall.

`face=back` is how the frontend asks for a double-faced card's (MDFC/
transform) back face — always attempted alongside the front by the
frontend, never known in advance from the card data we expose, so a
single-faced card's `face=back` request 404s and the frontend hides
that image (see `HttpxScryfallClient.fetch_card_image`'s docstring).
"""

from typing import Literal

from fastapi import APIRouter, Response

from app.services.scryfall import ScryfallClientDep
from app.services.scryfall.image_cache import read_cached_image, write_cached_image

router = APIRouter()


@router.get("/cards/{scryfall_id}/image")
async def get_card_image(
    scryfall_id: str,
    client: ScryfallClientDep,
    face: Literal["front", "back"] = "front",
) -> Response:
    cached = read_cached_image(scryfall_id, face)
    if cached is not None:
        return Response(content=cached, media_type="image/jpeg")

    fetch = await client.fetch_card_image(scryfall_id, face)
    write_cached_image(scryfall_id, fetch.content, face)
    return Response(content=fetch.content, media_type=fetch.content_type)
