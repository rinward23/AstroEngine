
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import (
    aspects_router,
    clear_position_provider,
    configure_position_provider,
    policies_router,
)

app = FastAPI(title="AstroEngine Plus API")
app.include_router(policies_router)
app.include_router(aspects_router)


__all__ = ["app", "configure_position_provider", "clear_position_provider"]

