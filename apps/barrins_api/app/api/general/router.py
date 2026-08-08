"""Aggregates general routes: root redirect, /health, and /api/v1 auth."""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.general import auth, health, mtgjson, scripture

router = APIRouter()


@router.get("/")
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=301)


router.include_router(health.router)
router.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
router.include_router(mtgjson.router, prefix="/api/v1", tags=["mtgjson"])
router.include_router(
    scripture.router, prefix="/internal/scripture", tags=["scripture-internal"]
)
