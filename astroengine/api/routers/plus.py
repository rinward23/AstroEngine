"""Health endpoints for the Plus module."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="", tags=["Plus"])


@router.get(
    "/health/plus",
    summary="Health check for Plus modules",
    description="Returns {status:'ok'} if Plus routes are wired.",
)
def health_plus() -> dict[str, str]:
    """Simple readiness probe for Plus features."""
    return {"status": "ok"}
