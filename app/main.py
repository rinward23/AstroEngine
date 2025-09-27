"""FastAPI application entry-point for AstroEngine."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from fastapi import FastAPI

from app.routers import aspects as aspects_module
from app.routers.aspects import router as aspects_router

app = FastAPI(title="AstroEngine API")
app.include_router(aspects_router)


def demo_provider(ts: datetime) -> Dict[str, float]:
    """Placeholder ephemeris returning static positions."""

    _ = ts
    return {"Sun": 0.0, "Moon": 0.0, "Mars": 0.0, "Venus": 0.0}


aspects_module.position_provider = demo_provider
