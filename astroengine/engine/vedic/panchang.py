"""Pañchānga helpers derived from sidereal chart data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ...chart.natal import NatalChart
from ...core.angles import normalize_degrees
from .chart import VedicChartContext
from .nakshatra import (
    NAKSHATRA_ARC_DEGREES,
    NakshatraPosition,
)
from .nakshatra import (
    position_for as nakshatra_position_for,
)

__all__ = [
    "TITHI_ARC_DEGREES",
    "YOGA_ARC_DEGREES",
    "KARANA_ARC_DEGREES",
    "Tithi",
    "NakshatraStatus",
    "Yoga",
    "Karana",
    "Vaar",
    "Panchang",
    "tithi_from_longitudes",
    "nakshatra_from_longitude",
    "yoga_from_longitudes",
    "karana_from_longitudes",
    "vaar_from_datetime",
    "panchang_from_chart",
]


TITHI_ARC_DEGREES: float = 360.0 / 30.0
"""Angular span of a single tithi in degrees."""

YOGA_ARC_DEGREES: float = 360.0 / 27.0
"""Angular span of a single yoga in degrees."""

KARANA_ARC_DEGREES: float = TITHI_ARC_DEGREES / 2.0
"""Angular span of a single karana (half tithi) in degrees."""


@dataclass(frozen=True)
class Tithi:
    """Derived lunar day metadata."""

    index: int
    name: str
    paksha: str
    longitude_delta: float
    progress: float


@dataclass(frozen=True)
class NakshatraStatus:
    """Nakshatra placement along with fractional progress."""

    position: NakshatraPosition
    progress: float


@dataclass(frozen=True)
class Yoga:
    """Sum of luminary longitudes divided into 27 yogas."""

    index: int
    name: str
    longitude_sum: float
    progress: float


@dataclass(frozen=True)
class Karana:
    """Half-tithi segment metadata."""

    index: int
    name: str
    longitude_delta: float
    progress: float


@dataclass(frozen=True)
class Vaar:
    """Weekday name derived from the chart moment."""

    index: int
    weekday: int
    name: str
    english: str


@dataclass(frozen=True)
class Panchang:
    """Complete pañchānga snapshot for a chart or context."""

    tithi: Tithi
    nakshatra: NakshatraStatus
    yoga: Yoga
    karana: Karana
    vaar: Vaar


@dataclass(frozen=True)
class _TithiDefinition:
    name: str
    paksha: str


@dataclass(frozen=True)
class _YogaDefinition:
    name: str


@dataclass(frozen=True)
class _KaranaDefinition:
    name: str


@dataclass(frozen=True)
class _VaarDefinition:
    name: str
    english: str


_TITHI_DEFINITIONS: Sequence[_TithiDefinition] = (
    _TithiDefinition("Shukla Pratipada", "Shukla"),
    _TithiDefinition("Shukla Dvitiiya", "Shukla"),
    _TithiDefinition("Shukla Tritiiya", "Shukla"),
    _TithiDefinition("Shukla Chaturthi", "Shukla"),
    _TithiDefinition("Shukla Panchami", "Shukla"),
    _TithiDefinition("Shukla Shashthi", "Shukla"),
    _TithiDefinition("Shukla Saptami", "Shukla"),
    _TithiDefinition("Shukla Ashtami", "Shukla"),
    _TithiDefinition("Shukla Navami", "Shukla"),
    _TithiDefinition("Shukla Dashami", "Shukla"),
    _TithiDefinition("Shukla Ekadashi", "Shukla"),
    _TithiDefinition("Shukla Dwadashi", "Shukla"),
    _TithiDefinition("Shukla Trayodashi", "Shukla"),
    _TithiDefinition("Shukla Chaturdashi", "Shukla"),
    _TithiDefinition("Purnima", "Shukla"),
    _TithiDefinition("Krishna Pratipada", "Krishna"),
    _TithiDefinition("Krishna Dvitiiya", "Krishna"),
    _TithiDefinition("Krishna Tritiiya", "Krishna"),
    _TithiDefinition("Krishna Chaturthi", "Krishna"),
    _TithiDefinition("Krishna Panchami", "Krishna"),
    _TithiDefinition("Krishna Shashthi", "Krishna"),
    _TithiDefinition("Krishna Saptami", "Krishna"),
    _TithiDefinition("Krishna Ashtami", "Krishna"),
    _TithiDefinition("Krishna Navami", "Krishna"),
    _TithiDefinition("Krishna Dashami", "Krishna"),
    _TithiDefinition("Krishna Ekadashi", "Krishna"),
    _TithiDefinition("Krishna Dwadashi", "Krishna"),
    _TithiDefinition("Krishna Trayodashi", "Krishna"),
    _TithiDefinition("Krishna Chaturdashi", "Krishna"),
    _TithiDefinition("Amavasya", "Krishna"),
)

_YOGA_DEFINITIONS: Sequence[_YogaDefinition] = (
    _YogaDefinition("Vishkambha"),
    _YogaDefinition("Priti"),
    _YogaDefinition("Ayushman"),
    _YogaDefinition("Saubhagya"),
    _YogaDefinition("Shobhana"),
    _YogaDefinition("Atiganda"),
    _YogaDefinition("Sukarma"),
    _YogaDefinition("Dhriti"),
    _YogaDefinition("Shoola"),
    _YogaDefinition("Ganda"),
    _YogaDefinition("Vriddhi"),
    _YogaDefinition("Dhruva"),
    _YogaDefinition("Vyaghata"),
    _YogaDefinition("Harshana"),
    _YogaDefinition("Vajra"),
    _YogaDefinition("Siddhi"),
    _YogaDefinition("Vyatipata"),
    _YogaDefinition("Variyana"),
    _YogaDefinition("Parigha"),
    _YogaDefinition("Shiva"),
    _YogaDefinition("Siddha"),
    _YogaDefinition("Sadhya"),
    _YogaDefinition("Shubha"),
    _YogaDefinition("Shukla"),
    _YogaDefinition("Brahma"),
    _YogaDefinition("Indra"),
    _YogaDefinition("Vaidhriti"),
)

_CHARA_KARANAS: Sequence[str] = (
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Gara",
    "Vanija",
    "Vishti",
)

_STHIRA_KARANAS: Sequence[str] = ("Shakuni", "Chatushpada", "Nagava")

_karana_names: list[str] = ["Kimstughna"]
_karana_names.extend(name for _ in range(8) for name in _CHARA_KARANAS)
_karana_names.extend(_STHIRA_KARANAS)

_KARANA_DEFINITIONS: Sequence[_KaranaDefinition] = tuple(
    _KaranaDefinition(name) for name in _karana_names
)

_VAAR_DEFINITIONS: Sequence[_VaarDefinition] = (
    _VaarDefinition("Ravivara", "Sunday"),
    _VaarDefinition("Somavara", "Monday"),
    _VaarDefinition("Mangalavara", "Tuesday"),
    _VaarDefinition("Budhavara", "Wednesday"),
    _VaarDefinition("Guruvara", "Thursday"),
    _VaarDefinition("Shukravara", "Friday"),
    _VaarDefinition("Shanivara", "Saturday"),
)


def _resolve_chart(chart_or_context: NatalChart | VedicChartContext) -> NatalChart:
    if isinstance(chart_or_context, VedicChartContext):
        return chart_or_context.chart
    if isinstance(chart_or_context, NatalChart):
        return chart_or_context
    raise TypeError("expected NatalChart or VedicChartContext")


def _body_longitude(chart: NatalChart, body: str) -> float:
    positions: Mapping[str, object] = chart.positions
    try:
        position = positions[body]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise KeyError(f"{body!r} position unavailable in chart") from exc
    longitude = getattr(position, "longitude", None)
    if longitude is None:
        raise AttributeError(f"{body!r} position missing longitude")
    return float(longitude)


def _tithi_definition(index_zero_based: int) -> _TithiDefinition:
    return _TITHI_DEFINITIONS[index_zero_based % len(_TITHI_DEFINITIONS)]


def _yoga_definition(index_zero_based: int) -> _YogaDefinition:
    return _YOGA_DEFINITIONS[index_zero_based % len(_YOGA_DEFINITIONS)]


def _karana_definition(index_zero_based: int) -> _KaranaDefinition:
    return _KARANA_DEFINITIONS[index_zero_based % len(_KARANA_DEFINITIONS)]


def _vaar_definition(weekday: int) -> _VaarDefinition:
    return _VAAR_DEFINITIONS[weekday % len(_VAAR_DEFINITIONS)]


def tithi_from_longitudes(moon_longitude: float, sun_longitude: float) -> Tithi:
    """Return the current tithi for the provided sidereal longitudes."""

    delta = normalize_degrees(moon_longitude - sun_longitude)
    index_zero = int(delta // TITHI_ARC_DEGREES)
    definition = _tithi_definition(index_zero)
    progress = (delta % TITHI_ARC_DEGREES) / TITHI_ARC_DEGREES
    return Tithi(
        index=index_zero + 1,
        name=definition.name,
        paksha=definition.paksha,
        longitude_delta=delta,
        progress=progress,
    )


def nakshatra_from_longitude(longitude: float) -> NakshatraStatus:
    """Return nakshatra placement and fractional progress."""

    position = nakshatra_position_for(longitude)
    offset_within = position.degree_in_pada + (position.pada - 1) * (
        NAKSHATRA_ARC_DEGREES / 4.0
    )
    progress = offset_within / NAKSHATRA_ARC_DEGREES
    return NakshatraStatus(position=position, progress=progress)


def yoga_from_longitudes(moon_longitude: float, sun_longitude: float) -> Yoga:
    """Return the current yoga for the provided sidereal longitudes."""

    total = normalize_degrees(moon_longitude + sun_longitude)
    index_zero = int(total // YOGA_ARC_DEGREES)
    definition = _yoga_definition(index_zero)
    progress = (total % YOGA_ARC_DEGREES) / YOGA_ARC_DEGREES
    return Yoga(
        index=index_zero + 1,
        name=definition.name,
        longitude_sum=total,
        progress=progress,
    )


def karana_from_longitudes(moon_longitude: float, sun_longitude: float) -> Karana:
    """Return the current karana for the provided sidereal longitudes."""

    delta = normalize_degrees(moon_longitude - sun_longitude)
    index_zero = int(delta // KARANA_ARC_DEGREES)
    definition = _karana_definition(index_zero)
    progress = (delta % KARANA_ARC_DEGREES) / KARANA_ARC_DEGREES
    return Karana(
        index=index_zero + 1,
        name=definition.name,
        longitude_delta=delta,
        progress=progress,
    )


def vaar_from_datetime(moment: datetime) -> Vaar:
    """Return the weekday metadata for ``moment``."""

    weekday = moment.weekday()
    definition = _vaar_definition((weekday + 1) % 7)
    index = ((weekday + 1) % 7) + 1
    return Vaar(index=index, weekday=weekday, name=definition.name, english=definition.english)


def panchang_from_chart(chart_or_context: NatalChart | VedicChartContext) -> Panchang:
    """Return pañchānga components derived from ``chart_or_context``."""

    chart = _resolve_chart(chart_or_context)
    moon_longitude = _body_longitude(chart, "Moon")
    sun_longitude = _body_longitude(chart, "Sun")

    tithi = tithi_from_longitudes(moon_longitude, sun_longitude)
    nakshatra = nakshatra_from_longitude(moon_longitude)
    yoga = yoga_from_longitudes(moon_longitude, sun_longitude)
    karana = karana_from_longitudes(moon_longitude, sun_longitude)
    vaar = vaar_from_datetime(chart.moment)

    return Panchang(tithi=tithi, nakshatra=nakshatra, yoga=yoga, karana=karana, vaar=vaar)
