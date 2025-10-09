"""Settings management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from astroengine.config import Settings, save_settings, settings as runtime_settings

router = APIRouter(prefix="/v1/settings", tags=["settings"])


@router.get("", response_model=Settings)
async def get_settings() -> Settings:
    """Return the current persisted settings."""

    return runtime_settings.persisted()


@router.put("", response_model=Settings)
async def put_settings(settings: Settings) -> Settings:
    """Persist updated settings sent by the client."""

    try:
        save_settings(settings)
        runtime_settings.cache_persisted(settings)
        return settings
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail=str(exc)) from exc

