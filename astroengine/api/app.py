"""FastAPI application factory used by ASGI servers and CLI tooling."""

from __future__ import annotations

import logging
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from astroengine.boot.logging import configure_logging
from astroengine.config import Settings, default_settings, load_settings

from .errors import install_error_handlers
from .routers import (
    analysis as analysis_router,
    doctor as doctor_router,
    forecast as forecast_router,
    health as health_router,
    interpret as interpret_router,
    lots as lots_router,
    natals as natals_router,
    plus as plus_router,
    returns as returns_router,
    scan as scan_router,
    synastry as synastry_router,
    timeline as timeline_router,
    topocentric as topocentric_router,
    transit_overlay as transit_overlay_router,
    vedic as vedic_router,
)
from .settings import settings as api_settings

LOGGER = logging.getLogger(__name__)

configure_logging()

_APP_INSTANCE: FastAPI | None = None


def _load_domain_settings() -> Settings:
    try:
        return load_settings()
    except Exception as exc:  # pragma: no cover - defensive: IO/env issues
        LOGGER.warning("Failed to load persisted settings; using defaults: %s", exc)
        return default_settings()


def _configure_cors(app: FastAPI) -> None:
    origins: Iterable[str] = api_settings.cors_origins
    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_routes(app: FastAPI) -> None:
    app.include_router(health_router.router)
    app.include_router(plus_router.router)
    app.include_router(analysis_router.router)
    app.include_router(interpret_router.router)
    app.include_router(forecast_router.router)
    app.include_router(natals_router.router)
    app.include_router(doctor_router.router)
    app.include_router(lots_router.router, prefix="/v1", tags=["lots"])
    app.include_router(scan_router.router, prefix="/v1/scan", tags=["scan"])
    app.include_router(returns_router.router)
    app.include_router(synastry_router.router, prefix="/v1/synastry", tags=["synastry"])
    app.include_router(vedic_router.router)
    app.include_router(topocentric_router.router, prefix="/v1", tags=["topocentric"])
    app.include_router(transit_overlay_router.router)
    app.include_router(timeline_router.router, prefix="/v1", tags=["timeline"])


def _register_startup_hooks(app: FastAPI) -> None:
    @app.on_event("startup")
    def _prime_settings() -> None:
        app.state.settings = _load_domain_settings()

    @app.on_event("startup")
    def _ensure_ephemeris() -> None:
        try:
            from astroengine.ephemeris import SwissEphemerisAdapter
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency missing
            raise RuntimeError("Swiss Ephemeris runtime unavailable") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise RuntimeError("Failed to import Swiss Ephemeris adapter") from exc

        try:
            adapter = SwissEphemerisAdapter.get_default_adapter()
            adapter.describe_configuration()
        except Exception as exc:
            LOGGER.error("Swiss Ephemeris readiness check failed: %s", exc)
            raise RuntimeError("Swiss Ephemeris readiness check failed") from exc

        app.state.ephemeris_adapter = adapter

    @app.on_event("startup")
    def _ensure_database() -> None:
        try:
            from sqlalchemy import text
            from app.db.session import engine
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency missing
            LOGGER.warning("Database dependencies unavailable; skipping readiness check: %s", exc)
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.warning("Database engine unavailable; skipping readiness check: %s", exc)
            return

        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            LOGGER.error("Database readiness check failed: %s", exc)
            raise RuntimeError("Database readiness check failed") from exc

        app.state.database_engine = engine


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""

    app = FastAPI(
        title="AstroEngine API",
        version="1.0",
        default_response_class=ORJSONResponse,
        openapi_tags=[
            {"name": "system", "description": "Service level operations."},
            {"name": "interpret", "description": "Relationship interpretation services."},
            {"name": "natals", "description": "Stored natal chart management."},
            {"name": "scan", "description": "Transit and progression scanning."},
            {"name": "synastry", "description": "Synastry chart operations."},
            {"name": "analysis", "description": "Catalog and fixed-star lookups."},
        ],
    )

    app.state.api_settings = api_settings

    app.add_middleware(GZipMiddleware, minimum_size=512)
    install_error_handlers(app)
    _configure_cors(app)
    _register_routes(app)
    _register_startup_hooks(app)

    return app


def get_app() -> FastAPI:
    global _APP_INSTANCE
    if _APP_INSTANCE is None:
        _APP_INSTANCE = create_app()
    return _APP_INSTANCE


app = get_app()


def run() -> None:  # pragma: no cover - integration entry point
    """Run the API using Uvicorn's development server."""

    import uvicorn

    uvicorn.run(
        "astroengine.api.app:app",
        host=api_settings.host,
        port=api_settings.port,
        log_level=api_settings.log_level,
        reload=api_settings.reload,
    )


__all__ = ["app", "create_app", "get_app", "run"]

