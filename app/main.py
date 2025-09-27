
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import policies_router

app = FastAPI(title="AstroEngine Plus API")
app.include_router(policies_router)


__all__ = ["app"]

