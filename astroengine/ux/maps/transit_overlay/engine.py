"""Position engine powering the transit ↔ natal overlay."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from astroengine.engine.ephe_runtime import init_ephe
from astroengine.ephemeris.swe import has_swe, swe

from ....chart.config import ChartConfig
from ....chart.natal import ChartLocation
from ....core.bodies import canonical_name
from ....core.time import ensure_utc
from ....ephemeris.swisseph_adapter import SwissEphemerisAdapter
from ....providers.swisseph_adapter import (
    VariantConfig as ProviderVariantConfig,
)
from ....providers.swisseph_adapter import (
    position_vec,
    position_with_variants,
)

__all__ = [
    "OverlayBodyState",
    "OverlayFrame",
    "OverlayOptions",
    "OverlayRequest",
    "TransitOverlayResult",
    "compute_overlay_frames",
]


@dataclass(frozen=True)
class OverlayOptions:
    """Options controlling ephemeris and orb policy for the overlay."""

    eph_source: str = "swiss"
    zodiac: str = "tropical"
    ayanamsha: str | None = None
    house_system: str = "placidus"
    nodes_variant: str = "mean"
    lilith_variant: str = "mean"
    orb_conjunction: float | None = None
    orb_opposition: float | None = None
    orb_overrides: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "eph_source", (self.eph_source or "swiss").lower())
        object.__setattr__(self, "zodiac", (self.zodiac or "tropical").lower())
        object.__setattr__(self, "house_system", (self.house_system or "placidus").lower())
        object.__setattr__(self, "nodes_variant", (self.nodes_variant or "mean").lower())
        object.__setattr__(self, "lilith_variant", (self.lilith_variant or "mean").lower())
        if self.orb_conjunction is not None:
            object.__setattr__(self, "orb_conjunction", float(self.orb_conjunction))
        if self.orb_opposition is not None:
            object.__setattr__(self, "orb_opposition", float(self.orb_opposition))
        overrides: dict[str, float] = {}
        for key, value in dict(self.orb_overrides or {}).items():
            canonical = canonical_name(str(key))
            overrides[canonical] = float(value)
        object.__setattr__(self, "orb_overrides", overrides)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | None) -> OverlayOptions:
        if payload is None:
            return cls()
        if isinstance(payload, OverlayOptions):
            return payload
        data = dict(payload)
        orbs_deg = data.get("orbs_deg")
        conj = data.get("orb_conjunction")
        opp = data.get("orb_opposition")
        if isinstance(orbs_deg, Mapping):
            conj = orbs_deg.get("conj", conj)
            opp = orbs_deg.get("opp", opp)
        overrides = data.get("orb_overrides")
        if isinstance(overrides, Mapping):
            overrides_map = {str(k): float(v) for k, v in overrides.items()}
        else:
            overrides_map = {}
        ayanamsha = data.get("ayanamsha")
        return cls(
            eph_source=str(data.get("eph_source", "swiss")),
            zodiac=str(data.get("zodiac", "tropical")),
            ayanamsha=str(ayanamsha) if ayanamsha is not None else None,
            house_system=str(data.get("house_system", "placidus")),
            nodes_variant=str(data.get("nodes_variant", "mean")),
            lilith_variant=str(data.get("lilith_variant", "mean")),
            orb_conjunction=float(conj) if conj is not None else None,
            orb_opposition=float(opp) if opp is not None else None,
            orb_overrides=overrides_map,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "eph_source": self.eph_source,
            "zodiac": self.zodiac,
            "house_system": self.house_system,
            "nodes_variant": self.nodes_variant,
            "lilith_variant": self.lilith_variant,
        }
        if self.ayanamsha is not None:
            payload["ayanamsha"] = self.ayanamsha
        if self.orb_conjunction is not None or self.orb_opposition is not None:
            payload["orbs_deg"] = {
                "conj": self.orb_conjunction,
                "opp": self.orb_opposition,
            }
        if self.orb_overrides:
            payload["orb_overrides"] = dict(self.orb_overrides)
        return payload


@dataclass(frozen=True)
class OverlayBodyState:
    """Position snapshot for a single body in a specific frame."""

    id: str
    lon_deg: float
    lat_deg: float
    radius_au: float
    speed_lon_deg_per_day: float
    speed_lat_deg_per_day: float
    speed_radius_au_per_day: float
    retrograde: bool
    frame: str
    metadata: Mapping[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "lon_deg": self.lon_deg,
            "lat_deg": self.lat_deg,
            "radius_au": self.radius_au,
            "speed_lon_deg_per_day": self.speed_lon_deg_per_day,
            "speed_lat_deg_per_day": self.speed_lat_deg_per_day,
            "speed_radius_au_per_day": self.speed_radius_au_per_day,
            "retrograde": self.retrograde,
            "frame": self.frame,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class OverlayFrame:
    """Collection of heliocentric and geocentric placements for a timestamp."""

    timestamp: datetime
    heliocentric: Mapping[str, OverlayBodyState]
    geocentric: Mapping[str, OverlayBodyState]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "heliocentric": {k: v.to_dict() for k, v in self.heliocentric.items()},
            "geocentric": {k: v.to_dict() for k, v in self.geocentric.items()},
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class OverlayRequest:
    """Input required to compute an overlay."""

    birth_dt: datetime
    birth_location: ChartLocation
    transit_dt: datetime
    bodies: Sequence[str]
    options: OverlayOptions | Mapping[str, object] | None = None


@dataclass(frozen=True)
class TransitOverlayResult:
    """Bundle containing natal and transit frames plus provenance."""

    natal: OverlayFrame
    transit: OverlayFrame
    options: OverlayOptions

    def to_dict(self) -> dict[str, object]:
        return {
            "natal": self.natal.to_dict(),
            "transit": self.transit.to_dict(),
            "options": self.options.to_dict(),
        }


def compute_overlay_frames(
    request: OverlayRequest,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> TransitOverlayResult:
    """Compute natal and transit frames for ``request``."""

    options = OverlayOptions.from_mapping(request.options)
    if options.eph_source != "swiss":
        raise ValueError("Only Swiss Ephemeris calculations are supported for overlays")
    _ensure_swisseph()
    adapter = adapter or _adapter_from_options(options)

    bodies = _normalize_bodies(request.bodies)
    natal_frame = _build_frame(adapter, request.birth_dt, request.birth_location, bodies, options)
    transit_frame = _build_frame(adapter, request.transit_dt, request.birth_location, bodies, options)
    return TransitOverlayResult(natal=natal_frame, transit=transit_frame, options=options)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PLANET_CODES: dict[str, int] = {}
if has_swe():  # pragma: no branch - evaluated once at import time
    swe_module = swe()
    for name in (
        "sun",
        "moon",
        "mercury",
        "venus",
        "earth",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
    ):
        attr = name.upper()
        code = getattr(swe_module, attr, None)
        if code is not None:
            _PLANET_CODES[name] = int(code)
    chiron = getattr(swe_module, "CHIRON", None)
    if chiron is not None:
        _PLANET_CODES["chiron"] = int(chiron)


def _ensure_swisseph() -> None:
    if swe is None:
        raise ModuleNotFoundError(
            "pyswisseph is required for the transit overlay. Install the 'pyswisseph' extra."
        )


_ADAPTER_CACHE: dict[tuple[str, str | None, str, str, str], SwissEphemerisAdapter] = {}


def _adapter_from_options(options: OverlayOptions) -> SwissEphemerisAdapter:
    key = (
        options.zodiac,
        options.ayanamsha,
        options.house_system,
        options.nodes_variant,
        options.lilith_variant,
    )
    try:
        return _ADAPTER_CACHE[key]
    except KeyError:
        config = ChartConfig(
            zodiac=options.zodiac,
            ayanamsha=options.ayanamsha,
            house_system=options.house_system,
            nodes_variant=options.nodes_variant,
            lilith_variant=options.lilith_variant,
        )
        adapter = SwissEphemerisAdapter.from_chart_config(config)
        _ADAPTER_CACHE[key] = adapter
        return adapter


def _normalize_datetime(moment: datetime) -> datetime:
    normalized = ensure_utc(moment)
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=UTC)
    return normalized


def _normalize_bodies(bodies: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for name in bodies:
        canonical = canonical_name(name)
        if not canonical or canonical in seen:
            continue
        ordered.append(canonical)
        seen.add(canonical)
    return tuple(ordered)


def _build_frame(
    adapter: SwissEphemerisAdapter,
    moment: datetime,
    location: ChartLocation,
    bodies: Sequence[str],
    options: OverlayOptions,
) -> OverlayFrame:
    timestamp = _normalize_datetime(moment)
    jd_ut = adapter.julian_day(timestamp)

    heliocentric: dict[str, OverlayBodyState] = {}
    for body in bodies:
        values = _position_for_body(body, jd_ut, options, helio=True)
        if values is None:
            continue
        heliocentric[body] = _state_from_values(body, values, frame="heliocentric")

    geocentric: dict[str, OverlayBodyState] = {}
    angles_requested = False
    for body in bodies:
        if body in {"asc", "mc"}:
            angles_requested = True
            continue
        values = _position_for_body(body, jd_ut, options, helio=False)
        if values is None:
            continue
        geocentric[body] = _state_from_values(body, values, frame="geocentric")

    metadata: dict[str, object] = {}
    if angles_requested:
        houses = adapter.houses(jd_ut, location.latitude, location.longitude, system=options.house_system)
        metadata["houses"] = houses.to_dict()
        if "asc" in bodies:
            geocentric["asc"] = _state_from_values(
                "asc",
                (houses.ascendant % 360.0, 0.0, 1.0, 0.0, 0.0, 0.0),
                frame="geocentric",
                metadata={"kind": "angle"},
            )
        if "mc" in bodies:
            geocentric["mc"] = _state_from_values(
                "mc",
                (houses.midheaven % 360.0, 0.0, 1.0, 0.0, 0.0, 0.0),
                frame="geocentric",
                metadata={"kind": "angle"},
            )

    return OverlayFrame(
        timestamp=timestamp,
        heliocentric=heliocentric,
        geocentric=geocentric,
        metadata=metadata,
    )


@lru_cache(maxsize=32768)
def _cached_planet_position(body_code: int, jd_ut: float, flags: int) -> tuple[float, float, float, float, float, float]:
    values = position_vec(body_code, jd_ut, flags=flags)
    lon, lat, dist, lon_spd, lat_spd, dist_spd = values
    return (lon % 360.0, lat, dist, lon_spd, lat_spd, dist_spd)


@lru_cache(maxsize=32768)
def _cached_variant_position(
    name: str,
    jd_ut: float,
    nodes_variant: str,
    lilith_variant: str,
    flags: int,
) -> tuple[float, float, float, float, float, float]:
    config = ProviderVariantConfig(nodes_variant=nodes_variant, lilith_variant=lilith_variant)
    values = position_with_variants(name, jd_ut, config, flags=flags)
    lon, lat, dist, lon_spd, lat_spd, dist_spd = values
    return (lon % 360.0, lat, dist, lon_spd, lat_spd, dist_spd)


def _position_for_body(
    name: str,
    jd_ut: float,
    options: OverlayOptions,
    *,
    helio: bool,
) -> tuple[float, float, float, float, float, float] | None:
    if not has_swe():
        return None
    canonical = canonical_name(name)
    if not canonical:
        return None
    if helio and canonical not in _PLANET_CODES:
        return None
    base_flags = init_ephe()
    swe_module = swe()
    flags = int(base_flags | getattr(swe_module, "FLG_SPEED", 0))
    if helio:
        flags |= int(getattr(swe_module, "FLG_HELCTR", 0))
    if canonical in _PLANET_CODES:
        return _cached_planet_position(_PLANET_CODES[canonical], jd_ut, flags)
    return _cached_variant_position(
        canonical,
        jd_ut,
        options.nodes_variant,
        options.lilith_variant,
        flags,
    )


def _state_from_values(
    body: str,
    values: tuple[float, float, float, float, float, float],
    *,
    frame: str,
    metadata: Mapping[str, object] | None = None,
) -> OverlayBodyState:
    lon, lat, dist, lon_spd, lat_spd, dist_spd = values
    return OverlayBodyState(
        id=body,
        lon_deg=lon % 360.0,
        lat_deg=lat,
        radius_au=dist,
        speed_lon_deg_per_day=lon_spd,
        speed_lat_deg_per_day=lat_spd,
        speed_radius_au_per_day=dist_spd,
        retrograde=lon_spd < 0.0,
        frame=frame,
        metadata=metadata,
    )
