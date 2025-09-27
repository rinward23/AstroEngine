
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import aspects_router, policies_router, rel_router, transits_router

app = FastAPI(title="AstroEngine Plus API")
app.include_router(aspects_router)
app.include_router(transits_router)
app.include_router(policies_router)
app.include_router(rel_router)


__all__ = ["app"]

