"""Composite and midpoint chart helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..ephemeris import BodyPosition, HousePositions, SwissEphemerisAdapter
from ..utils.angles import delta_angle, norm360
from .config import ChartConfig
from .natal import DEFAULT_BODIES, ChartLocation, NatalChart, compute_natal_chart

__all__ = [
    "CompositeBodyPosition",
    "CompositeChart",
    "MidpointEntry",
    "compute_composite_chart",
    "compute_midpoint_tree",
]


@dataclass(frozen=True)
class MidpointEntry:
    """Midpoint between two chart factors treated as a body."""

    name: str
    bodies: tuple[str, str]
    position: BodyPosition
    separation: float


@dataclass(frozen=True)
class CompositeBodyPosition:
    """Body position enriched with midpoint compatibility metadata."""

    body: str
    julian_day: float
    longitude: float
    latitude: float
    distance_au: float
    speed_longitude: float
    speed_latitude: float
    speed_distance: float
    declination: float
    speed_declination: float
    midpoint_longitude: float

    @classmethod
    def from_body_position(cls, pos: BodyPosition) -> CompositeBodyPosition:
        return cls(
            body=pos.body,
            julian_day=pos.julian_day,
            longitude=pos.longitude,
            latitude=pos.latitude,
            distance_au=pos.distance_au,
            speed_longitude=pos.speed_longitude,
            speed_latitude=pos.speed_latitude,
            speed_distance=pos.speed_distance,
            declination=pos.declination,
            speed_declination=pos.speed_declination,
            midpoint_longitude=pos.longitude,
        )

    def to_body_position(self) -> BodyPosition:
        return BodyPosition(
            body=self.body,
            julian_day=self.julian_day,
            longitude=self.longitude,
            latitude=self.latitude,
            distance_au=self.distance_au,
            speed_longitude=self.speed_longitude,
            speed_latitude=self.speed_latitude,
            speed_distance=self.speed_distance,
            declination=self.declination,
            speed_declination=self.speed_declination,
        )

    def to_dict(self) -> dict[str, float]:
        payload = dict(self.to_body_position().to_dict())
        payload["midpoint_longitude"] = self.midpoint_longitude
        return payload


@dataclass(frozen=True)
class CompositeChart:
    """Composite chart constructed from two natal charts."""

    method: str
    moment: datetime
    location: ChartLocation
    julian_day: float
    positions: Mapping[str, CompositeBodyPosition]
    houses: HousePositions
    midpoints: tuple[MidpointEntry, ...]
    sources: tuple[NatalChart, NatalChart]


def _midpoint_angle(first: float, second: float) -> float:
    """Return the longitude midway between two angles."""

    return norm360(first + delta_angle(first, second) / 2.0)


def _average(value_a: float, value_b: float) -> float:
    return (value_a + value_b) / 2.0


def _average_body_position(
    pos_a: BodyPosition,
    pos_b: BodyPosition,
    *,
    label: str,
    julian_day: float | None = None,
) -> CompositeBodyPosition:
    jd = (
        julian_day
        if julian_day is not None
        else _average(pos_a.julian_day, pos_b.julian_day)
    )
    base = BodyPosition(
        body=label,
        julian_day=jd,
        longitude=_midpoint_angle(pos_a.longitude, pos_b.longitude),
        latitude=_average(pos_a.latitude, pos_b.latitude),
        distance_au=_average(pos_a.distance_au, pos_b.distance_au),
        speed_longitude=_average(pos_a.speed_longitude, pos_b.speed_longitude),
        speed_latitude=_average(pos_a.speed_latitude, pos_b.speed_latitude),
        speed_distance=_average(pos_a.speed_distance, pos_b.speed_distance),
        declination=_average(pos_a.declination, pos_b.declination),
        speed_declination=_average(pos_a.speed_declination, pos_b.speed_declination),
    )
    return CompositeBodyPosition.from_body_position(base)


def _mean_datetime(moment_a: datetime, moment_b: datetime) -> datetime:
    utc_a = moment_a.astimezone(UTC)
    utc_b = moment_b.astimezone(UTC)
    return utc_a + (utc_b - utc_a) / 2


def _mean_location(loc_a: ChartLocation, loc_b: ChartLocation) -> ChartLocation:
    lat = _average(loc_a.latitude, loc_b.latitude)
    lon_a = norm360(loc_a.longitude)
    lon_b = norm360(loc_b.longitude)
    lon = _midpoint_angle(lon_a, lon_b)
    if lon > 180.0:
        lon -= 360.0
    return ChartLocation(latitude=lat, longitude=lon)


def _average_houses(
    houses_a: HousePositions, houses_b: HousePositions
) -> HousePositions:
    if houses_a.system != houses_b.system:
        raise ValueError(
            "House systems must match to compute a midpoint composite chart"
        )
    if len(houses_a.cusps) != len(houses_b.cusps):
        raise ValueError("House cusps must have matching lengths")

    cusps = tuple(
        _midpoint_angle(first, second)
        for first, second in zip(houses_a.cusps, houses_b.cusps, strict=False)
    )
    asc = _midpoint_angle(houses_a.ascendant, houses_b.ascendant)
    mc = _midpoint_angle(houses_a.midheaven, houses_b.midheaven)
    return HousePositions(
        system=houses_a.system, cusps=cusps, ascendant=asc, midheaven=mc
    )


def _midpoint_entries_from_positions(
    positions: Mapping[str, CompositeBodyPosition],
) -> tuple[MidpointEntry, ...]:
    names = list(positions.keys())
    entries: list[MidpointEntry] = []
    for index, name_a in enumerate(names):
        for name_b in names[index + 1 :]:
            pos_a = positions[name_a].to_body_position()
            pos_b = positions[name_b].to_body_position()
            label = f"{name_a}/{name_b}"
            midpoint = _average_body_position(pos_a, pos_b, label=label)
            separation = abs(delta_angle(pos_a.longitude, pos_b.longitude))
            entries.append(
                MidpointEntry(
                    name=label,
                    bodies=(name_a, name_b),
                    position=midpoint.to_body_position(),
                    separation=separation,
                )
            )
    return tuple(entries)


def compute_midpoint_tree(
    chart: NatalChart,
    *,
    include: Sequence[str] | None = None,
) -> tuple[MidpointEntry, ...]:
    """Compute midpoint entries for all body pairs in a natal chart."""

    if include is None:
        body_names: Iterable[str] = chart.positions.keys()
    else:
        include_lower = {name.lower() for name in include}
        body_names = [
            name for name in chart.positions.keys() if name.lower() in include_lower
        ]
    positions = {
        name: CompositeBodyPosition.from_body_position(chart.positions[name])
        for name in body_names
    }
    return _midpoint_entries_from_positions(positions)


def _shared_body_names(
    chart_a: NatalChart,
    chart_b: NatalChart,
    include: Sequence[str] | None,
) -> tuple[str, ...]:
    names_b = set(chart_b.positions)
    if include is None:
        ordered = [name for name in chart_a.positions.keys() if name in names_b]
    else:
        ordered = [
            name for name in include if name in chart_a.positions and name in names_b
        ]
    return tuple(ordered)


def compute_composite_chart(
    chart_a: NatalChart,
    chart_b: NatalChart,
    *,
    method: str = "midpoint",
    include: Sequence[str] | None = None,
    body_codes: Mapping[str, int] | None = None,
    config: ChartConfig | None = None,
    adapter: SwissEphemerisAdapter | None = None,
) -> CompositeChart:
    """Compute a relationship composite chart from two natal charts."""

    method_normalized = method.lower()
    chart_config = config or ChartConfig()
    shared_names = _shared_body_names(chart_a, chart_b, include)
    if not shared_names:
        raise ValueError("No shared bodies available to build a composite chart")

    moment = _mean_datetime(chart_a.moment, chart_b.moment)
    location = _mean_location(chart_a.location, chart_b.location)

    if method_normalized == "midpoint":
        julian_day = _average(chart_a.julian_day, chart_b.julian_day)
        positions = {
            name: _average_body_position(
                chart_a.positions[name],
                chart_b.positions[name],
                label=name,
                julian_day=julian_day,
            )
            for name in shared_names
        }
        houses = _average_houses(chart_a.houses, chart_b.houses)
    elif method_normalized == "davison":

        adapter = adapter or SwissEphemerisAdapter.from_chart_config(chart_config)

        mapping = body_codes or DEFAULT_BODIES
        body_map = {name: mapping[name] for name in shared_names if name in mapping}
        if len(body_map) != len(shared_names):
            missing = sorted(set(shared_names) - set(body_map))
            raise ValueError(
                "Body codes required for Davison composite: missing "
                + ", ".join(missing)
            )
        natal = compute_natal_chart(
            moment,
            location,
            bodies=body_map,
            config=chart_config,
            adapter=adapter,
        )
        julian_day = natal.julian_day
        positions = {
            name: CompositeBodyPosition.from_body_position(natal.positions[name])
            for name in shared_names
        }
        houses = natal.houses
    else:
        raise ValueError("Composite method must be 'midpoint' or 'davison'")

    midpoints = _midpoint_entries_from_positions(positions)
    return CompositeChart(
        method=method_normalized,
        moment=moment,
        location=location,
        julian_day=julian_day,
        positions=positions,
        houses=houses,
        midpoints=midpoints,
        sources=(chart_a, chart_b),
    )
