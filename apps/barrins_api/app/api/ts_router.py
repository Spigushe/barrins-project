"""API v1 — Tamiyo Scroll BFF (Competitive MTG Tracking)."""

from fastapi import APIRouter

from app.api.bff.ts_router import (
    card_tests,
    matches,
    meta_decks,
    personal_decks,
    settings,
    stats,
)

router = APIRouter(prefix="/bff/tamiyo-scroll", tags=["tamiyo-scroll"])

router.include_router(settings.router)
router.include_router(personal_decks.router)
router.include_router(meta_decks.router)
router.include_router(matches.router)
router.include_router(card_tests.router)
router.include_router(stats.router)
