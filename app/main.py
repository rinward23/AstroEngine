
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from astroengine.cache.positions_cache import warm_startup_grid
from astroengine.config import load_settings
from astroengine.ephemeris.adapter import EphemerisAdapter, EphemerisConfig

from app.db.session import engine
from app.observability import configure_observability
from app.telemetry import resolve_observability_config, setup_tracing
from astroengine.web.middleware import configure_compression

LOGGER = logging.getLogger(__name__)

from app.routers import (
    aspects_router,
    declinations_router,
    electional_router,
    events_router,
    doctor_router,
    health_router,
    interpret_router,
    lots_router,
    narrative_profiles_router,
    policies_router,
    profiles_router,
    narrative_mix_router,
    settings_router,
    reports_router,
    relationship_router,
    transits_router,
    notes_router,
    data_router,
    charts_router,
)
from app.routers.aspects import (  # re-exported for convenience
    clear_position_provider,
    configure_position_provider,
)

try:  # pragma: no cover - falls back when optional dependency missing
    from fastapi.responses import ORJSONResponse
except ImportError:  # pragma: no cover - exercised in environments without orjson
    DEFAULT_RESPONSE_CLASS = JSONResponse
else:
    DEFAULT_RESPONSE_CLASS = ORJSONResponse

SAFE_MODE = os.getenv("SAFE_MODE") == "1"
DEV_MODE_ENABLED = os.getenv("DEV_MODE")

app = FastAPI(
    title="AstroEngine Plus API", default_response_class=DEFAULT_RESPONSE_CLASS
)
configure_compression(app)
configure_observability(app)
_obs_cfg = resolve_observability_config(app)
setup_tracing(
    app,
    sqlalchemy_engine=engine,
    sampling_ratio=getattr(_obs_cfg, "sampling_ratio", None),
    enabled=getattr(_obs_cfg, "otel_enabled", None),
)
app.include_router(aspects_router)
app.include_router(declinations_router)
app.include_router(electional_router)
app.include_router(events_router)
app.include_router(doctor_router)
app.include_router(transits_router)
app.include_router(policies_router)
app.include_router(lots_router)
app.include_router(relationship_router)
app.include_router(interpret_router)
app.include_router(reports_router)
app.include_router(health_router)
app.include_router(settings_router)
app.include_router(notes_router)
app.include_router(data_router)
app.include_router(charts_router)
app.include_router(profiles_router)
app.include_router(narrative_profiles_router)
if DEV_MODE_ENABLED:
    from app.devmode import router as devmode_router

    app.include_router(devmode_router)


def _log_ephemeris_path(state: Any) -> None:
    """Record Swiss ephemeris path configuration and surface startup warnings."""

    ephe_raw = os.getenv("SE_EPHE_PATH")
    state.se_ephe_path = ephe_raw
    if not ephe_raw:
        state.se_ephe_path_resolved = None
        state.se_ephe_path_exists = False
        LOGGER.warning(
            "Swiss Ephemeris path not configured; set SE_EPHE_PATH to enable high-precision Swiss data."
        )
        return

    candidate = Path(ephe_raw).expanduser()
    state.se_ephe_path_resolved = str(candidate)
    exists = candidate.exists()
    state.se_ephe_path_exists = exists
    if exists:
        LOGGER.info("Swiss Ephemeris path resolved to %s", candidate)
    else:
        LOGGER.warning(
            "Swiss Ephemeris path %s does not exist; Swiss calculations may fall back to bundled data.",
            candidate,
        )


@app.on_event("startup")
def _init_singletons() -> None:
    """Initialize application-wide state on startup."""

    app.state.trust_proxy = os.getenv("TRUST_PROXY", "0").lower() in {"1", "true", "yes"}
    app.state.settings = load_settings()
    _log_ephemeris_path(app.state)
    app.state.safe_mode = SAFE_MODE
    if SAFE_MODE:
        app.state.plugin_registry = None
        app.state.loaded_plugins = []
        app.state.loaded_providers = []
    else:
        try:
            from astroengine.plugins.runtime import (
                Registry,
                load_plugins,
                load_providers,
            )
        except ImportError:  # pragma: no cover - optional dependency missing
            app.state.plugin_registry = None
            app.state.loaded_plugins = []
            app.state.loaded_providers = []
        else:
            registry = Registry()
            app.state.plugin_registry = registry
            try:
                app.state.loaded_plugins = load_plugins(registry)
                app.state.loaded_providers = load_providers(registry)
            except Exception as exc:  # pragma: no cover - defensive guard
                app.state.plugin_registry_error = str(exc)
                app.state.loaded_plugins = []
                app.state.loaded_providers = []
    app.state.dev_mode_enabled = bool(DEV_MODE_ENABLED)

    try:
        warmed_entries = warm_startup_grid()
    except Exception:  # pragma: no cover - defensive guard
        LOGGER.exception("Startup cache warm failed")
        app.state.startup_cache_warm_entries = 0
    else:
        app.state.startup_cache_warm_entries = warmed_entries
        LOGGER.debug("Warmed %s JD/body entries during startup", warmed_entries)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Apply default security headers to every HTTP response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=()"
    )
    if request.method == "GET":
        response.headers.setdefault("Cache-Control", "public, max-age=60")
    return response


__all__ = [
    "app",
    "configure_position_provider",
    "clear_position_provider",
    "get_adapter",
]

