"""Route registration for the relationship API."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .composite import handle_composite, handle_davison
from .config import ServiceSettings
from .errors import ServiceError
from .models import (
    ApiError,
    CompositeRequest,
    CompositeResponse,
    DavisonRequest,
    DavisonResponse,
    SynastryRequest,
    SynastryResponse,
)
from .synastry import compute_synastry
from .telemetry import get_logger


def _etag(path: str, payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")  # type: ignore[call-arg]
    else:
        data = payload
    raw = json.dumps({"path": path, "payload": data}, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f'"{digest}"'


def register_routes(app: FastAPI, settings: ServiceSettings) -> None:
    router = APIRouter(prefix="/v1", tags=["Relationship"])

    @app.exception_handler(ServiceError)
    async def _service_error_handler(request: Request, exc: ServiceError):  # type: ignore[override]
        logger = getattr(request.state, "logger", get_logger())
        logger.warning(
            "service.error",
            extra={"code": exc.code, "message": str(exc)},
        )
        payload = ApiError(code=exc.code, message=str(exc), details=exc.details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):  # type: ignore[override]
        logger = getattr(request.state, "logger", get_logger())
        logger.warning("validation.error", extra={"errors": exc.errors()})
        payload = ApiError(code="BAD_INPUT", message="Invalid request payload", details={"errors": exc.errors()})
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload.model_dump())

    @router.get("/healthz", summary="Service health", tags=["Health"])
    async def healthz() -> dict[str, Any]:
        return {"status": "ok"}

    @router.post(
        "/relationship/synastry",
        response_model=SynastryResponse,
        summary="Synastry hits, grid, overlay, and scores",
        responses={
            429: {
                "model": ApiError,
                "description": "Rate limited. Back off and retry after the number of seconds in the Retry-After header.",
            }
        },
    )
    async def synastry_endpoint(request: Request, response: Response, payload: SynastryRequest) -> SynastryResponse:
        logger = getattr(request.state, "logger", get_logger())
        logger.info("synastry.request", extra={"path": request.url.path})
        if settings.enable_etag:
            etag_value = _etag("synastry", payload)
            if request.headers.get("if-none-match") == etag_value:
                headers = {"ETag": etag_value}
                headers.setdefault("X-Request-ID", getattr(request.state, "request_id", "-"))
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)  # type: ignore[return-value]
            response.headers["ETag"] = etag_value
        result = compute_synastry(payload)
        return result

    @router.post(
        "/relationship/composite",
        response_model=CompositeResponse,
        summary="Composite midpoint positions",
        responses={
            429: {
                "model": ApiError,
                "description": "Rate limited. Back off and retry after the number of seconds in the Retry-After header.",
            }
        },
    )
    async def composite_endpoint(request: Request, response: Response, payload: CompositeRequest) -> CompositeResponse:
        logger = getattr(request.state, "logger", get_logger())
        logger.info("composite.request", extra={"path": request.url.path})
        if settings.enable_etag:
            etag_value = _etag("composite", payload)
            if request.headers.get("if-none-match") == etag_value:
                headers = {"ETag": etag_value}
                headers.setdefault("X-Request-ID", getattr(request.state, "request_id", "-"))
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)  # type: ignore[return-value]
            response.headers["ETag"] = etag_value
        return handle_composite(payload)

    @router.post(
        "/relationship/davison",
        response_model=DavisonResponse,
        summary="Davison midpoints and positions",
        responses={
            429: {
                "model": ApiError,
                "description": "Rate limited. Back off and retry after the number of seconds in the Retry-After header.",
            }
        },
    )
    async def davison_endpoint(request: Request, payload: DavisonRequest) -> DavisonResponse:
        logger = getattr(request.state, "logger", get_logger())
        logger.info("davison.request", extra={"path": request.url.path, "eph": payload.eph})
        try:
            return handle_davison(payload)
        except ServiceError:
            raise
        except Exception as exc:
            raise ServiceError("EPHEMERIS_ERROR", "Davison computation failed", status_code=500, details={"error": str(exc)}) from exc

    app.include_router(router)


__all__ = ["register_routes"]
