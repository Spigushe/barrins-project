"""Base class for all Response schemas."""

from pydantic import BaseModel, ConfigDict


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )


class Paginated[T](BaseModel):
    """Page-number pagination envelope.

    See ADR-14 in `docs/content/ops/architecture/decisions.md`.

    Distinct from Tolaria News' cursor-based `Envelope[T]`/`Page`
    (`responses_tolaria_news.py`) -- that shape is for infinite-scroll
    over staleness-sensitive scraped data; this one is for callers that
    want a total count and the ability to jump between pages.
    """

    items: list[T]
    total: int
    page: int
    per_page: int
