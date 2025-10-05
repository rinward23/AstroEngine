"""Declination helpers built on top of Swiss ephemeris data."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from typing import Mapping, MutableMapping, Sequence

from ..astro.declination import ecl_to_dec, is_contraparallel, is_parallel
from ..chart.config import ChartConfig
from ..ephemeris.swisseph_adapter import SwissEphemerisAdapter, get_swisseph

try:  # Optional Swiss Ephemeris dependency
    import swisseph as swe  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled dynamically
    swe = None  # type: ignore[assignment]

__all__ = ["DeclinationAspect", "declination_aspects", "get_declinations"]


@dataclass(frozen=True, slots=True)
class DeclinationAspect:
    """Represents a declination parallel or contraparallel between two bodies."""

    body_a: str
    body_b: str
    kind: str  # "parallel" or "contraparallel"
    declination_a: float
    declination_b: float
    orb: float
    delta: float


_BODY_NAME_TO_ATTR = {
    "sun": "SUN",
    "moon": "MOON",
    "mercury": "MERCURY",
    "venus": "VENUS",
    "mars": "MARS",
    "jupiter": "JUPITER",
    "saturn": "SATURN",
    "uranus": "URANUS",
    "neptune": "NEPTUNE",
    "pluto": "PLUTO",
    "ceres": "CERES",
    "pallas": "PALLAS",
    "juno": "JUNO",
    "vesta": "VESTA",
    "chiron": "CHIRON",
    "true node": "TRUE_NODE",
    "mean node": "MEAN_NODE",
    "north node": "MEAN_NODE",
    "node": "MEAN_NODE",
    "nn": "MEAN_NODE",
    "south node": "MEAN_NODE",
    "descending node": "MEAN_NODE",
    "sn": "MEAN_NODE",
    "mean lilith": "MEAN_APOG",
    "true lilith": "OSCU_APOG",
    "lilith": "MEAN_APOG",
    "black moon lilith": "MEAN_APOG",
}

_NEGATE_DECL = {"south node", "descending node", "sn"}


def _sanitize_name(name: str) -> str:
    return (name or "").strip().lower()


def _resolve_body_code(name: str, swe_module) -> tuple[int, bool] | None:
    normalized = _sanitize_name(name)
    attr = _BODY_NAME_TO_ATTR.get(normalized)
    if attr is None:
        token = normalized.replace("-", " ").replace("/", " ").replace("\t", " ")
        token = "_".join(chunk for chunk in token.split() if chunk)
        attr = token.upper()
    candidates = []
    if attr:
        candidates.append(attr)
        if not attr.startswith("SE_"):
            candidates.append(f"SE_{attr}")
    for candidate in candidates:
        try:
            value = int(getattr(swe_module, candidate))
        except (AttributeError, TypeError, ValueError):
            continue
        negate = normalized in _NEGATE_DECL
        return value, negate
    return None


def _chart_julian_day(chart) -> float | None:
    for attr in ("julian_day", "jd_ut", "jd"):
        value = getattr(chart, attr, None)
        if value is None and isinstance(chart, Mapping):
            value = chart.get(attr)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if isfinite(numeric):
            return numeric
    return None


def _chart_metadata(chart) -> Mapping[str, object] | None:
    meta = getattr(chart, "metadata", None)
    if meta is None and isinstance(chart, Mapping):
        meta = chart.get("metadata")
    return meta if isinstance(meta, Mapping) else None


@lru_cache(maxsize=8)
def _adapter_for_chart(
    zodiac: str,
    ayanamsha: str | None,
    nodes_variant: str | None,
    lilith_variant: str | None,
) -> SwissEphemerisAdapter:
    zodiac_normalized = (zodiac or "tropical").lower()
    ayan_value = ayanamsha if zodiac_normalized == "sidereal" else None
    config = ChartConfig(
        zodiac=zodiac_normalized,
        ayanamsha=ayan_value,
        nodes_variant=(nodes_variant or "mean"),
        lilith_variant=(lilith_variant or "mean"),
    )
    return SwissEphemerisAdapter(chart_config=config)


def _extract_declination(value) -> float | None:
    if hasattr(value, "declination"):
        try:
            val = float(getattr(value, "declination"))
        except (TypeError, ValueError):
            val = None
        if val is not None and isfinite(val):
            return val
    if isinstance(value, Mapping):
        for key in ("declination", "dec", "decl"):
            if key in value:
                try:
                    val = float(value[key])
                except (TypeError, ValueError):
                    continue
                if isfinite(val):
                    return val
    return None


def _extract_longitude(value) -> float | None:
    if hasattr(value, "longitude"):
        try:
            val = float(getattr(value, "longitude"))
        except (TypeError, ValueError):
            val = None
        if val is not None and isfinite(val):
            return val
    if isinstance(value, Mapping):
        for key in ("longitude", "lon", "lambda"):
            if key in value:
                try:
                    val = float(value[key])
                except (TypeError, ValueError):
                    continue
                if isfinite(val):
                    return val
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    return val if isfinite(val) else None


def _declinations_from_positions(
    positions: Mapping[str, object],
    *,
    chart,
) -> MutableMapping[str, float]:
    results: MutableMapping[str, float] = {}

    jd_ut = _chart_julian_day(chart)
    meta = _chart_metadata(chart) or {}
    zodiac = getattr(chart, "zodiac", None) or meta.get("zodiac") or "tropical"
    ayan = getattr(chart, "ayanamsa", None) or getattr(chart, "ayanamsha", None)
    nodes_variant = meta.get("nodes_variant") if isinstance(meta, Mapping) else None
    lilith_variant = meta.get("lilith_variant") if isinstance(meta, Mapping) else None

    swe_module = None
    adapter: SwissEphemerisAdapter | None = None
    if jd_ut is not None and swe is not None:
        try:
            swe_module = get_swisseph()
            adapter = _adapter_for_chart(
                str(zodiac),
                str(ayan) if ayan is not None else None,
                str(nodes_variant) if nodes_variant is not None else None,
                str(lilith_variant) if lilith_variant is not None else None,
            )
        except (ModuleNotFoundError, ValueError):  # pragma: no cover - runtime guard
            swe_module = None
            adapter = None

    for name, value in positions.items():
        decl = _extract_declination(value)
        if decl is None and swe_module is not None and adapter is not None:
            code_info = _resolve_body_code(name, swe_module)
            if code_info is not None:
                code, negate = code_info
                try:
                    pos = adapter.body_position(jd_ut, code, body_name=name)
                except Exception:  # pragma: no cover - defensive fallback
                    pos = None
                if pos is not None:
                    decl = float(pos.declination)
                    if negate:
                        decl = -decl
        if decl is None:
            lon = _extract_longitude(value)
            if lon is not None:
                decl = ecl_to_dec(lon)
        if decl is not None and isfinite(decl):
            results[str(name)] = float(decl)
    return results


def get_declinations(chart) -> dict[str, float]:
    """Return declination values keyed by body name for ``chart``.

    The helper inspects any ``declination`` attribute present on the supplied
    positions, falling back to Swiss Ephemeris equatorial calculations when
    available.  When Swiss Ephemeris is not present, ecliptic longitudes are
    converted using ``ecl_to_dec`` as a last resort.
    """

    positions = getattr(chart, "positions", chart)
    if not isinstance(positions, Mapping):
        raise TypeError("chart.positions must be a mapping of body → position data")
    return dict(_declinations_from_positions(positions, chart=chart))


def declination_aspects(
    declinations: Mapping[str, float],
    orb_deg: float = 0.5,
) -> list[DeclinationAspect]:
    """Return declination parallels/contraparallels within ``orb_deg`` degrees."""

    if not declinations:
        return []

    hits: list[DeclinationAspect] = []
    names: Sequence[str] = sorted(declinations.keys())
    for idx, name_a in enumerate(names):
        dec_a = declinations.get(name_a)
        if dec_a is None or not isfinite(dec_a):
            continue
        for name_b in names[idx + 1 :]:
            dec_b = declinations.get(name_b)
            if dec_b is None or not isfinite(dec_b):
                continue
            delta = dec_a - dec_b
            if is_parallel(dec_a, dec_b, orb_deg):
                orb = abs(delta)
                hits.append(
                    DeclinationAspect(
                        body_a=name_a,
                        body_b=name_b,
                        kind="parallel",
                        declination_a=dec_a,
                        declination_b=dec_b,
                        orb=orb,
                        delta=delta,
                    )
                )
            elif is_contraparallel(dec_a, dec_b, orb_deg):
                sum_delta = dec_a + dec_b
                orb = abs(sum_delta)
                hits.append(
                    DeclinationAspect(
                        body_a=name_a,
                        body_b=name_b,
                        kind="contraparallel",
                        declination_a=dec_a,
                        declination_b=dec_b,
                        orb=orb,
                        delta=sum_delta,
                    )
                )
    hits.sort(key=lambda h: (h.orb, h.body_a.lower(), h.body_b.lower()))
    return hits
