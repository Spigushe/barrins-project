"""FastAPI application entry point and configuration.

Endpoints:
    - GET /: Redirects to /docs (API documentation)
    - GET /health: Liveness check (constitution §31.2)
    - GET /.well-known/jwks.json: Public key discovery
"""

import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1_router import router as v1_router
from app.api.v1_router import well_known_router
from app.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.log_config import get_logger
from app.core.rate_limit import limiter

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info(settings.project_version)
    logger.info(settings.base.__repr__())

    # NB: the schema is managed exclusively by Alembic (`alembic upgrade head`).
    # We deliberately don't call `Base.metadata.create_all` here — see
    # apps/barrins_api/app/main.py for the same rationale.

    logger.info("Application started successfully")
    yield

    logger.info("Shutting down application")


app = FastAPI(
    title=settings.base.project_name,
    version=settings.base.version,
    debug=settings.is_debug,
    lifespan=lifespan,
)

register_exception_handlers(app)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


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

    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"Route: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s | "
        f"RequestID: {request_id}"
    )
    return response


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


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check (constitution §31.2)."""
    return {"status": "ok"}


app.include_router(v1_router)
app.include_router(well_known_router)
