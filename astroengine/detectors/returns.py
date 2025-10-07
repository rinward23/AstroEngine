"""Solar and lunar return detection using Swiss longitudes."""

from __future__ import annotations

from datetime import UTC, datetime

from ..ephemeris import SwissEphemerisAdapter
from ..ephemeris.swisseph_adapter import get_swisseph
from ..events import ReturnEvent
from .common import delta_deg, jd_to_iso, solve_zero_crossing

__all__ = ["solar_lunar_returns", "scan_returns"]


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _body_accessor(kind: str, swe_module) -> tuple[str, int]:
    key = kind.lower()
    if key == "solar":
        return "Sun", swe_module.SUN
    if key == "lunar":
        return "Moon", swe_module.MOON
    raise ValueError(f"Unsupported return kind '{kind}'")


def solar_lunar_returns(
    natal_jd: float,
    start_jd: float,
    end_jd: float,
    kind: str = "solar",
    *,
    step_days: float | None = None,
    adapter: SwissEphemerisAdapter | None = None,
) -> list[ReturnEvent]:
    """Return solar or lunar return events within a Julian day window."""

    if end_jd <= start_jd:
        return []

    adapter = adapter or SwissEphemerisAdapter.get_default_adapter()
    swe = get_swisseph()
    body_name, body_code = _body_accessor(kind, swe)

    def lon_at(jd: float) -> float:
        return (
            adapter.body_position(jd, body_code, body_name=body_name).longitude % 360.0
        )

    target_lon = lon_at(natal_jd) % 360.0
    step = step_days if step_days is not None else (1.0 if body_name == "Sun" else 0.5)

    events: list[ReturnEvent] = []
    seen: set[int] = set()

    prev_jd = start_jd
    prev_delta = delta_deg(lon_at(prev_jd), target_lon)
    current = start_jd + step
    while current <= end_jd + step:
        curr_delta = delta_deg(lon_at(current), target_lon)
        if prev_delta == 0.0:
            root = prev_jd
        elif prev_delta * curr_delta <= 0.0:
            try:
                root = solve_zero_crossing(
                    lambda x, tgt=target_lon: delta_deg(lon_at(x), tgt),
                    prev_jd,
                    min(current, end_jd),
                    tol=1e-5,
                    tol_deg=1e-4,
                )
            except ValueError:
                prev_jd, prev_delta = current, curr_delta
                current += step
                continue
        else:
            prev_jd, prev_delta = current, curr_delta
            current += step
            continue

        key = int(round(root * 86400))
        if key not in seen and start_jd <= root <= end_jd:
            longitude = lon_at(root) % 360.0
            events.append(
                ReturnEvent(
                    ts=jd_to_iso(root),
                    jd=root,
                    body=body_name,
                    method=kind.lower(),
                    longitude=longitude,
                )
            )
            seen.add(key)

        prev_jd, prev_delta = current, curr_delta
        current += step

    events.sort(key=lambda event: event.jd)
    return events


def scan_returns(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    kind: str,
    step_days: float | None = None,
) -> list[ReturnEvent]:
    """Wrapper translating ISO timestamps to Julian day inputs."""

    adapter = SwissEphemerisAdapter.get_default_adapter()
    start_dt = _parse_iso(start_ts)
    end_dt = _parse_iso(end_ts)
    if end_dt <= start_dt:
        return []

    natal_dt = _parse_iso(natal_ts)
    natal_jd = adapter.julian_day(natal_dt)
    start_jd = adapter.julian_day(start_dt)
    end_jd = adapter.julian_day(end_dt)

    return solar_lunar_returns(
        natal_jd,
        start_jd,
        end_jd,
        kind=kind,
        step_days=step_days,
        adapter=adapter,
    )
