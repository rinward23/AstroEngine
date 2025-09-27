
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import aspects_router, policies_router, transits_router

app = FastAPI(title="AstroEngine Plus API")
for router in (policies_router, aspects_router, transits_router):
    app.include_router(router)


__all__ = ["app"]

