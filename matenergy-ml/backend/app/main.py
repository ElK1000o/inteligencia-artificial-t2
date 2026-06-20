"""
MatEnergy-ML — FastAPI application entry point.

Startup sequence (lifespan):
  1. configure_logging() — must be first so all subsequent code uses structured logs
  2. (future) database connectivity check
  3. (future) ML artifact warm-up

Exception handlers registered:
  - MatEnergyBaseError  → domain-aware JSON response (4xx)
  - RequestValidationError → 422 with Pydantic field details
  - Exception (catch-all) → generic 500, full exc info logged internally
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.error_handlers import (
    generic_exception_handler,
    matenergy_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import MatEnergyBaseError
from app.core.logging_config import configure_logging, get_logger


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application startup / shutdown logic."""
    # Logging must be configured before any logger is used
    configure_logging()
    logger = get_logger(__name__)
    logger.info(
        "startup",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        api_prefix=settings.API_V1_PREFIX,
    )
    yield
    logger.info("shutdown", service=settings.PROJECT_NAME)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Kept as a factory function to make testing (and future multi-tenancy)
    straightforward — tests can call ``create_app()`` directly.
    """
    _app = FastAPI(
        title="MatEnergy-ML API",
        description=(
            "Computational screening platform for energy materials "
            "using ML and DFT-derived data."
        ),
        version="0.1.0",
        # Disable interactive docs in production to reduce the attack surface
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # Middleware
    # -----------------------------------------------------------------------
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # -----------------------------------------------------------------------
    # Exception handlers
    # (order matters: most specific first, catch-all last)
    # -----------------------------------------------------------------------
    _app.add_exception_handler(MatEnergyBaseError, matenergy_exception_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    _app.add_exception_handler(Exception, generic_exception_handler)

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    from app.api.v1 import router as api_v1_router
    _app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return _app


# ---------------------------------------------------------------------------
# Module-level singleton used by uvicorn / gunicorn
# ---------------------------------------------------------------------------

app = create_app()


# ---------------------------------------------------------------------------
# Built-in health probes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"], summary="Liveness probe")
async def health_check() -> dict:
    """
    Liveness probe for Docker and load balancers.

    Returns HTTP 200 as long as the process is running and the event loop
    is not blocked.  Does **not** check downstream dependencies (database,
    Redis, etc.) — use /api/v1/health for a deeper readiness check.
    """
    return {
        "status": "ok",
        "service": "matenergy-ml-backend",
        "version": "0.1.0",
    }


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["health"], summary="Readiness probe")
async def api_health() -> dict:
    """
    Readiness probe — confirms the API v1 prefix is reachable.

    Future versions of this endpoint will also verify database connectivity
    and cache availability before returning ``"status": "ok"``.
    """
    return {
        "status": "ok",
        "api_version": "v1",
        "environment": settings.ENVIRONMENT,
    }
