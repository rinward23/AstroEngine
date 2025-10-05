"""Endpoints exposing catalog-based analysis helpers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...analysis.fixed_stars import load_catalog, star_hits
from ...config import load_settings

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


class FixedStarHit(BaseModel):
    name: str
    delta_deg: float
    longitude_deg: float
    latitude_deg: float
    magnitude: float


class FixedStarResponse(BaseModel):
    enabled: bool
    orb_deg: float
    catalog: str
    hits: list[FixedStarHit]


@router.get(
    "/fixed-stars",
    response_model=FixedStarResponse,
    summary="List fixed stars near a given longitude",
    description="Return fixed stars within the requested orb of the provided ecliptic longitude.",
)
def fixed_star_contacts(
    lon: float = Query(..., description="Ecliptic longitude in degrees."),
    orb: float | None = Query(None, ge=0.0, description="Override orb in degrees."),
    catalog: str | None = Query(
        None,
        description="Optional catalog identifier (defaults to the configured catalog).",
    ),
) -> FixedStarResponse:
    settings = load_settings()
    fs_cfg = getattr(settings, "fixed_stars", None)

    if fs_cfg is None:
        enabled = False
        configured_orb = 0.0
        configured_catalog = catalog or "robson"
    else:
        enabled = fs_cfg.enabled
        configured_orb = float(fs_cfg.orb_deg)
        configured_catalog = (catalog or fs_cfg.catalog or "robson").lower()

    effective_orb = float(configured_orb if orb is None else orb)
    if effective_orb < 0:
        raise HTTPException(status_code=400, detail="Orb must be non-negative")

    if not enabled:
        return FixedStarResponse(
            enabled=False,
            orb_deg=effective_orb,
            catalog=configured_catalog,
            hits=[],
        )

    try:
        hits = star_hits(lon, effective_orb, catalog=configured_catalog)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    catalog_entries = {star.name: star for star in load_catalog(configured_catalog)}
    response_hits = [
        FixedStarHit(
            name=name,
            delta_deg=delta,
            longitude_deg=catalog_entries[name].lon_deg,
            latitude_deg=catalog_entries[name].lat_deg,
            magnitude=catalog_entries[name].mag,
        )
        for name, delta in hits
        if name in catalog_entries
    ]

    return FixedStarResponse(
        enabled=True,
        orb_deg=effective_orb,
        catalog=configured_catalog,
        hits=response_hits,
    )
