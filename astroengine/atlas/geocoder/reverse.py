"""Reverse geocoding helpers for UI hints."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import Iterable, TypedDict

EARTH_RADIUS_KM = 6371.0


class HeatmapHint(TypedDict):
    """Simple payload describing a reverse-geocoding heatmap point."""

    lat: float
    lon: float
    weight: float
    label: str


@dataclass(frozen=True)
class _HeatSeed:
    lat: float
    lon: float
    weight: float
    label: str


def _offset(lat: float, lon: float, km: float, bearing_deg: float) -> tuple[float, float]:
    """Return coordinates ``km`` away from ``lat/lon`` at ``bearing_deg``."""

    # Very small offsets are sufficient for hinting; a simple equirectangular
    # approximation keeps the implementation deterministic without pulling in
    # heavy geographic dependencies.
    delta_lat = (km / EARTH_RADIUS_KM) * (180.0 / 3.141592653589793)
    delta_lon = delta_lat / max(cos(radians(lat)), 0.0001)
    return lat + delta_lat * cos(radians(bearing_deg)), lon + delta_lon * sin(radians(bearing_deg))


def _generate_seeds(lat: float, lon: float) -> Iterable[_HeatSeed]:
    yield _HeatSeed(lat, lon, 1.0, "Primary match")
    for idx, bearing in enumerate((0.0, 90.0, 180.0, 270.0), start=1):
        offset_lat, offset_lon = _offset(lat, lon, km=idx * 5.0, bearing_deg=bearing)
        yield _HeatSeed(offset_lat, offset_lon, max(0.4, 1.0 - idx * 0.15), f"Context radius {idx}")


def heatmap_hints(lat: float, lon: float) -> list[HeatmapHint]:
    """Return heatmap hints centred around the provided coordinate."""

    hints: list[HeatmapHint] = []
    for seed in _generate_seeds(lat, lon):
        hints.append({"lat": seed.lat, "lon": seed.lon, "weight": seed.weight, "label": seed.label})
    return hints
