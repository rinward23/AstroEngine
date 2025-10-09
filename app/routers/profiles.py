"""Profiles API endpoints for AstroEngine settings management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from astroengine.config import (
    Settings,
    apply_profile_overlay,
    delete_user_profile,
    list_profiles,
    load_profile_overlay,
    save_settings,
    save_user_profile,
    settings as runtime_settings,
)

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])


class NamedSettings(BaseModel):
    """Bundle a settings payload with a profile name."""

    name: str
    settings: Settings


@router.get("")
async def get_profiles() -> dict[str, list[str]]:
    """Return the available built-in and user-defined profiles."""

    return list_profiles()


@router.get("/{name}", response_model=Settings)
async def get_profile(name: str) -> Settings:
    """Return the settings that would result from applying ``name``."""

    try:
        overlay = load_profile_overlay(name)
    except FileNotFoundError as exc:  # pragma: no cover - defensive mapping
        raise HTTPException(status_code=404, detail="profile not found") from exc
    base = runtime_settings.persisted()
    return apply_profile_overlay(base, overlay)


@router.post("/{name}/apply", response_model=Settings)
async def apply_profile(name: str) -> Settings:
    """Apply ``name`` to the persisted settings and return the new state."""

    try:
        overlay = load_profile_overlay(name)
    except FileNotFoundError as exc:  # pragma: no cover - defensive mapping
        raise HTTPException(status_code=404, detail="profile not found") from exc
    current = runtime_settings.persisted()
    merged = apply_profile_overlay(current, overlay)
    save_settings(merged)
    runtime_settings.cache_persisted(merged)
    return merged


@router.post("", response_model=dict)
async def create_profile(payload: NamedSettings) -> dict[str, str]:
    """Persist a new user profile."""

    saved_path = save_user_profile(payload.name, payload.settings)
    return {"saved": str(saved_path)}


@router.put("/{name}")
async def update_profile(name: str, settings: Settings) -> dict[str, str]:
    """Replace the stored profile ``name`` with ``settings``."""

    saved_path = save_user_profile(name, settings)
    return {"saved": str(saved_path)}


@router.delete("/{name}")
async def delete_profile_api(name: str) -> dict[str, str]:
    """Delete the persisted user profile if it exists."""

    if delete_user_profile(name):
        return {"deleted": name}
    raise HTTPException(status_code=404, detail="not found")
