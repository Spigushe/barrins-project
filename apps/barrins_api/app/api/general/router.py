"""Aggregates general routes: root redirect, /health, and /api/v1 auth."""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.general import auth, health

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


@router.get("/")
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=301)
