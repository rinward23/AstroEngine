"""Narrative mix management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from astroengine.config import (
    NarrativeMixCfg,
    Settings,
    compose_narrative_from_mix,
    list_narrative_profiles,
    save_mix_as_user_narrative_profile,
    save_settings,
    settings as runtime_settings,
)

router = APIRouter(prefix="/v1/narrative-mix", tags=["narrative-mix"])


class MixPayload(BaseModel):
    """Request payload for applying a narrative mix."""

    profiles: dict[str, float]
    normalize: bool = True
    save_as: str | None = None


@router.get("/")
async def get_mix() -> dict[str, object]:
    """Return the persisted mix configuration and the effective narrative."""

    persisted = runtime_settings.persisted()
    effective = compose_narrative_from_mix(persisted, persisted.narrative_mix)
    return {
        "mix": persisted.narrative_mix.model_dump(),
        "effective": effective.model_dump(),
        "available": list_narrative_profiles(),
    }


@router.post("/apply", response_model=Settings)
async def apply_mix(payload: MixPayload) -> Settings:
    """Persist a new mix, optionally saving it as a reusable profile."""

    config = runtime_settings.persisted()
    positive = {name: float(weight) for name, weight in payload.profiles.items() if weight > 0}
    if not positive:
        raise HTTPException(status_code=422, detail="At least one profile must have a positive weight.")

    config.narrative_mix = NarrativeMixCfg(
        enabled=True,
        profiles=positive,
        normalize=payload.normalize,
    )

    effective = compose_narrative_from_mix(config, config.narrative_mix)
    config.narrative = effective
    save_settings(config)
    runtime_settings.cache_persisted(config)
    if payload.save_as:
        save_mix_as_user_narrative_profile(payload.save_as, config, config.narrative_mix)
    return config
