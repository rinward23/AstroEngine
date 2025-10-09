"""Basic service health endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get(
    "/healthz",
    summary="Service readiness probe",
    description="Returns a simple status payload for infrastructure health checks.",
    response_model=dict[str, str],
)
async def health_check() -> dict[str, str]:
    """Return an affirmative status payload for container health probes."""

    return {"status": "ok"}


__all__ = ["router"]

