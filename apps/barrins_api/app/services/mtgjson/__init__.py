"""MTGJSON card/set reference-data pipeline (S8)."""

from typing import Annotated

from fastapi import Depends

from app.services.mtgjson.base import MTGJSONClient
from app.services.mtgjson.http_client import HttpxMTGJSONClient
from app.services.mtgjson.importer import ImportResult, import_all_printings


def get_mtgjson_client() -> MTGJSONClient:
    """MTGJSON needs no credentials (free public bulk file) -- unlike
    Moxfield, there's no configured/unconfigured split to select between.
    """
    return HttpxMTGJSONClient()


MTGJSONClientDep = Annotated[MTGJSONClient, Depends(get_mtgjson_client)]

__all__ = [
    "HttpxMTGJSONClient",
    "ImportResult",
    "MTGJSONClient",
    "MTGJSONClientDep",
    "get_mtgjson_client",
    "import_all_printings",
]
