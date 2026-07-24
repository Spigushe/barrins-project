"""Development/test client: no network call, returns a fixed sample deck."""

from app.core.log_config import get_logger

logger = get_logger(__name__)

_SAMPLE_DECKLIST = "1 Atraxa, Praetors' Voice\n1 Sol Ring\n1 Command Tower"


class ConsoleMoxfieldClient:
    """`MoxfieldClient` implementation used when `moxfield_user_agent` is empty.

    Makes no network call — returns a fixed sample decklist, which is only
    acceptable in development/test (never in production, since Moxfield
    import would silently produce fake data otherwise).
    """

    async def fetch_decklist(self, deck_url: str) -> str:
        logger.info(
            "ConsoleMoxfieldClient — returning sample decklist for %s", deck_url
        )
        return _SAMPLE_DECKLIST
