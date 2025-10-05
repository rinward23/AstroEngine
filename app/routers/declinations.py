"""Declination aspect detection endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from fastapi import APIRouter, Request

from astroengine.analysis import declination_aspects, get_declinations
from astroengine.config import default_settings
from app.schemas.declinations import (
    DeclinationAspectHit,
    DeclinationRequest,
    DeclinationResponse,
)

router = APIRouter(prefix="/declinations", tags=["Declinations"])


@dataclass(slots=True)
class _InlineChart:
    """Lightweight container mirroring chart attributes required for declinations."""

    positions: Dict[str, Dict[str, float]]
    julian_day: float | None
    zodiac: str | None
    ayanamsa: str | None
    metadata: Dict[str, object]

    def __post_init__(self) -> None:
        # Provide both ayanamsa spellings expected by downstream helpers.
        object.__setattr__(self, "ayanamsha", self.ayanamsa)


@router.post(
    "/aspects",
    response_model=DeclinationResponse,
    summary="Detect declination parallels and contraparallels",
    description="Compute declination values and return parallels/contraparallels within the configured orb.",
    operation_id="declinations_aspects",
)
async def declination_aspects_endpoint(
    request: Request, payload: DeclinationRequest
) -> DeclinationResponse:
    """Return declination metadata and aspect hits for the supplied chart payload."""

    settings = getattr(request.app.state, "settings", default_settings())
    decl_settings = getattr(settings, "declinations", default_settings().declinations)

    orb_value = float(
        payload.orb_deg if payload.orb_deg is not None else decl_settings.orb_deg
    )
    enabled = bool(getattr(decl_settings, "enabled", True))

    metadata: Dict[str, object] = {}
    if payload.nodes_variant is not None:
        metadata["nodes_variant"] = payload.nodes_variant
    if payload.lilith_variant is not None:
        metadata["lilith_variant"] = payload.lilith_variant
    if payload.zodiac is not None:
        metadata["zodiac"] = payload.zodiac

    positions: Dict[str, Dict[str, float]] = {}
    for name, pos in payload.positions.items():
        entry: Dict[str, float] = {}
        if pos.lon is not None:
            entry["longitude"] = float(pos.lon)
            entry["lon"] = float(pos.lon)
        if pos.declination is not None:
            entry["declination"] = float(pos.declination)
        if pos.lat is not None:
            entry["lat"] = float(pos.lat)
        positions[name] = entry

    chart = _InlineChart(
        positions=positions,
        julian_day=float(payload.julian_day) if payload.julian_day is not None else None,
        zodiac=payload.zodiac,
        ayanamsa=payload.ayanamsa,
        metadata=metadata,
    )

    declinations = get_declinations(chart)

    hits = (
        declination_aspects(declinations, orb_deg=orb_value) if enabled else []
    )
    aspect_hits = [
        DeclinationAspectHit(
            body_a=hit.body_a,
            body_b=hit.body_b,
            kind=hit.kind,
            declination_a=hit.declination_a,
            declination_b=hit.declination_b,
            orb=hit.orb,
            delta=hit.delta,
        )
        for hit in hits
    ]

    return DeclinationResponse(
        declinations={name: float(value) for name, value in declinations.items()},
        aspects=aspect_hits,
        orb_deg=orb_value,
        enabled=enabled,
    )


__all__ = ["router"]
