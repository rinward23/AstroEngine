"""Sign ingress detection for solar system bodies."""

from __future__ import annotations

from collections.abc import Sequence

from ..events import IngressEvent
from .common import body_lon, delta_deg, jd_to_iso, norm360, solve_zero_crossing

__all__ = ["find_ingresses"]

_SIGN_NAMES = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

_SIGN_DEGREES = tuple(index * 30.0 for index in range(12))
_STEP_TOL = 1e-6


def _sign_index(longitude: float) -> int:
    """Return the zodiac sign index (0-11) for ``longitude``."""

    return int(norm360(longitude) // 30.0) % 12


def _boundary_for(prev_index: int) -> float:
    """Return the degree boundary crossed leaving ``prev_index``."""

    return _SIGN_DEGREES[(prev_index + 1) % 12] if prev_index < 11 else 360.0


def _to_ingress_event(body_label: str, body_key: str, jd_ut: float, sign_index: int) -> IngressEvent:
    longitude = norm360(body_lon(jd_ut, body_key))
    sign_name = _SIGN_NAMES[sign_index]
    return IngressEvent(
        ts=jd_to_iso(jd_ut),
        jd=jd_ut,
        body=body_label,
        sign=sign_name,
        longitude=longitude,
        sign_index=sign_index,
    )


def find_ingresses(
    start_jd: float,
    end_jd: float,
    bodies: Sequence[str],
    *,
    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Return ingress events for ``bodies`` between ``start_jd`` and ``end_jd``."""

    if end_jd <= start_jd:
        return []

    step_days = step_hours / 24.0
    events: list[IngressEvent] = []

    for body_label in bodies:
        body = body_label.lower()
        prev_jd = start_jd
        prev_lon = norm360(body_lon(prev_jd, body))
        prev_sign = _sign_index(prev_lon)

        jd = start_jd + step_days
        while jd <= end_jd + step_days:
            curr_lon = norm360(body_lon(jd, body))
            curr_sign = _sign_index(curr_lon)

            if curr_sign != prev_sign:
                boundary = _boundary_for(prev_sign)
                target_sign = _sign_index(boundary)
                try:
                    root = solve_zero_crossing(
                        lambda value, body=body, boundary=boundary: delta_deg(
                            norm360(body_lon(value, body)), boundary
                        ),
                        prev_jd,
                        min(jd, end_jd),
                        tol=_STEP_TOL,
                        tol_deg=1e-4,
                    )
                except ValueError:
                    root = None

                if root is not None and start_jd - _STEP_TOL <= root <= end_jd + _STEP_TOL:
                    events.append(_to_ingress_event(body_label, body, root, target_sign))

            prev_jd = jd
            prev_lon = curr_lon
            prev_sign = curr_sign
            jd += step_days

    events.sort(key=lambda item: (item.jd, item.body))
    # Deduplicate in case of floating point jitter
    deduped: list[IngressEvent] = []
    seen: set[tuple[str, int, int]] = set()
    for event in events:
        key = (event.body.lower(), int(round(event.jd * 86400)), event.sign_index)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped
