"""Lightweight wrapper around Swiss Ephemeris house calculations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from ...ephemeris import HousePositions, SwissEphemerisAdapter

__all__ = ["GeoLoc", "HousesResult", "compute_angles_houses"]


@dataclass(frozen=True)
class GeoLoc:
    """Geographic location used when computing angles/houses."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.latitude_deg, self.longitude_deg, self.elevation_m)


@dataclass(frozen=True)
class HousesResult:
    """Structured representation of house cusps and angles."""

    system: str
    ascendant: float
    midheaven: float
    cusps: tuple[float, ...]
    metadata: Mapping[str, object]

    def to_mapping(self) -> dict[str, object]:
        return {
            "system": self.system,
            "ascendant": self.ascendant,
            "midheaven": self.midheaven,
            "cusps": self.cusps,
            "metadata": dict(self.metadata),
        }


def _ensure_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def compute_angles_houses(
    moment: datetime,
    location: GeoLoc,
    *,
    system: str,
    adapter: SwissEphemerisAdapter | None = None,
) -> HousesResult:
    """Compute ascendant, midheaven, and house cusps for ``moment``."""

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    moment_utc = _ensure_utc(moment)
    jd = adapter.julian_day(moment_utc)
    house_positions: HousePositions = adapter.houses(
        jd,
        location.latitude_deg,
        location.longitude_deg,
        system=system,
    )
    metadata = dict(house_positions.provenance or {})
    if house_positions.fallback_from is not None:
        metadata["fallback"] = {
            "from": house_positions.fallback_from,
            "reason": house_positions.fallback_reason,
        }
    return HousesResult(
        system=house_positions.system_name or house_positions.system,
        ascendant=house_positions.ascendant % 360.0,
        midheaven=house_positions.midheaven % 360.0,
        cusps=tuple(float(c) % 360.0 for c in house_positions.cusps),
        metadata=metadata,
    )
