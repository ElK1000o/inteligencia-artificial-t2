"""
FastAPI exception handlers for MatEnergy-ML.

All handlers return a consistent JSON envelope:
    {
        "error":              "<MACHINE_READABLE_CODE>",
        "message":            "<user-safe description>",
        "recommended_action": "<recovery hint>"         # omitted when empty
    }

Validation errors (422) include an additional "details" key with the
Pydantic error list so clients can map errors back to specific fields.

Register all handlers in app/main.py via:
    app.add_exception_handler(MatEnergyBaseError, matenergy_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
"""
from __future__ import annotations

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DatasetValidationError,
    FileUploadError,
    InsufficientPermissionsError,
    MatEnergyBaseError,
    NotFoundError,
    ResourceConflictError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenTypeMismatchError,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# HTTP status mapping helpers
# ---------------------------------------------------------------------------

_AUTH_ERRORS = (
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenTypeMismatchError,
)


def _status_for(exc: MatEnergyBaseError) -> int:
    if isinstance(exc, _AUTH_ERRORS):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(exc, InsufficientPermissionsError):
        return status.HTTP_403_FORBIDDEN
    if isinstance(exc, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, ResourceConflictError):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, (FileUploadError, DatasetValidationError)):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    return status.HTTP_400_BAD_REQUEST


def _build_error_body(exc: MatEnergyBaseError) -> dict:
    body: dict = {
        "error": exc.code,
        "message": exc.message,
    }
    if exc.recommended_action:
        body["recommended_action"] = exc.recommended_action
    return body


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def matenergy_exception_handler(
    request: Request, exc: MatEnergyBaseError
) -> JSONResponse:
    """
    Handle all MatEnergyBaseError subclasses.

    Logs the internal detail at WARNING level (not exposed to clients) and
    returns a sanitised JSON error response.
    """
    http_status = _status_for(exc)
    logger.warning(
        "domain_error",
        code=exc.code,
        detail=exc.detail,
        path=str(request.url),
        method=request.method,
        http_status=http_status,
    )

    headers: dict[str, str] = {}
    if isinstance(exc, _AUTH_ERRORS):
        headers["WWW-Authenticate"] = "Bearer"

    return JSONResponse(
        status_code=http_status,
        content=_build_error_body(exc),
        headers=headers or None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic / FastAPI request validation errors (HTTP 422).

    The raw error list from Pydantic is safe to return because it only
    references field names and constraint descriptions — no internal paths
    or secrets.
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=str(request.url),
        method=request.method,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Datos de la solicitud inválidos",
            "details": exc.errors(),
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Logs at ERROR level with full exception info for the on-call engineer.
    Returns a generic 500 that reveals nothing about internals to the client.
    """
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        path=str(request.url),
        method=request.method,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Ocurrió un error interno inesperado. Nuestro equipo ha sido notificado.",
        },
    )
