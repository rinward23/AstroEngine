"""Example plugin that contributes fixed-star detections."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from functools import cache

from ...analysis.fixed_stars import load_catalog
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

_ORB_ALLOW = 1.0
_MAGNITUDE_LIMIT = 4.5


def _star_slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


@cache
def _catalog_longitudes() -> list[tuple[str, float, float]]:
    stars = []
    for star in load_catalog():
        if star.mag <= _MAGNITUDE_LIMIT:
            stars.append((star.name, star.lon_deg, star.mag))
    return stars


def _angular_separation(a: float, b: float) -> float:
    return abs(delta_angle(a, b))


def _detect_fixed_star_hits(context: DetectorContext) -> Iterable[LegacyTransitEvent]:
    events: list[LegacyTransitEvent] = []
    tracked_stars = _catalog_longitudes()
    if not tracked_stars:
        return events
    for iso in context.ticks:
        positions = context.provider.positions_ecliptic(iso, [context.moving])
        entry = positions.get(context.moving)
        if not entry:
            continue
        lon = float(entry.get("lon", 0.0))
        speed = float(entry.get("speed_lon", 0.0))
        for star_name, star_lon, star_mag in tracked_stars:
            separation = _angular_separation(lon, star_lon)
            if separation <= _ORB_ALLOW:
                phase = classify_applying_separating(lon, speed, star_lon)
                slug = _star_slug(star_name)
                events.append(
                    LegacyTransitEvent(
                        kind="fixed_star_hit",
                        timestamp=iso,
                        moving=context.moving,
                        target=f"fixed_star:{slug}",
                        orb_abs=separation,
                        orb_allow=_ORB_ALLOW,
                        applying_or_separating=phase,
                        score=0.0,
                        lon_moving=lon,
                        lon_target=star_lon,
                        metadata={
                            "fixed_star": slug,
                            "fixed_star_name": star_name,
                            "magnitude": star_mag,
                            "source": "fixed_star_hits",
                        },
                    )
                )
    return events


@hookimpl
def register_detectors(registry: DetectorRegistry) -> None:
    tracked = _catalog_longitudes()
    registry.register(
        "fixed_star_hits",
        _detect_fixed_star_hits,
        metadata={
            "catalog": "robson",
            "magnitude_limit": _MAGNITUDE_LIMIT,
            "stars": [name for name, _, _ in tracked],
        },
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
    tracked = _catalog_longitudes()
    yield UIPanelSpec(
        identifier="fixed-star-hits",
        label="Fixed Stars",
        component="FixedStarHitsPanel",
        props={"stars": [name for name, _, _ in tracked]},
    )
