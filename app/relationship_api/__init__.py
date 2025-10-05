"""Relationship API service (B-003) exposing synastry, composite, Davison endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .config import ServiceSettings
from .middleware import install_middleware
from .routes import register_routes
from .telemetry import configure_logging


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    """Create and configure a FastAPI application for the relationship API."""

    settings = settings or ServiceSettings.from_env()
    configure_logging()
    app = FastAPI(
        title="AstroEngine Relationship API",
        version="1.0.0",
        openapi_url="/v1/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        default_response_class=ORJSONResponse,
    )
    install_middleware(app, settings)
    register_routes(app, settings)
    return app


__all__ = ["create_app", "ServiceSettings"]
