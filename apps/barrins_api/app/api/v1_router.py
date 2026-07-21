"""API v1 root router."""

from fastapi import APIRouter

from app.api.v1 import auth as auth

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
