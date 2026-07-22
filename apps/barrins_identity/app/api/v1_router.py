"""API v1 root router."""

from fastapi import APIRouter

from app.api.v1 import auth, service_accounts, well_known

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(service_accounts.router, tags=["service-accounts"])

# JWKS is conventionally served at the domain root, not under /api/v1.
well_known_router = APIRouter()
well_known_router.include_router(well_known.router, tags=["jwks"])
