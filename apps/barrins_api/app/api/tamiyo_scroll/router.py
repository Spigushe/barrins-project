"""Tamiyo Scroll BFF routes (Competitive MTG Tracking), under /bff/tamiyo-scroll."""

from fastapi import APIRouter

from app.api.tamiyo_scroll import (
    card_tests,
    matches,
    meta_decks,
    personal_decks,
    sessions,
    settings,
    stats,
    teams,
)

router = APIRouter(prefix="/bff/tamiyo-scroll", tags=["tamiyo-scroll"])

router.include_router(settings.router)
router.include_router(personal_decks.router)
router.include_router(meta_decks.router)
router.include_router(matches.router)
router.include_router(card_tests.router)
router.include_router(stats.router)
router.include_router(sessions.router)
router.include_router(teams.router)
