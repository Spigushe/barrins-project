"""FastAPI application entry point and configuration.

This module initializes the FastAPI application with middleware, CORS settings,
and route registration. It defines the application lifespan context manager
for startup/shutdown events and request logging middleware.

Endpoints:
    - GET /: Redirects to /docs (API documentation)
    - GET /health/*: Health check endpoints (live, ready)
    - GET /metrics: Prometheus metrics endpoint
"""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.ts_router import router as ts_router
from app.api.v1_router import router as v1_router
from app.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.log_config import get_logger

# Logging configuration
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
    # Startup checks
    logger.info(settings.project_version)
    logger.info(settings.base.__repr__())

    # NB: the schema is managed exclusively by Alembic (`alembic upgrade head`).
    # We deliberately don't call `Base.metadata.create_all` here: this
    # method only knows how to create missing tables (never alter an
    # existing one), which makes it diverge from the migrations and fail
    # as soon as a table inherited from an old schema is present in the DB.

    logger.info("Application started successfully")
    yield

    # Application shutdown
    logger.info("Shutting down application")


# App creation
app = FastAPI(
    title=settings.base.project_name,
    version=settings.base.version,
    debug=settings.is_debug,
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"Route: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s | "
        f"RequestID: {request_id}"
    )
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.base.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=301)


# Register the routes
app.include_router(v1_router)
app.include_router(ts_router)
