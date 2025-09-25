"""Example plugin that contributes fixed-star detections."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from ...exporters import LegacyTransitEvent
from ...utils.angles import classify_applying_separating, delta_angle
from .. import (
    DetectorContext,
    DetectorRegistry,
    ExportContext,
    ScoreExtensionRegistry,
    UIPanelSpec,
    hookimpl,
)

ASTROENGINE_PLUGIN_API = "1.0"
LOGGER = logging.getLogger(__name__)

_STAR_LONGITUDES = {
    "regulus": 150.0,
    "aldebaran": 69.0,
    "antares": 250.0,
}
_ORB_ALLOW = 1.0


def _angular_separation(a: float, b: float) -> float:
    return abs(delta_angle(a, b))


def _detect_fixed_star_hits(context: DetectorContext) -> Iterable[LegacyTransitEvent]:
    events: list[LegacyTransitEvent] = []
    for iso in context.ticks:
        positions = context.provider.positions_ecliptic(iso, [context.moving])
        entry = positions.get(context.moving)
        if not entry:
            continue
        lon = float(entry.get("lon", 0.0))
        speed = float(entry.get("speed_lon", 0.0))
        for star_name, star_lon in _STAR_LONGITUDES.items():
            separation = _angular_separation(lon, star_lon)
            if separation <= _ORB_ALLOW:
                phase = classify_applying_separating(lon, speed, star_lon)
                events.append(
                    LegacyTransitEvent(
                        kind="fixed_star_hit",
                        timestamp=iso,
                        moving=context.moving,
                        target=f"fixed_star:{star_name}",
                        orb_abs=separation,
                        orb_allow=_ORB_ALLOW,
                        applying_or_separating=phase,
                        score=0.0,
                        lon_moving=lon,
                        lon_target=star_lon,
                        metadata={
                            "fixed_star": star_name,
                            "source": "fixed_star_hits",
                        },
                    )
                )
    return events


@hookimpl
def register_detectors(registry: DetectorRegistry) -> None:
    registry.register(
        "fixed_star_hits",
        _detect_fixed_star_hits,
        metadata={"stars": sorted(_STAR_LONGITUDES)},
    )


@hookimpl
def extend_scoring(registry: ScoreExtensionRegistry) -> None:
    def _bonus(inputs, _result):
        moving = inputs.moving.lower()
        bonus = 0.0
        if moving in {"sun", "moon"}:
            bonus = 0.1
        return {"bonus": bonus}

    registry.register("fixed_star_bonus", _bonus, namespace="fixed_star")


@hookimpl
def post_export(context: ExportContext) -> None:
    if context.destinations:
        LOGGER.info(
            "fixed_star_hits observed export: destinations=%s",
            list(context.destinations),
        )


@hookimpl
def ui_panels() -> Iterable[UIPanelSpec]:
    yield UIPanelSpec(
        identifier="fixed-star-hits",
        label="Fixed Stars",
        component="FixedStarHitsPanel",
        props={"stars": sorted(_STAR_LONGITUDES)},
    )
