"""Health and readiness endpoints for deployment probes."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db.session import session_scope
from astroengine.cache import positions_cache
from astroengine.infrastructure.storage.sqlite import apply_default_pragmas
from astroengine.ephemeris.utils import get_se_ephe_path

router = APIRouter(tags=["observability"])


@router.get("/healthz", summary="Lightweight liveness probe")
async def healthz() -> dict[str, str]:
    """Return success when the API process is running."""

    return {"status": "ok"}


def _check_database() -> dict[str, Any]:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive to surface readiness failures
        return {"status": "error", "error": str(exc)}
    return {"status": "ok"}


def _check_cache() -> dict[str, Any]:
    try:
        connection = sqlite3.connect(str(positions_cache.DB))
        apply_default_pragmas(connection)
        try:
            connection.execute("SELECT 1")
        finally:
            connection.close()
    except Exception as exc:  # pragma: no cover - defensive logging path
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "path": str(positions_cache.DB)}


def _check_ephemeris() -> dict[str, Any]:
    path = get_se_ephe_path()
    if path:
        return {"status": "ok", "path": path}
    return {"status": "error", "error": "Swiss ephemeris path not configured"}


@router.get("/readyz", summary="Readiness probe with backing service checks")
async def readyz() -> dict[str, Any]:
    """Validate dependencies required for serving real astrology data."""

    checks = {
        "database": _check_database(),
        "cache": _check_cache(),
        "swiss_ephemeris": _check_ephemeris(),
    }
    failures = {name: result for name, result in checks.items() if result["status"] != "ok"}
    if failures:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "checks": checks},
        )
    return {"status": "ok", "checks": checks}


__all__ = ["router"]
