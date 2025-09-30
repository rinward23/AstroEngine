"""Sidereal lunar calendar helpers (masa and paksha)."""

from __future__ import annotations

from astroengine.chart import NatalChart

from ..lunar import MasaInfo, PakshaInfo, masa_for_longitude, paksha_from_longitudes

__all__ = [
    "masa_for_chart",
    "paksha_for_chart",
]


def _require_body(chart: NatalChart, body: str) -> float:
    position = chart.positions.get(body)
    if position is None:
        raise ValueError(f"{body} position unavailable in chart")
    return position.longitude


def masa_for_chart(chart: NatalChart) -> MasaInfo:
    """Return the sidereal lunar month for ``chart``."""

    sun_lon = _require_body(chart, "Sun")
    return masa_for_longitude(sun_lon, zodiac="sidereal")


def paksha_for_chart(chart: NatalChart) -> PakshaInfo:
    """Return the sidereal paksha state for ``chart``."""

    moon_lon = _require_body(chart, "Moon")
    sun_lon = _require_body(chart, "Sun")
    return paksha_from_longitudes(moon_lon, sun_lon)
