"""System doctor API endpoint returning runtime diagnostics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from astroengine.config import Settings
from astroengine.observability import run_system_doctor

router = APIRouter(prefix="/v1/doctor", tags=["system"])


def _extract_settings(request: Request) -> Settings | None:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else None


@router.get(
    "",
    summary="Run system doctor",
    description="Return Swiss ephemeris, database, migration, and cache diagnostics.",
)
async def system_doctor(request: Request) -> dict[str, Any]:
    """Return the aggregated diagnostics report."""

    return run_system_doctor(settings=_extract_settings(request))


__all__ = ["router"]
