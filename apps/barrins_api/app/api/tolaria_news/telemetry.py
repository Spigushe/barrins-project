"""Routes /telemetry (bottom-rail season/countdown/last-sync) -- public,
no auth.
"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.database.session import DatabaseSession
from app.schemas.responses_tolaria_news import Envelope, Meta, TelemetryResponse
from app.services.tolaria_news import telemetry as service
from app.services.tolaria_news import tournaments as tournaments_service

router = APIRouter()


async def _meta(session: DatabaseSession) -> Meta:
    return Meta(
        generated_at=datetime.now(UTC),
        source_synced_at=await tournaments_service.latest_sync(session),
    )


@router.get("/telemetry", response_model=Envelope[TelemetryResponse])
async def get_telemetry(session: DatabaseSession) -> Envelope[TelemetryResponse]:
    return Envelope(data=service.get_telemetry(), meta=await _meta(session))
