"""Development/test client: no network call, returns a fixed sample deck."""

from app.core.log_config import get_logger
from app.services.moxfield.base import MoxfieldDeckFetch

logger = get_logger(__name__)

_SAMPLE_DECKLIST = "1 Atraxa, Praetors' Voice\n1 Sol Ring\n1 Command Tower"

# No real Moxfield response to store — `lastUpdatedAtUtc` stays absent so
# the staleness check has nothing to compare against for fixture data.
_SAMPLE_RAW_DATA = {
    "commanders": {"Atraxa, Praetors' Voice": {"quantity": 1}},
    "companions": {},
    "mainboard": {"Sol Ring": {"quantity": 1}, "Command Tower": {"quantity": 1}},
}


class ConsoleMoxfieldClient:
    """`MoxfieldClient` implementation used when `moxfield_user_agent` is empty.

    Makes no network call — returns a fixed sample decklist, which is only
    acceptable in development/test (never in production, since Moxfield
    import would silently produce fake data otherwise).
    """

    async def fetch_decklist(self, deck_url: str) -> MoxfieldDeckFetch:
        logger.info(
            "ConsoleMoxfieldClient — returning sample decklist for %s", deck_url
        )
        return MoxfieldDeckFetch(content=_SAMPLE_DECKLIST, raw_data=_SAMPLE_RAW_DATA)
