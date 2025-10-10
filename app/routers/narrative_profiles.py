"""API endpoints for managing narrative profile overlays."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from astroengine.config import (
    NarrativeCfg,
    Settings,
    apply_narrative_profile_overlay,
    delete_user_narrative_profile,
    list_narrative_profiles,
    load_narrative_profile_overlay,
    save_settings,
    save_user_narrative_profile,
)
from astroengine.runtime_config import runtime_settings

router = APIRouter(prefix="/v1/narrative-profiles", tags=["narrative-profiles"])


class NamedNarrative(BaseModel):
    """Payload for creating a named narrative profile."""

    name: str
    narrative: NarrativeCfg


@router.get("")
async def get_profiles() -> dict[str, list[str]]:
    """Return the list of built-in and user-defined narrative profiles."""

    return list_narrative_profiles()


@router.get("/{name}", response_model=NarrativeCfg)
async def get_profile(name: str) -> NarrativeCfg:
    """Return the resolved narrative configuration for the requested profile."""

    try:
        overlay = load_narrative_profile_overlay(name)
    except FileNotFoundError as exc:  # pragma: no cover - FastAPI handles mapping
        raise HTTPException(status_code=404, detail="profile not found") from exc
    current = runtime_settings.persisted()
    updated = apply_narrative_profile_overlay(current, overlay)
    return updated.narrative


@router.post("/{name}/apply", response_model=Settings)
async def apply_profile(name: str) -> Settings:
    """Apply the given profile to persisted settings and return the new state."""

    try:
        overlay = load_narrative_profile_overlay(name)
    except FileNotFoundError as exc:  # pragma: no cover - FastAPI handles mapping
        raise HTTPException(status_code=404, detail="profile not found") from exc
    current = runtime_settings.persisted()
    updated = apply_narrative_profile_overlay(current, overlay)
    save_settings(updated)
    runtime_settings.cache_persisted(updated)
    return updated


@router.post("", response_model=dict)
async def create_profile(payload: NamedNarrative) -> dict[str, str]:
    """Create a user-defined narrative profile overlay."""

    saved_path = save_user_narrative_profile(payload.name, payload.narrative)
    return {"saved": str(saved_path)}


@router.put("/{name}")
async def update_profile(name: str, narrative: NarrativeCfg) -> dict[str, str]:
    """Overwrite the narrative overlay stored for ``name``."""

    saved_path = save_user_narrative_profile(name, narrative)
    return {"saved": str(saved_path)}


@router.delete("/{name}")
async def delete_profile_api(name: str) -> dict[str, str]:
    """Remove the requested user-defined narrative profile."""

    if delete_user_narrative_profile(name):
        return {"deleted": name}
    raise HTTPException(status_code=404, detail="not found")


__all__ = ["router"]

