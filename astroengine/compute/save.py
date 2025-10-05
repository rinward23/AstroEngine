"""Helpers for computing and serialising chart payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from astroengine.chart.config import ChartConfig
from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.config.settings import Settings


def _chart_config_from_settings(settings: Settings) -> ChartConfig:
    zodiac = settings.zodiac.type
    ayanamsha = settings.zodiac.ayanamsa if zodiac == "sidereal" else None
    house_system = settings.houses.system
    return ChartConfig(
        zodiac=zodiac,
        ayanamsha=ayanamsha,
        house_system=house_system,
    )


def _serialize_bodies(chart) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name, position in chart.positions.items():
        payload[name] = {
            "longitude": float(position.longitude),
            "latitude": float(position.latitude),
            "distance_au": float(position.distance_au),
            "speed_longitude": float(position.speed_longitude),
            "speed_latitude": float(position.speed_latitude),
            "retrograde": bool(position.speed_longitude < 0.0),
            "declination": float(position.declination),
        }
    return payload


def _serialize_houses(chart) -> dict[str, Any]:
    houses_dict = chart.houses.to_dict()
    cusps = houses_dict.get("cusps")
    if isinstance(cusps, tuple):
        houses_dict["cusps"] = list(cusps)
    return houses_dict


def _serialize_aspects(chart) -> list[dict[str, Any]]:
    aspects: list[dict[str, Any]] = []
    for aspect in chart.aspects:
        aspects.append(
            {
                "body_a": aspect.body_a,
                "body_b": aspect.body_b,
                "angle": int(aspect.angle),
                "orb": float(aspect.orb),
                "separation": float(aspect.separation),
            }
        )
    return aspects


def build_payload(
    dt_utc: datetime,
    lat: float,
    lon: float,
    settings: Settings,
) -> Dict[str, Any]:
    """Return serialisable chart payloads ready for persistence."""

    chart_config = _chart_config_from_settings(settings)
    chart = compute_natal_chart(
        dt_utc,
        ChartLocation(latitude=float(lat), longitude=float(lon)),
        config=chart_config,
    )

    bodies = _serialize_bodies(chart)
    houses = _serialize_houses(chart)
    aspects = _serialize_aspects(chart)
    patterns: list[dict[str, Any]] = []

    metadata = {}
    if chart.metadata:
        metadata = dict(chart.metadata)

    return {
        "bodies": bodies,
        "houses": houses,
        "aspects": aspects,
        "patterns": patterns,
        "metadata": metadata,
    }
