from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterator, Mapping

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRouter

from app.routers import clear_position_provider, configure_position_provider
from app.routers import aspects as aspects_module
from app.routers.aspects import PositionProvider


@dataclass
class LinearEphemeris:
    """Linear ephemeris used by API tests to generate deterministic positions."""

    t0: datetime
    base: Mapping[str, float]
    rates: Mapping[str, float]

    def __call__(self, ts: datetime) -> Dict[str, float]:
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            key: (self.base.get(key, 0.0) + self.rates.get(key, 0.0) * dt_days) % 360.0
            for key in self.base
        }


def build_app(*routers: APIRouter) -> FastAPI:
    """Build a FastAPI app with the provided routers included."""

    app = FastAPI(default_response_class=ORJSONResponse)
    for router in routers:
        app.include_router(router)
    return app


@contextmanager
def patch_aspects_provider(provider: PositionProvider) -> Iterator[PositionProvider]:
    """Temporarily register a position provider for aspect scans."""

    previous = aspects_module.position_provider
    configure_position_provider(provider)
    try:
        yield provider
    finally:
        if previous is None:
            clear_position_provider()
        else:
            configure_position_provider(previous)
