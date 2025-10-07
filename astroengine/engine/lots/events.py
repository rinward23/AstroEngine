"""Event scanning for Arabic Lots aspects."""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...scoring.policy import OrbPolicy
from .aspects import _angles_from_harmonics, _resolve_orb, _severity

__all__ = ["LotEvent", "scan_lot_events"]


@dataclass(frozen=True)
class LotEvent:
    lot: str
    body: str
    kind: str
    timestamp: _dt.datetime
    angle: float
    orb: float
    severity: float
    applying: bool | None
    metadata: Mapping[str, object]


def _get_longitude(ephem: object, body: str, moment: _dt.datetime) -> tuple[float, float | None]:
    if hasattr(ephem, "longitude"):
        lon = ephem.longitude(body, moment)
        return float(lon) % 360.0, None
    if hasattr(ephem, "sample"):
        sample = ephem.sample(body, moment)
        longitude = sample.longitude
        speed = getattr(sample, "speed_longitude", None)
        return float(longitude) % 360.0, float(speed) if speed is not None else None
    raise TypeError("Ephemeris adapter must expose 'longitude' or 'sample'")


def _angular_separation(body: float, lot: float) -> float:
    return (body - lot + 180.0) % 360.0 - 180.0


def _bisect(
    ephem: object,
    body: str,
    lot: float,
    target: float,
    start: _dt.datetime,
    end: _dt.datetime,
    *,
    iterations: int = 12,
) -> _dt.datetime:
    low = start
    high = end
    for _ in range(iterations):
        mid = low + (high - low) / 2
        body_low, _ = _get_longitude(ephem, body, low)
        body_mid, _ = _get_longitude(ephem, body, mid)
        diff_low = _angular_separation(body_low, lot) - target
        diff_mid = _angular_separation(body_mid, lot) - target
        if diff_low == 0.0:
            return low
        if diff_mid == 0.0:
            return mid
        if diff_low * diff_mid <= 0:
            high = mid
        else:
            low = mid
    return low + (high - low) / 2


def _event_metadata(angle: float, harmonic: int) -> dict[str, object]:
    return {"aspect_angle": angle, "harmonic": harmonic}


def scan_lot_events(
    ephem: object,
    lot_lambda: float,
    bodies: Iterable[str],
    t0: _dt.datetime,
    t1: _dt.datetime,
    policy: OrbPolicy,
    harmonics: Iterable[int],
    *,
    kind: str = "transit",
    step_hours: float = 12.0,
    lot_name: str = "Lot",
) -> list[LotEvent]:
    """Scan ``bodies`` for aspect hits to a single lot between ``t0`` and ``t1``."""

    if t1 <= t0:
        return []
    angles = _angles_from_harmonics(harmonics)
    step = _dt.timedelta(hours=max(0.1, float(step_hours)))
    lot_lambda = lot_lambda % 360.0

    events: list[LotEvent] = []
    for body in bodies:
        for angle in angles:
            current = t0
            body_val, body_speed = _get_longitude(ephem, body, current)
            allowance = _resolve_orb(policy, body, angle)
            target = angle if abs(_angular_separation(body_val, lot_lambda) - angle) <= abs(_angular_separation(body_val, lot_lambda) + angle) else -angle
            diff_prev = _angular_separation(body_val, lot_lambda) - target
            while current < t1:
                next_time = min(current + step, t1)
                body_next, _ = _get_longitude(ephem, body, next_time)
                diff_next = _angular_separation(body_next, lot_lambda) - target
                if diff_prev == 0.0:
                    root = current
                elif diff_prev * diff_next <= 0.0:
                    root = _bisect(ephem, body, lot_lambda, target, current, next_time)
                else:
                    root = None
                if root is not None:
                    body_root, body_speed = _get_longitude(ephem, body, root)
                    separation = abs(_angular_separation(body_root, lot_lambda))
                    orb = abs(separation - angle)
                    if orb <= allowance:
                        severity = _severity(orb, allowance)
                        applying: bool | None = None
                        if body_speed is not None:
                            delta = _angular_separation(body_root, lot_lambda)
                            target = angle if abs(delta - angle) <= abs(delta + angle) else -angle
                            diff = delta - target
                            if diff > 0:
                                applying = body_speed < 0
                            elif diff < 0:
                                applying = body_speed > 0
                        events.append(
                            LotEvent(
                                lot=lot_name,
                                body=body,
                                kind=kind,
                                timestamp=root,
                                angle=angle,
                                orb=orb,
                                severity=severity,
                                applying=applying,
                                metadata=_event_metadata(angle, int(round(360 / angle)) if angle else 0),
                            )
                        )
                diff_prev = diff_next
                current = next_time
                body_val = body_next
    events.sort(key=lambda event: event.timestamp)
    return events
