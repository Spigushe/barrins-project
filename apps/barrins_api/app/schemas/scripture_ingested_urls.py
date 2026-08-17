"""Response contract for `GET /internal/scripture/ingested-urls`."""

from app.schemas.responses_base import BaseResponse


class ResponseScriptureIngestedUrls(BaseResponse):
    urls: list[str]
