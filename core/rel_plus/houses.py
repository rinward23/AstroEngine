"""House computation helpers for composite and Davison charts.

This module keeps the Swiss Ephemeris interaction in one place so that both the
API layer and the Streamlit UI can request Asc/MC and house cusps for
relationship charts.  The implementation follows SPEC-B-010:

* Davison charts use the midpoint time and location produced by
  :func:`core.rel_plus.composite.davison_chart` / :class:`DavisonResult`.
* Composite charts are time free; we derive an ARMC midpoint from the natal
  birth events and compute houses with :func:`swe().houses_armc`.
* Systems fall back in the order Placidus → Koch → Porphyry → Regiomontanus →
  Whole Sign, forcing Whole Sign if every system fails (STEP-A-040).

Where possible we expose debugging metadata (ARMC, obliquity, sidereal time
values) to aid parity checks and diagnose edge cases.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from astroengine.engine.ephe_runtime import init_ephe
from astroengine.ephemeris.swe import has_swe, swe

LOG = logging.getLogger(__name__)

_HAS_SWE = has_swe()
if not _HAS_SWE:
    _SWISSEPH_IMPORT_ERROR = RuntimeError("pyswisseph is not available")
else:
    _SWISSEPH_IMPORT_ERROR = None

from .composite import BirthEvent, DavisonResult, circular_midpoint, geodesic_midpoint

TAU = 360.0

# Swiss house system codes we expose via the API (single ring wheel spec)
_SYSTEM_CODES: Mapping[str, bytes] = {
    "P": b"P",  # Placidus
    "K": b"K",  # Koch
    "O": b"O",  # Porphyry
    "R": b"R",  # Regiomontanus
    "W": b"W",  # Whole Sign
}

# Friendly labels for metadata/debug payloads
_SYSTEM_LABELS: Mapping[str, str] = {
    "P": "placidus",
    "K": "koch",
    "O": "porphyry",
    "R": "regiomontanus",
    "W": "whole_sign",
}

# STEP-A-040 fallback order
FALLBACK_ORDER: tuple[str, ...] = ("P", "K", "O", "R", "W")


class HouseError(RuntimeError):
    """Raised when Swiss Ephemeris cannot compute houses for the inputs."""


def _require_swe() -> None:
    if not _HAS_SWE:  # pragma: no cover - guarded by optional dependency tests
        raise HouseError("Swiss Ephemeris (pyswisseph) is not available") from _SWISSEPH_IMPORT_ERROR


def _normalize_system(requested: str | None) -> str:
    code = (requested or "P").strip().upper()
    if code in _SYSTEM_CODES:
        return code
    name = code.replace(" ", "_")
    for short, label in _SYSTEM_LABELS.items():
        if name == label.upper() or name == label.replace("_", "").upper():
            return short
    raise ValueError(f"Unsupported house system '{requested}'")


def _fallback_sequence(requested: str) -> Sequence[str]:
    seq = [requested]
    for cand in FALLBACK_ORDER:
        if cand not in seq:
            seq.append(cand)
    return seq


def _julian_day(dt: datetime) -> float:
    _require_swe()
    ts = dt.astimezone(UTC)
    frac = (
        ts.hour
        + ts.minute / 60.0
        + ts.second / 3600.0
        + ts.microsecond / 3_600_000_000.0
    )
    init_ephe()
    return swe().julday(ts.year, ts.month, ts.day, frac)


def _sidereal_time_deg(jd_ut: float) -> float:
    _require_swe()
    return (swe().sidtime(jd_ut) * 15.0) % TAU


def _houses_ex(jd_ut: float, lat: float, lon: float, system: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    _require_swe()
    code = _SYSTEM_CODES[system]
    cusps, ascmc = swe().houses_ex(jd_ut, lat, lon, code)
    return cusps, ascmc


def _houses_armc(armc: float, lat: float, eps: float, system: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    _require_swe()
    code = _SYSTEM_CODES[system]
    cusps, ascmc = swe().houses_armc(armc, lat, eps, code)
    return cusps, ascmc


def _wrap360(value: float) -> float:
    res = math.fmod(value, TAU)
    if res < 0.0:
        res += TAU
    return 0.0 if math.isclose(res, TAU, abs_tol=1e-12, rel_tol=0.0) else res


def _circular_delta(a: float, b: float) -> float:
    diff = (b - a + 540.0) % TAU - 180.0
    return diff


def _solved_houses_armc(
    armc: float,
    lat: float,
    eps: float,
    system: str,
    *,
    target_mc: float | None = None,
    tol: float = 1e-6,
    max_iter: int = 12,
) -> tuple[tuple[float, ...], tuple[float, ...], float]:
    """Return cusps/angles for ``armc`` optionally nudging to hit ``target_mc``."""

    armc_deg = _wrap360(armc)
    for _ in range(max_iter):
        cusps, ascmc = _houses_armc(armc_deg, lat, eps, system)
        mc = _wrap360(ascmc[1])
        if target_mc is None:
            return cusps, ascmc, armc_deg
        diff = _circular_delta(mc, target_mc)
        if abs(diff) <= tol:
            return cusps, ascmc, armc_deg
        armc_deg = _wrap360(armc_deg + diff)
    # Final evaluation before raising for visibility
    cusps, ascmc = _houses_armc(armc_deg, lat, eps, system)
    return cusps, ascmc, armc_deg


def _midpoint_armc(a: BirthEvent, b: BirthEvent) -> tuple[float, float, float, dict[str, float]]:
    jd_a = _julian_day(a.when)
    jd_b = _julian_day(b.when)
    lst_a = _wrap360(_sidereal_time_deg(jd_a) + a.lon)
    lst_b = _wrap360(_sidereal_time_deg(jd_b) + b.lon)
    armc_mid = circular_midpoint(lst_a, lst_b)
    meta = {
        "sidereal_time_a": lst_a,
        "sidereal_time_b": lst_b,
        "jd_ut_a": jd_a,
        "jd_ut_b": jd_b,
    }
    return armc_mid, jd_a, jd_b, meta


def _obliquity_deg(jd_ut: float) -> float:
    _require_swe()
    if hasattr(swe, "obl_ecl"):
        eps, _ = swe().obl_ecl(jd_ut)  # type: ignore[call-arg]
        return float(eps)
    # Fallback for Swiss Ephemeris variants without ``obl_ecl`` helper
    base_flag = init_ephe()
    values, _ = swe().calc_ut(jd_ut, swe().ECL_NUT, base_flag)
    return float(values[0])


def _midpoint_datetime(a: datetime, b: datetime) -> datetime:
    a_utc = a.astimezone(UTC)
    b_utc = b.astimezone(UTC)
    mid_ts = (a_utc.timestamp() + b_utc.timestamp()) / 2.0
    return datetime.fromtimestamp(mid_ts, tz=UTC)


@dataclass(frozen=True)
class HouseResult:
    ascendant: float
    midheaven: float
    cusps: tuple[float, ...]
    system_requested: str
    system_used: str
    fallback_reason: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ascendant": self.ascendant,
            "midheaven": self.midheaven,
            "cusps": list(self.cusps),
            "house_system_requested": self.system_requested,
            "house_system_used": self.system_used,
        }
        if self.fallback_reason:
            payload["fallback_reason"] = self.fallback_reason
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def davison_houses(
    davison: DavisonResult,
    system: str | None = None,
    *,
    fallback_reason: str | None = None,
) -> HouseResult:
    """Return Asc/MC and house cusps for a Davison chart."""

    requested = _normalize_system(system)
    jd_ut = _julian_day(davison.mid_when)
    latitude = davison.mid_lat
    longitude = davison.mid_lon
    last_error: Exception | None = None

    lst = _wrap360(_sidereal_time_deg(jd_ut) + longitude)
    for sys in _fallback_sequence(requested):
        try:
            cusps, ascmc = _houses_ex(jd_ut, latitude, longitude, sys)
        except Exception as exc:  # pragma: no cover - Swiss specific failures
            last_error = exc
            continue
        used = sys
        meta: MutableMapping[str, object] = {
            "jd_ut": jd_ut,
            "latitude": latitude,
            "longitude": longitude,
            "system_label": _SYSTEM_LABELS[used],
            "sidereal_time": lst,
            "method": "davison",
        }
        if sys != requested:
            meta["fallback_chain"] = f"{requested}->{used}"
        reason = fallback_reason
        if sys != requested:
            reason = reason or f"fallback:{requested}->{sys}"
        return HouseResult(
            ascendant=_wrap360(ascmc[0]),
            midheaven=_wrap360(ascmc[1]),
            cusps=tuple(_wrap360(val) for val in cusps[:12]),
            system_requested=requested,
            system_used=used,
            fallback_reason=reason,
            metadata=meta,
        )

    # Force Whole Sign if everything fails
    cusps, ascmc = _houses_ex(jd_ut, latitude, longitude, "W")
    reason = fallback_reason or "forced_whole_sign"
    if last_error is not None:
        reason = f"{reason}:{last_error}"
    return HouseResult(
        ascendant=_wrap360(ascmc[0]),
        midheaven=_wrap360(ascmc[1]),
        cusps=tuple(_wrap360(val) for val in cusps[:12]),
        system_requested=requested,
        system_used="W",
        fallback_reason=reason,
        metadata={
            "jd_ut": jd_ut,
            "latitude": latitude,
            "longitude": longitude,
            "system_label": _SYSTEM_LABELS["W"],
            "sidereal_time": lst,
            "method": "davison",
        },
    )


def composite_houses(
    event_a: BirthEvent,
    event_b: BirthEvent,
    system: str | None = None,
) -> HouseResult:
    """Return Asc/MC and cusps for the midpoint composite chart."""

    requested = _normalize_system(system)
    armc_mid, jd_a, jd_b, meta = _midpoint_armc(event_a, event_b)
    latitude_mid, longitude_mid = geodesic_midpoint(event_a.lat, event_a.lon, event_b.lat, event_b.lon)
    mid_dt = _midpoint_datetime(event_a.when, event_b.when)
    jd_mid = _julian_day(mid_dt)
    eps = _obliquity_deg(jd_mid)

    meta.update(
        {
            "armc_mid": armc_mid,
            "obliquity": eps,
            "jd_ut_mid": jd_mid,
            "midpoint_lat": latitude_mid,
            "midpoint_lon": longitude_mid,
            "sidereal_time_mid": _wrap360(_sidereal_time_deg(jd_mid) + longitude_mid),
            "method": "armc_midpoint",
        }
    )

    last_error: Exception | None = None
    chosen_system: str | None = None
    chosen_data: tuple[tuple[float, ...], tuple[float, ...], float] | None = None
    for sys in _fallback_sequence(requested):
        try:
            chosen_data = _solved_houses_armc(armc_mid, latitude_mid, eps, sys)
            chosen_system = sys
            break
        except Exception as exc:
            last_error = exc
            continue

    if chosen_data is None or chosen_system is None:
        # Attempt angle-midpoint fallback
        angles_meta: dict[str, float] = {}
        asc_targets: list[float] = []
        mc_targets: list[float] = []
        for label, event in (("a", event_a), ("b", event_b)):
            jd = _julian_day(event.when)
            for sys in _fallback_sequence(requested):
                try:
                    _, ascmc = _houses_ex(jd, event.lat, event.lon, sys)
                    asc = _wrap360(ascmc[0])
                    mc = _wrap360(ascmc[1])
                    angles_meta[f"asc_{label}"] = asc
                    angles_meta[f"mc_{label}"] = mc
                    asc_targets.append(asc)
                    mc_targets.append(mc)
                    break
                except Exception:
                    continue
        if asc_targets and mc_targets:
            asc_mid = circular_midpoint(asc_targets[0], asc_targets[1]) if len(asc_targets) >= 2 else asc_targets[0]
            mc_mid = circular_midpoint(mc_targets[0], mc_targets[1]) if len(mc_targets) >= 2 else mc_targets[0]
            try:
                cusps, ascmc, armc_used = _solved_houses_armc(armc_mid, latitude_mid, eps, "W", target_mc=mc_mid)
                meta.update(angles_meta)
                meta.update(
                    {
                        "armc_used": armc_used,
                        "system_label": _SYSTEM_LABELS["W"],
                        "fallback_chain": f"{requested}->W",
                        "fallback_method": "angle_midpoint",
                        "method": "angle_midpoint",
                    }
                )
                return HouseResult(
                    ascendant=asc_mid,
                    midheaven=_wrap360(ascmc[1]),
                    cusps=tuple(_wrap360(val) for val in cusps[:12]),
                    system_requested=requested,
                    system_used="W",
                    fallback_reason=f"forced_whole_sign:{last_error}" if last_error else "forced_whole_sign",
                    metadata=meta,
                )
            except Exception as exc:
                LOG.warning(
                    "Angle midpoint house computation failed for %s: %s", requested, exc
                )

        reason = f"forced_whole_sign:{last_error}" if last_error else "forced_whole_sign"
        meta.update({"fallback_method": "default_whole_sign", "method": "forced_whole_sign", "fallback_chain": f"{requested}->W"})
        base_asc = asc_targets[0] if asc_targets else 0.0
        cusps_default = tuple(_wrap360(base_asc + 30.0 * i) for i in range(12))
        return HouseResult(
            ascendant=_wrap360(base_asc),
            midheaven=_wrap360(mc_targets[0]) if mc_targets else _wrap360(meta["sidereal_time_mid"]),
            cusps=cusps_default,
            system_requested=requested,
            system_used="W",
            fallback_reason=reason,
            metadata=meta,
        )

    cusps, ascmc, armc_used = chosen_data
    if chosen_system != requested:
        meta["fallback_chain"] = requested
    meta["armc_used"] = armc_used
    meta["system_label"] = _SYSTEM_LABELS[chosen_system]

    return HouseResult(
        ascendant=_wrap360(ascmc[0]),
        midheaven=_wrap360(ascmc[1]),
        cusps=tuple(_wrap360(val) for val in cusps[:12]),
        system_requested=requested,
        system_used=chosen_system,
        fallback_reason=(None if chosen_system == requested else f"fallback:{requested}->{chosen_system}"),
        metadata=meta,
    )


__all__ = [
    "HouseError",
    "HouseResult",
    "FALLBACK_ORDER",
    "composite_houses",
    "davison_houses",
]
