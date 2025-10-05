
"""FastAPI application exposing AstroEngine Plus CRUD services."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.observability import configure_observability

from app.routers import (
    aspects_router,
    electional_router,
    events_router,
    interpret_router,
    lots_router,
    policies_router,
    reports_router,
    relationship_router,
    transits_router,
)
from app.routers.aspects import (  # re-exported for convenience
    clear_position_provider,
    configure_position_provider,
)

app = FastAPI(title="AstroEngine Plus API")
configure_observability(app)
app.include_router(aspects_router)
app.include_router(electional_router)
app.include_router(events_router)
app.include_router(transits_router)
app.include_router(policies_router)
app.include_router(lots_router)
app.include_router(relationship_router)
app.include_router(interpret_router)
app.include_router(reports_router)


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Apply default security headers to every HTTP response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=()"
    )
    if request.method == "GET":
        response.headers.setdefault("Cache-Control", "public, max-age=60")
    return response


__all__ = ["app", "configure_position_provider", "clear_position_provider"]

