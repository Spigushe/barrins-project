"""Development/test client: no network call, returns a fixed placeholder image."""

import base64
from typing import Literal

from app.core.log_config import get_logger
from app.services.scryfall.base import ScryfallImageFetch

logger = get_logger(__name__)

# A minimal valid 1x1 JPEG, used only as a dev/test placeholder — never
# served in production (see get_scryfall_client).
_PLACEHOLDER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
    "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAA"
    "AAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oA"
    "DAMBAAIRAxEAPwCdABmX/9k="
)


class ConsoleScryfallClient:
    """`ScryfallClient` implementation used when `scryfall_user_agent` is empty.

    Makes no network call — returns a fixed placeholder image, which is
    only acceptable in development/test (never in production, since the
    image proxy would silently serve fake card art otherwise).
    """

    async def fetch_card_image(
        self, scryfall_id: str, face: Literal["front", "back"] = "front"
    ) -> ScryfallImageFetch:
        logger.info(
            "ConsoleScryfallClient — returning placeholder %s-face image for %s",
            face,
            scryfall_id,
        )
        return ScryfallImageFetch(content=_PLACEHOLDER_JPEG, content_type="image/jpeg")
