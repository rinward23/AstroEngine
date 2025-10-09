"""FastAPI application factory and legacy transit helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

if TYPE_CHECKING:  # pragma: no cover - runtime side effects avoided during typing
    from astroengine.core.api import TransitEvent, TransitScanConfig
    from astroengine.core.transit_engine import TransitEngine, TransitEngineConfig

_APP_INSTANCE: FastAPI | None = None


def _load_transit_engine() -> tuple[type[TransitEngine], type[TransitEngineConfig]]:
    """Import transit engine helpers lazily to avoid heavy dependencies."""

    from astroengine.core.transit_engine import TransitEngine, TransitEngineConfig

    return TransitEngine, TransitEngineConfig


def _load_transit_api() -> tuple[type[TransitEvent], type[TransitScanConfig]]:
    """Import public dataclasses exposed for backwards compatibility."""

    from astroengine.core.api import TransitEvent, TransitScanConfig

    return TransitEvent, TransitScanConfig


def __getattr__(name: str) -> Any:  # pragma: no cover - invoked via diagnostics
    """Preserve legacy re-exports from :mod:`astroengine.api`.

    Older integrations imported :class:`TransitEngine` and its related
    dataclasses directly from :mod:`astroengine.api`.  The FastAPI module was
    recently split out and those aliases were lost, breaking diagnostics and
    downstream tooling.  We restore the symbols here while keeping imports
    lazy so environments without Swiss Ephemeris support do not fail at import
    time.
    """

    if name in {"TransitEngine", "TransitEngineConfig"}:
        TransitEngine, TransitEngineConfig = _load_transit_engine()
        globals().update(
            {
                "TransitEngine": TransitEngine,
                "TransitEngineConfig": TransitEngineConfig,
            }
        )
        return globals()[name]
    if name in {"TransitEvent", "TransitScanConfig"}:
        TransitEvent, TransitScanConfig = _load_transit_api()
        globals().update(
            {
                "TransitEvent": TransitEvent,
                "TransitScanConfig": TransitScanConfig,
            }
        )
        return globals()[name]
    raise AttributeError(name)


def __dir__() -> list[str]:  # pragma: no cover - used for tooling hints only
    return sorted(
        set(globals())
        | {"TransitEngine", "TransitEngineConfig", "TransitEvent", "TransitScanConfig"}
    )


def create_app() -> FastAPI:
    from .errors import install_error_handlers
    from .routers import analysis as analysis_router
    from .routers import forecast as forecast_router
    from .routers import interpret as interpret_router
    from .routers import lots as lots_router
    from .routers import natals as natals_router
    from .routers import plus as plus_router
    from .routers import returns as returns_router
    from .routers import scan as scan_router
    from .routers import synastry as synastry_router
    from .routers import timeline as timeline_router
    from .routers import topocentric as topocentric_router
    from .routers import transit_overlay as transit_overlay_router
    from .routers import vedic as vedic_router

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
            {"name": "analysis", "description": "Chart dignity and condition reports."},
        ],
    )
    app.add_middleware(GZipMiddleware, minimum_size=512)
    install_error_handlers(app)

    app.include_router(plus_router.router)
    app.include_router(analysis_router.router)
    app.include_router(interpret_router.router)
    app.include_router(forecast_router.router)
    app.include_router(natals_router.router)
    app.include_router(lots_router.router, prefix="/v1", tags=["lots"])
    app.include_router(scan_router.router, prefix="/v1/scan", tags=["scan"])
    app.include_router(returns_router.router)
    app.include_router(synastry_router.router, prefix="/v1/synastry", tags=["synastry"])
    app.include_router(vedic_router.router)
    app.include_router(topocentric_router.router, prefix="/v1", tags=["topocentric"])
    app.include_router(transit_overlay_router.router)
    app.include_router(timeline_router.router, prefix="/v1", tags=["timeline"])

    return app


def get_app() -> FastAPI:
    global _APP_INSTANCE
    if _APP_INSTANCE is None:
        _APP_INSTANCE = create_app()
    return _APP_INSTANCE


app = get_app()



__all__ = [
    "app",
    "create_app",
    "get_app",
    "TransitEngine",
    "TransitEngineConfig",
    "TransitEvent",
    "TransitScanConfig",
]

