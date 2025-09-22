"""Sign ingress detectors backed by Swiss Ephemeris longitudes."""

from __future__ import annotations

from typing import Iterable, Sequence

try:  # pragma: no cover - exercised through swiss-marked tests
    import swisseph as swe  # type: ignore
except Exception:  # pragma: no cover
    swe = None  # type: ignore

from ..events import IngressEvent
from .common import delta_deg, jd_to_iso, solve_zero_crossing

__all__ = ["find_sign_ingresses"]


_SIGN_NAMES: Sequence[str] = (
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

_BODY_CODES = {
    "sun": lambda: swe.SUN,
    "moon": lambda: swe.MOON,
    "mercury": lambda: swe.MERCURY,
    "venus": lambda: swe.VENUS,
    "mars": lambda: swe.MARS,
    "jupiter": lambda: swe.JUPITER,
    "saturn": lambda: swe.SATURN,
    "uranus": lambda: swe.URANUS,
    "neptune": lambda: swe.NEPTUNE,
    "pluto": lambda: swe.PLUTO,
    "ceres": lambda: swe.CERES,
    "pallas": lambda: swe.PALLAS,
    "juno": lambda: swe.JUNO,
    "vesta": lambda: swe.VESTA,
    "chiron": lambda: swe.CHIRON,
}


def _body_code(name: str) -> int | None:
    resolver = _BODY_CODES.get(name.lower())
    if resolver is None or swe is None:
        return None
    return int(resolver())


def _longitude_and_speed(jd_ut: float, code: int) -> tuple[float, float]:
    assert swe is not None
    values, _ = swe.calc_ut(jd_ut, code, swe.FLG_SWIEPH | swe.FLG_SPEED)
    longitude = float(values[0]) % 360.0
    speed = float(values[3])
    return longitude, speed


def _sign_index(longitude: float) -> int:
    return int((longitude % 360.0) // 30.0)


def _sign_name(index: int) -> str:
    return _SIGN_NAMES[index % len(_SIGN_NAMES)]


def find_sign_ingresses(
    start_jd: float,
    end_jd: float,
    bodies: Iterable[str] | None = None,
    *,
    step_hours: float = 6.0,
) -> list[IngressEvent]:
    """Return zodiacal ingress events for ``bodies`` within ``start_jd`` → ``end_jd``."""

    if end_jd <= start_jd:
        return []
    if swe is None:
        raise RuntimeError("Swiss ephemeris not available; install astroengine[ephem]")

    step_days = step_hours / 24.0
    body_names = list(bodies) if bodies is not None else list(_BODY_CODES)

    events: list[IngressEvent] = []
    seen: set[tuple[str, int]] = set()

    for name in body_names:
        code = _body_code(name)
        if code is None:
            continue

        prev_jd = start_jd
        prev_lon, prev_speed = _longitude_and_speed(prev_jd, code)
        prev_sign = _sign_index(prev_lon)

        jd = start_jd + step_days
        while jd <= end_jd + step_days:
            lon, speed = _longitude_and_speed(jd, code)
            sign = _sign_index(lon)

            if sign != prev_sign:
                target = (sign * 30.0) % 360.0

                try:
                    root = solve_zero_crossing(
                        lambda candidate, c=code, tgt=target: delta_deg(
                            _longitude_and_speed(candidate, c)[0], tgt
                        ),
                        prev_jd,
                        min(jd, end_jd),
                        tol=1e-5,
                        tol_deg=1e-4,
                    )
                except ValueError:
                    root = jd

                if not (start_jd <= root <= end_jd):
                    prev_jd, prev_lon, prev_speed, prev_sign = jd, lon, speed, sign
                    jd += step_days
                    continue

                key = (name, int(round(root * 86400)))
                if key in seen:
                    prev_jd, prev_lon, prev_speed, prev_sign = jd, lon, speed, sign
                    jd += step_days
                    continue

                final_lon, final_speed = _longitude_and_speed(root, code)
                events.append(
                    IngressEvent(
                        ts=jd_to_iso(root),
                        jd=root,
                        body=name.capitalize(),
                        sign_from=_sign_name(prev_sign),
                        sign_to=_sign_name(sign),
                        longitude=final_lon,
                        speed_longitude=final_speed,
                        retrograde=final_speed < 0.0,
                    )
                )
                seen.add(key)

            prev_jd, prev_lon, prev_speed, prev_sign = jd, lon, speed, sign
            jd += step_days

    events.sort(key=lambda event: event.jd)
    return events
