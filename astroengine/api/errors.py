"""Error handling utilities shared across AstroEngine API deployments."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    """Standardized error payload returned by the public API."""

    code: str = Field(description="Machine readable error code.")
    message: str = Field(description="Human friendly summary of the error.")
    details: Any | None = Field(
        default=None, description="Optional structured details that expand on the error."
    )


def _status_to_code(status_code: int) -> str:
    try:
        status = HTTPStatus(status_code)
    except ValueError:  # pragma: no cover - defensive
        return "ERROR"
    name = status.name
    # HTTPStatus enums use underscores already, but we normalize to upper snake case.
    return name.upper()


def _normalize_detail(detail: Any, default_status: int) -> ErrorEnvelope:
    """Convert FastAPI/HTTPException detail payloads into an :class:`ErrorEnvelope`."""

    default_code = _status_to_code(default_status)
    default_message = HTTPStatus(default_status).phrase

    if isinstance(detail, ErrorEnvelope):
        return detail
    if isinstance(detail, BaseModel):
        return ErrorEnvelope(**detail.model_dump())
    if isinstance(detail, Mapping):
        data = dict(detail)
        code = str(data.pop("code", default_code) or default_code)
        message = str(data.pop("message", default_message) or default_message)
        details = data.pop("details", None)
        if details is None and data:
            details = data
        return ErrorEnvelope(code=code, message=message, details=details)
    if isinstance(detail, str):
        return ErrorEnvelope(code=default_code, message=detail)
    if detail is None:
        return ErrorEnvelope(code=default_code, message=default_message)
    # Fallback for non-standard detail payloads.
    return ErrorEnvelope(code=default_code, message=default_message, details=detail)


async def http_exception_handler(_: Request, exc: HTTPException) -> ORJSONResponse:
    envelope = _normalize_detail(exc.detail, exc.status_code)
    return ORJSONResponse(status_code=exc.status_code, content=envelope.model_dump())


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> ORJSONResponse:
    envelope = ErrorEnvelope(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=exc.errors(),
    )
    return ORJSONResponse(status_code=422, content=envelope.model_dump())


async def unhandled_exception_handler(_: Request, exc: Exception) -> ORJSONResponse:  # pragma: no cover - defensive
    envelope = ErrorEnvelope(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred while processing the request.",
        details={"type": exc.__class__.__name__},
    )
    return ORJSONResponse(status_code=500, content=envelope.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    """Register shared exception handlers on the provided FastAPI app."""

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "ErrorEnvelope",
    "http_exception_handler",
    "install_error_handlers",
    "unhandled_exception_handler",
    "validation_exception_handler",
]

