
"""FastAPI application factory for AstroEngine services."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import scan as scan_router
from .routers import synastry as synastry_router


def create_app() -> FastAPI:
    app = FastAPI(title="AstroEngine API")
    app.include_router(scan_router.router, prefix="/v1/scan", tags=["scan"])
    app.include_router(synastry_router.router, prefix="/v1/synastry", tags=["synastry"])
    return app


app = create_app()

__all__ = ["create_app", "app"]

