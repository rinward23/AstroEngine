
"""FastAPI application factory for AstroEngine services."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

_APP_INSTANCE: FastAPI | None = None


def create_app() -> FastAPI:
    from .errors import install_error_handlers
    from .routers import interpret as interpret_router
    from .routers import lots as lots_router
    from .routers import natals as natals_router
    from .routers import plus as plus_router
    from .routers import scan as scan_router
    from .routers import synastry as synastry_router
    from .routers import topocentric as topocentric_router
    from .routers import transit_overlay as transit_overlay_router
    from .routers import vedic as vedic_router
    from .routers import timeline as timeline_router

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
        ],
    )
    app.add_middleware(GZipMiddleware, minimum_size=512)
    install_error_handlers(app)

    app.include_router(plus_router.router)
    app.include_router(interpret_router.router)
    app.include_router(natals_router.router)
    app.include_router(lots_router.router, prefix="/v1", tags=["lots"])
    app.include_router(scan_router.router, prefix="/v1/scan", tags=["scan"])
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



__all__ = ["app", "create_app", "get_app"]


