"""Health check endpoint — reports service and database availability."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import ServiceUnavailableError
from app.core.log_config import get_logger
from app.dependencies import DatabaseSession
from app.schemas.responses_health import HealthResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(session: DatabaseSession) -> HealthResponse:
    """Report service health for external uptime monitoring.

    Returns 200 when the database is reachable. Raises
    ServiceUnavailableError (503, via the global AppException handler)
    otherwise.
    """
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Health check failed: database unreachable", exc_info=exc)
        raise ServiceUnavailableError(message="Database is unreachable") from exc

    return HealthResponse(status="ok")
