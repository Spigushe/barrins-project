"""Tolaria News BFF routes (public Duel Commander tournament data).

Under /bff/tolaria-news.
"""

from fastapi import APIRouter

from app.api.tolaria_news import decks, stats, telemetry, tournaments

router = APIRouter(prefix="/bff/tolaria-news", tags=["tolaria-news"])

router.include_router(tournaments.router)
router.include_router(decks.router)
router.include_router(telemetry.router)
router.include_router(stats.router)
