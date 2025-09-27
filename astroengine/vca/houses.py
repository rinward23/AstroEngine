from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import math
import weakref
from typing import Any, Mapping, Sequence

import yaml

from ..chart.config import ChartConfig
from ..chart.natal import DEFAULT_BODIES, ChartLocation
from ..core.bodies import canonical_name
from ..ephemeris import HousePositions, SwissEphemerisAdapter
from ..infrastructure.paths import profiles_dir

__all__ = [
    "DomainW",
    "HouseSystem",
    "load_house_profile",
    "domain_for_house",
    "house_of",
    "weights_for_body",
    "blend",
]


@dataclass(frozen=True)
class DomainW:
    """Container for normalized Mind/Body/Spirit weights."""

    Mind: float
    Body: float
    Spirit: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "Mind", float(self.Mind))
        object.__setattr__(self, "Body", float(self.Body))
        object.__setattr__(self, "Spirit", float(self.Spirit))

    def total(self) -> float:
        return self.Mind + self.Body + self.Spirit

    def normalized(self) -> DomainW:
        total = self.total()
        if not math.isfinite(total) or total <= 0:
            return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
        return DomainW(self.Mind / total, self.Body / total, self.Spirit / total)

    def scaled(self, factor: float) -> DomainW:
        return DomainW(self.Mind * factor, self.Body * factor, self.Spirit * factor)

    def weighted(self, factor: float) -> DomainW:
        return DomainW(self.Mind * factor, self.Body * factor, self.Spirit * factor)


class HouseSystem(str):
    PLACIDUS = "placidus"
    WHOLE_SIGN = "whole_sign"
    EQUAL = "equal"
    KOCH = "koch"


class _ProfileDict(dict[int, DomainW]):
    __slots__ = ("__weakref__",)


_DEFAULT_PROFILE: tuple[_ProfileDict, dict[str, dict[str, Any]]] | None = None
_PROFILE_META: dict[int, dict[str, dict[str, Any]]] = {}
_PROFILE_META_REFS: dict[int, weakref.ReferenceType[_ProfileDict]] = {}


def _default_profile_path() -> Path:
    return profiles_dir() / "domains" / "houses.yaml"


def _coerce_domain(entry: Mapping[str, Any]) -> DomainW:
    mind = float(entry.get("Mind", entry.get("mind", 0.0)))
    body = float(entry.get("Body", entry.get("body", 0.0)))
    spirit = float(entry.get("Spirit", entry.get("spirit", 0.0)))
    total = mind + body + spirit
    if not math.isfinite(total) or total <= 0:
        return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    return DomainW(mind / total, body / total, spirit / total)


def load_house_profile(
    path: str | None = None,
) -> tuple[dict[int, DomainW], dict[str, dict[str, Any]]]:
    profile_path = Path(path) if path else _default_profile_path()
    data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}

    profile: _ProfileDict = _ProfileDict()
    meta: dict[str, dict[str, Any]] = {}
    for key, value in data.items():
        if isinstance(key, int) or (isinstance(key, str) and key.strip().isdigit()):
            idx = int(key)
            if isinstance(value, Mapping):
                profile[idx] = _coerce_domain(value)
            else:
                profile[idx] = DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
            continue
        if isinstance(value, Mapping):
            meta[str(key)] = dict(value)

    global _DEFAULT_PROFILE
    _DEFAULT_PROFILE = (profile, meta)
    key = id(profile)
    _PROFILE_META[key] = meta

    def _cleanup(_ref, lookup: int = key) -> None:
        _PROFILE_META.pop(lookup, None)
        _PROFILE_META_REFS.pop(lookup, None)

    _PROFILE_META_REFS[key] = weakref.ref(profile, _cleanup)
    return profile, meta


def _profile_meta(profile: Mapping[int, DomainW]) -> dict[str, dict[str, Any]]:
    meta = _PROFILE_META.get(id(profile))
    if meta is not None:
        return meta
    if _DEFAULT_PROFILE is None:
        load_house_profile()
    meta = _PROFILE_META.get(id(profile))
    if meta is not None:
        return meta
    default_meta = _DEFAULT_PROFILE[1] if _DEFAULT_PROFILE else {}
    return default_meta


def _classification_factor(house: int, meta: Mapping[str, Any]) -> float:
    factor = 1.0
    for key in ("angular_boost", "succedent_boost", "cadent_boost"):
        entry = meta.get(key)
        if not isinstance(entry, Mapping):
            continue
        houses = entry.get("houses")
        try:
            house_list = [int(item) for item in houses] if houses else []
        except Exception:  # pragma: no cover - defensive
            house_list = []
        if house in house_list:
            try:
                value = float(entry.get("factor", 1.0))
            except (TypeError, ValueError):
                value = 1.0
            factor *= value
    return factor


def _sharpen(domain: DomainW, factor: float) -> DomainW:
    if not math.isfinite(factor) or factor <= 0:
        return domain
    if math.isclose(factor, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        return domain
    components = [max(domain.Mind, 0.0), max(domain.Body, 0.0), max(domain.Spirit, 0.0)]
    adjusted = [value ** factor if value > 0 else 0.0 for value in components]
    total = sum(adjusted)
    if not math.isfinite(total) or total <= 0:
        return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    return DomainW(adjusted[0] / total, adjusted[1] / total, adjusted[2] / total)


def domain_for_house(
    h: int, profile: Mapping[int, DomainW], boosts: Mapping[str, dict[str, Any]] | None
) -> DomainW:
    house = int(h)
    base = profile.get(house)
    if base is None:
        return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    meta = boosts or {}
    factor = _classification_factor(house, meta)
    return _sharpen(base, factor)


def _ensure_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return None
        token = token.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(token)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def _extract_moment(chart: Any) -> datetime | None:
    candidate = getattr(chart, "moment", None)
    if candidate is None and isinstance(chart, Mapping):
        candidate = chart.get("moment") or chart.get("ts") or chart.get("utc")
    return _ensure_datetime(candidate)


def _extract_location(chart: Any) -> ChartLocation | None:
    candidate = getattr(chart, "location", None)
    if candidate is None and isinstance(chart, Mapping):
        candidate = chart.get("location")
    if isinstance(candidate, ChartLocation):
        return candidate
    if isinstance(candidate, Mapping):
        lat = candidate.get("latitude", candidate.get("lat"))
        lon = candidate.get("longitude", candidate.get("lon"))
        if lat is None or lon is None:
            return None
        return ChartLocation(latitude=float(lat), longitude=float(lon))
    lat = getattr(chart, "lat", None)
    lon = getattr(chart, "lon", None)
    if lat is None or lon is None:
        if isinstance(chart, Mapping):
            lat = chart.get("lat")
            lon = chart.get("lon")
    if lat is None or lon is None:
        return None
    return ChartLocation(latitude=float(lat), longitude=float(lon))


def _coerce_house_positions(value: Any) -> HousePositions | None:
    if isinstance(value, HousePositions):
        return value
    if not isinstance(value, Mapping):
        return None
    cusps = value.get("cusps")
    if not cusps:
        return None
    try:
        cusp_tuple = tuple(float(x) % 360.0 for x in cusps)
    except Exception:
        return None
    asc = value.get("ascendant", value.get("asc"))
    mc = value.get("midheaven", value.get("mc"))
    if asc is None or mc is None:
        return None
    system = str(value.get("system", value.get("system_name", "placidus")))
    return HousePositions(
        system=system.lower(),
        cusps=cusp_tuple,
        ascendant=float(asc) % 360.0,
        midheaven=float(mc) % 360.0,
        system_name=value.get("system_name"),
        requested_system=value.get("requested_system"),
        fallback_from=value.get("fallback_from"),
        fallback_reason=value.get("fallback_reason"),
        provenance=value.get("provenance"),
    )


def _compute_houses(moment: datetime, location: ChartLocation, system: str) -> HousePositions:
    chart_config = ChartConfig(house_system=system)
    adapter = SwissEphemerisAdapter.from_chart_config(chart_config)
    jd = adapter.julian_day(moment)
    return adapter.houses(jd, location.latitude, location.longitude, system=system)


def _resolve_houses(chart: Any, system: str) -> HousePositions | None:
    houses = _coerce_house_positions(getattr(chart, "houses", None))
    if houses is None and isinstance(chart, Mapping):
        houses = _coerce_house_positions(chart.get("houses"))
    if houses is not None and houses.cusps:
        if system and houses.system.lower() != system.lower():
            moment = _extract_moment(chart)
            location = _extract_location(chart)
            if moment and location:
                return _compute_houses(moment, location, system)
        return houses
    moment = _extract_moment(chart)
    location = _extract_location(chart)
    if moment and location:
        return _compute_houses(moment, location, system)
    return None


def _position_mapping(chart: Any) -> Mapping[str, Any] | None:
    positions = getattr(chart, "positions", None)
    if positions is None and isinstance(chart, Mapping):
        positions = chart.get("positions")
    return positions if isinstance(positions, Mapping) else None


def _extract_longitude(value: Any) -> float | None:
    if hasattr(value, "longitude"):
        try:
            return float(getattr(value, "longitude")) % 360.0
        except Exception:  # pragma: no cover - defensive
            return None
    if isinstance(value, Mapping):
        for key in ("lon", "longitude"):
            if key in value:
                try:
                    return float(value[key]) % 360.0
                except Exception:  # pragma: no cover - defensive
                    continue
    if isinstance(value, (int, float)):
        return float(value) % 360.0
    return None


def _body_longitude(chart: Any, body: str) -> float | None:
    positions = _position_mapping(chart)
    if positions:
        target = canonical_name(body)
        for name, entry in positions.items():
            if canonical_name(str(name)) == target:
                lon = _extract_longitude(entry)
                if lon is not None:
                    return lon
    moment = _extract_moment(chart)
    location = _extract_location(chart)
    if moment is None or location is None:
        return None
    canonical = canonical_name(body)
    code = DEFAULT_BODIES.get(body) or DEFAULT_BODIES.get(body.capitalize())
    if code is None:
        for key, value in DEFAULT_BODIES.items():
            if canonical_name(key) == canonical:
                code = value
                break
    if code is None:
        return None
    adapter = SwissEphemerisAdapter.from_chart_config(ChartConfig())
    jd = adapter.julian_day(moment)
    position = adapter.body_position(jd, code, body_name=body)
    return float(position.longitude) % 360.0


def _house_index(cusps: Sequence[float], longitude: float) -> int:
    if not cusps:
        raise ValueError("No house cusps available")
    lon = float(longitude) % 360.0
    cusp_list = [float(c) % 360.0 for c in cusps[:12]]
    total = len(cusp_list)
    if total < 12:
        raise ValueError("Insufficient house cusps")
    for idx in range(total):
        start = cusp_list[idx]
        end = cusp_list[(idx + 1) % total]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def house_of(chart: Any, body: str, system: str) -> int:
    normalized_system = (system or HouseSystem.PLACIDUS).lower()
    houses = _resolve_houses(chart, normalized_system)
    if houses is None:
        raise ValueError("Unable to compute houses for chart")
    longitude = _body_longitude(chart, body)
    if longitude is None:
        raise ValueError(f"Missing longitude for body '{body}'")
    return _house_index(houses.cusps, longitude)


def weights_for_body(
    chart: Any,
    body: str,
    system: str,
    profile: Mapping[int, DomainW] | None = None,
) -> DomainW:
    try:
        profile_map, meta = (profile, _profile_meta(profile)) if profile else load_house_profile()
    except Exception:  # pragma: no cover - defensive fallback
        profile_map, meta = load_house_profile()
    try:
        house = house_of(chart, body, system)
    except Exception:
        return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    return domain_for_house(house, profile_map, meta)


def blend(weights: Sequence[DomainW], alphas: Sequence[float] | None = None) -> DomainW:
    filtered = [w for w in weights if isinstance(w, DomainW)]
    if not filtered:
        return DomainW(1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    if alphas is None:
        factors = [1.0 for _ in filtered]
    else:
        factors = [float(a) for a in alphas[: len(filtered)]]
        if len(factors) < len(filtered):
            factors.extend([1.0] * (len(filtered) - len(factors)))
    total_factor = sum(max(f, 0.0) for f in factors)
    if total_factor <= 0:
        factors = [1.0 for _ in filtered]
        total_factor = float(len(filtered))
    mind = sum(w.Mind * f for w, f in zip(filtered, factors))
    body = sum(w.Body * f for w, f in zip(filtered, factors))
    spirit = sum(w.Spirit * f for w, f in zip(filtered, factors))
    blended = DomainW(mind / total_factor, body / total_factor, spirit / total_factor)
    return blended.normalized()
