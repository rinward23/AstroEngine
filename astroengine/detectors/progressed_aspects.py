"""Secondary progression aspect detector utilities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from time import perf_counter

from ..chart.config import ChartConfig
from ..chart.natal import DEFAULT_BODIES, ChartLocation, compute_natal_chart
from ..chart.progressions import compute_secondary_progressed_chart
from ..core.angles import normalize_degrees, signed_delta
from ..detectors_aspects import AspectHit
from ..ephemeris import SwissEphemerisAdapter
from ..observability import ASPECT_COMPUTE_DURATION, COMPUTE_ERRORS

__all__ = ["progressed_natal_aspects"]


_PARTILE_THRESHOLD_DEG = 10.0 / 60.0
_DEFAULT_LOCATION = ChartLocation(latitude=0.0, longitude=0.0)


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _isoformat(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _resolve_body_names(selection: Sequence[str] | None) -> list[str]:
    if selection is None:
        return list(DEFAULT_BODIES.keys())

    resolved: list[str] = []
    for token in selection:
        normalized = str(token).strip()
        if not normalized:
            continue
        match = next(
            (name for name in DEFAULT_BODIES if name.lower() == normalized.lower()),
            None,
        )
        if match and match not in resolved:
            resolved.append(match)

    if not resolved:
        raise ValueError("No recognised bodies provided for progressed aspects")

    return resolved


def _smallest_separation(lon_a: float, lon_b: float) -> float:
    delta = abs(normalize_degrees(lon_a) - normalize_degrees(lon_b)) % 360.0
    return delta if delta <= 180.0 else 360.0 - delta


def _update_motion_state(
    history: dict[tuple[str, str, float], float],
    moving: str,
    target: str,
    angle: float,
    orb_abs: float,
    offset_signed: float,
) -> str:
    key = (moving, target, angle)
    previous = history.get(key)
    if previous is None:
        if abs(offset_signed) <= 1e-6:
            state = "exact"
        else:
            state = "applying" if offset_signed < 0 else "separating"
    else:
        if orb_abs < previous - 1e-6:
            state = "applying"
        elif orb_abs > previous + 1e-6:
            state = "separating"
        else:
            state = "exact"
    history[key] = orb_abs
    return state


def _update_speed(
    lon_cache: dict[str, float],
    time_cache: dict[str, datetime],
    name: str,
    longitude: float,
    moment: datetime,
    fallback_speed: float,
) -> float:
    previous_lon = lon_cache.get(name)
    previous_moment = time_cache.get(name)
    lon_cache[name] = longitude
    time_cache[name] = moment

    if previous_lon is None or previous_moment is None:
        return float(fallback_speed)

    delta_days = (moment - previous_moment).total_seconds() / 86400.0
    if delta_days <= 0:
        return float(fallback_speed)

    delta_lon = signed_delta(longitude - previous_lon)
    return float(delta_lon / delta_days)


def progressed_natal_aspects(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    aspects: Sequence[int],
    orb_deg: float,
    bodies: Sequence[str] | None = None,
    step_days: float = 1.0,
) -> list[AspectHit]:
    """Return progressed→natal aspect hits within ``[start_ts, end_ts]``."""

    method_label = "progressed_natal_aspects"
    start_time = perf_counter()
    try:
        start = _parse_iso(start_ts)
        end = _parse_iso(end_ts)
        if end <= start:
            return []

        if step_days <= 0:
            raise ValueError("step_days must be positive for progressed aspect scans")

        target_names = _resolve_body_names(bodies)
        body_codes = {name: DEFAULT_BODIES[name] for name in target_names}

        chart_config = ChartConfig()
        adapter = SwissEphemerisAdapter.from_chart_config(chart_config)
        natal_moment = _parse_iso(natal_ts)

        natal_chart = compute_natal_chart(
            natal_moment,
            _DEFAULT_LOCATION,
            bodies=body_codes,
            config=chart_config,
            adapter=adapter,
        )

        natal_longitudes = {
            name: normalize_degrees(position.longitude)
            for name, position in natal_chart.positions.items()
        }

        aspect_angles = sorted(float(angle) for angle in aspects)
        motion_history: dict[tuple[str, str, float], float] = {}
        lon_cache: dict[str, float] = {}
        time_cache: dict[str, datetime] = {}

        hits: list[AspectHit] = []
        step = timedelta(days=step_days)
        current = start
        while current <= end:
            progressed = compute_secondary_progressed_chart(
                natal_chart,
                current,
                bodies=body_codes,
                config=chart_config,
                adapter=adapter,
            )
            iso_when = _isoformat(current)
            for moving, position in progressed.chart.positions.items():
                lon_moving = normalize_degrees(position.longitude)
                speed = _update_speed(
                    lon_cache,
                    time_cache,
                    moving,
                    lon_moving,
                    current,
                    getattr(position, "speed_longitude", 0.0),
                )
                retrograde = speed < 0
                for target, natal_lon in natal_longitudes.items():
                    if moving == target:
                        continue
                    separation = _smallest_separation(lon_moving, natal_lon)
                    delta_lambda = normalize_degrees(lon_moving - natal_lon)
                    for angle in aspect_angles:
                        offset = separation - angle
                        orb_abs = abs(offset)
                        if orb_abs <= orb_deg + 1e-9:
                            phase = _update_motion_state(
                                motion_history,
                                moving,
                                target,
                                angle,
                                orb_abs,
                                offset,
                            )
                            hits.append(
                                AspectHit(
                                    kind="progressed_natal_aspect",
                                    when_iso=iso_when,
                                    moving=moving,
                                    target=target,
                                    angle_deg=float(angle),
                                    lon_moving=float(lon_moving),
                                    lon_target=float(natal_lon),
                                    delta_lambda_deg=float(delta_lambda),
                                    offset_deg=float(offset),
                                    orb_abs=float(orb_abs),
                                    orb_allow=float(orb_deg),
                                    is_partile=orb_abs <= _PARTILE_THRESHOLD_DEG,
                                    applying_or_separating=phase,
                                    family="progressed-natal",
                                    corridor_width_deg=None,
                                    corridor_profile=None,
                                    speed_deg_per_day=float(speed),
                                    retrograde=retrograde,
                                )
                            )
            current += step

        hits.sort(key=lambda hit: (hit.when_iso, hit.moving, hit.target, hit.angle_deg))
        return hits
    except Exception as exc:
        COMPUTE_ERRORS.labels(
            component=f"aspect:{method_label}",
            error=exc.__class__.__name__,
        ).inc()
        raise
    finally:
        duration = perf_counter() - start_time
        ASPECT_COMPUTE_DURATION.labels(method=method_label).observe(duration)
