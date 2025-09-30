
"""FastAPI application factory for AstroEngine services."""

from __future__ import annotations

from fastapi import FastAPI

_APP_INSTANCE: FastAPI | None = None


def create_app() -> FastAPI:
    from .routers import lots as lots_router
    from .routers import plus as plus_router
    from .routers import scan as scan_router
    from .routers import synastry as synastry_router

    from .routers import topocentric as topocentric_router


    app = FastAPI(title="AstroEngine API")
    app.include_router(plus_router.router)
    app.include_router(lots_router.router, prefix="/v1", tags=["lots"])
    app.include_router(scan_router.router, prefix="/v1/scan", tags=["scan"])
    app.include_router(synastry_router.router, prefix="/v1/synastry", tags=["synastry"])

    app.include_router(topocentric_router.router, prefix="/v1", tags=["topocentric"])

    return app


def get_app() -> FastAPI:
    global _APP_INSTANCE
    if _APP_INSTANCE is None:
        _APP_INSTANCE = create_app()
    return _APP_INSTANCE


app = get_app()



__all__ = ["app", "create_app", "get_app"]



app = get_app()


