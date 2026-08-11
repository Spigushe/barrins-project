"""Response contract for `GET /internal/scripture/db-metrics`."""

from app.schemas.responses_base import BaseResponse


class ResponseTableSize(BaseResponse):
    table_name: str
    size_bytes: int
    row_count: int


class ResponseScriptureDbMetrics(BaseResponse):
    tables: list[ResponseTableSize]
