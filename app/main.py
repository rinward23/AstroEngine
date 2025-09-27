
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import (
    aspects_router,
    electional_router,
    events_router,
    lots_router,
    policies_router,
    transits_router,
)
from app.routers.aspects import (  # re-exported for convenience
    clear_position_provider,
    configure_position_provider,
)

app = FastAPI(title="AstroEngine Plus API")
app.include_router(aspects_router)
app.include_router(electional_router)
app.include_router(events_router)
app.include_router(transits_router)
app.include_router(policies_router)
app.include_router(lots_router)


__all__ = ["app", "configure_position_provider", "clear_position_provider"]

