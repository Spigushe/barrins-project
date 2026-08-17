"""Bottom-rail telemetry (season, banlist countdown) backing the Tolaria
News BFF. Pure date math -- no DB session needed; `last_sync` is reported
separately via the route's own `Meta` (see `api/tolaria_news/telemetry.py`).
"""

from datetime import UTC, datetime

from dc_calendar.windowing import banlist_period_number, effective_banlist_period

from app.schemas.responses_tolaria_news import TelemetryResponse, WindowOut


def get_telemetry() -> TelemetryResponse:
    season, next_banlist_at = effective_banlist_period(datetime.now(UTC))
    year, number = banlist_period_number(season)
    return TelemetryResponse(
        season=WindowOut(
            kind="banlist_period",
            label=season.label,
            date_from=season.date_from,
            date_to=season.date_to,
        ),
        season_year=year,
        season_number=number,
        next_banlist_at=next_banlist_at,
    )
