"""Health endpoints for the Plus module."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/system", tags=["system"])


@router.get(
    "/health",
    summary="Health check for Plus modules",
    description="Returns {status:'ok'} if Plus routes are wired.",
    operation_id="checkSystemHealth",
    responses={200: {"description": "Service is ready."}},
)
def health_plus() -> dict[str, str]:
    """Simple readiness probe for Plus features."""
    return {"status": "ok"}
