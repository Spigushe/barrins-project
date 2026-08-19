"""Routes /stats (landing-page headline counts) -- public, no auth."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.schemas.responses_tolaria_news import Envelope, Meta, StatsResponse
from app.services.tolaria_news import stats as service
from app.services.tolaria_news import tournaments as tournaments_service

router = APIRouter()


async def _meta(session: DatabaseSession) -> Meta:
    return Meta(
        generated_at=datetime.now(UTC),
        source_synced_at=await tournaments_service.latest_sync(session),
    )


@router.get("/stats", response_model=Envelope[StatsResponse])
async def get_stats(session: DatabaseSession) -> Envelope[StatsResponse]:
    return Envelope(data=await service.get_stats(session), meta=await _meta(session))
