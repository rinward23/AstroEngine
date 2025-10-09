"""Detection utilities for prominent Vedic yogas.

This module inspects a :class:`~astroengine.engine.vedic.chart.VedicChartContext`
and reports classical yoga configurations together with supporting
diagnostics.  The implementation keeps the existing module → submodule
hierarchy by living under ``astroengine.engine.vedic`` and mirrors the
metadata-rich style used elsewhere in the engine.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache

from ...detectors.ingresses import ZODIAC_SIGNS, sign_index
from ...engine.horary.rulers import house_ruler
from ...scoring_legacy.dignity import load_dignities
from ...vca.houses import house_of
from .chart import VedicChartContext

KENDRA_HOUSES: frozenset[int] = frozenset({1, 4, 7, 10})
DUSTHANA_HOUSES: frozenset[int] = frozenset({6, 8, 12})
ANGULAR_SET = KENDRA_HOUSES
SUCCEDENT_SET = frozenset({2, 5, 8, 11})


@dataclass(frozen=True)
class PlanetStrength:
    """Snapshot of a planet's placement, dignity, and house ownership."""

    name: str
    longitude: float
    sign: str
    sign_index: int
    house: int
    house_class: str
    retrograde: bool
    combust: bool
    dignity: Mapping[str, bool]
    dignity_label: str | None
    dispositor: str | None
    ruled_houses: tuple[int, ...]

    def dignity_flags(self) -> Mapping[str, bool]:
        return dict(self.dignity)


@dataclass(frozen=True)
class YogaResult:
    """Structured description of a triggered yoga."""

    name: str
    category: str
    participants: tuple[PlanetStrength, ...]
    checks: Mapping[str, Mapping[str, object]]
    notes: tuple[str, ...] = ()


def _title(name: str) -> str:
    token = (name or "").strip()
    if not token:
        return token
    if token.lower() in {"rahu", "ketu"}:
        return token.title()
    return token[0].upper() + token[1:].lower()


def _wrap_angle(delta: float) -> float:
    value = delta % 360.0
    if value > 180.0:
        value -= 360.0
    return value


def _separation(a: float, b: float) -> float:
    return abs(_wrap_angle(float(a) - float(b)))


def _house_class(house: int) -> str:
    if house in ANGULAR_SET:
        return "angular"
    if house in SUCCEDENT_SET:
        return "succedent"
    return "cadent"


@lru_cache(maxsize=1)
def _load_sign_dignities() -> dict[str, dict[str, str]]:
    """Return a mapping of sign → dignity allocations for quick lookups."""

    data: dict[str, dict[str, str]] = {
        sign: {"domicile": "", "detriment": "", "exaltation": "", "fall": ""}
        for sign in ZODIAC_SIGNS
    }
    for record in load_dignities():
        sign = _title(record.sign)
        if sign not in data:
            continue
        kind = record.dignity_type.lower()
        planet = _title(record.planet)
        if kind == "rulership":
            data[sign]["domicile"] = planet
        elif kind == "detriment":
            data[sign]["detriment"] = planet
        elif kind == "exaltation":
            data[sign]["exaltation"] = planet
        elif kind == "fall":
            data[sign]["fall"] = planet
    return data


def _dignity_for(planet: str, sign: str) -> tuple[dict[str, bool], str | None]:
    table = _load_sign_dignities().get(sign, {})
    domicile = table.get("domicile") == planet
    exaltation = table.get("exaltation") == planet
    detriment = table.get("detriment") == planet
    fall = table.get("fall") == planet
    label: str | None
    if exaltation:
        label = "exaltation"
    elif domicile:
        label = "own_sign"
    elif fall:
        label = "debilitation"
    elif detriment:
        label = "detriment"
    else:
        label = None
    return (
        {
            "domicile": domicile,
            "exaltation": exaltation,
            "detriment": detriment,
            "fall": fall,
        },
        label,
    )


def _house_lords(ascendant: float) -> dict[int, str]:
    asc_sign_index = sign_index(ascendant)
    lords: dict[int, str] = {}
    for offset in range(12):
        house_num = offset + 1
        sign = ZODIAC_SIGNS[(asc_sign_index + offset) % 12]
        try:
            ruler = house_ruler(sign)
        except KeyError:
            ruler = ""
        lords[house_num] = _title(ruler)
    return lords


def _ruled_houses_for(planet: str, house_lords: Mapping[int, str]) -> tuple[int, ...]:
    owned = [house for house, ruler in house_lords.items() if ruler == planet]
    return tuple(sorted(owned))


def _planet_strengths(
    ctx: VedicChartContext,
    *,
    consider: Iterable[str] = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
    combust_threshold: float = 8.0,
) -> dict[str, PlanetStrength]:
    chart = ctx.chart
    house_map = _house_lords(chart.houses.ascendant)
    sun = chart.positions.get("Sun")
    sun_lon = float(sun.longitude) if sun else 0.0
    strengths: dict[str, PlanetStrength] = {}
    for name in consider:
        position = chart.positions.get(name)
        if position is None:
            continue
        sign_idx = sign_index(position.longitude)
        sign = ZODIAC_SIGNS[sign_idx]
        system = ctx.config.house_system or "whole_sign"
        try:
            house = house_of(chart, name, system)
        except Exception:
            continue
        dignity, label = _dignity_for(name, sign)
        try:
            dispositor = house_ruler(sign) if sign in ZODIAC_SIGNS else None
        except KeyError:
            dispositor = None
        dispositor = _title(dispositor) if dispositor else None
        strengths[name] = PlanetStrength(
            name=name,
            longitude=float(position.longitude),
            sign=sign,
            sign_index=sign_idx,
            house=house,
            house_class=_house_class(house),
            retrograde=position.speed_longitude < 0,
            combust=_separation(position.longitude, sun_lon) <= combust_threshold if name != "Sun" else False,
            dignity=dignity,
            dignity_label=label,
            dispositor=dispositor,
            ruled_houses=_ruled_houses_for(name, house_map),
        )
    return strengths


def _is_kendra_from(reference: int, target: int) -> bool:
    diff = (target - reference) % 12
    return diff in (0, 3, 6, 9)


def _collect_panch_mahapurusha(strengths: Mapping[str, PlanetStrength]) -> list[YogaResult]:
    yogas: list[YogaResult] = []
    mapping = {
        "Mars": "Ruchaka",
        "Mercury": "Bhadra",
        "Jupiter": "Hamsa",
        "Venus": "Malavya",
        "Saturn": "Shasha",
    }
    for planet, label in mapping.items():
        status = strengths.get(planet)
        if not status:
            continue
        if status.house not in KENDRA_HOUSES:
            continue
        if not (status.dignity.get("domicile") or status.dignity.get("exaltation")):
            continue
        if status.dignity.get("fall") or status.dignity.get("detriment"):
            continue
        if status.combust:
            continue
        checks = {
            "strength": {
                "house_class": status.house_class,
                "retrograde": status.retrograde,
                "combust": status.combust,
            },
            "dignity": status.dignity_flags(),
            "lordship": {
                "dispositor": status.dispositor,
            },
            "house_ownership": {
                "ruled_houses": status.ruled_houses,
            },
        }
        yogas.append(
            YogaResult(
                name=f"{label} Yoga",
                category="panch_mahapurusha",
                participants=(status,),
                checks=checks,
            )
        )
    return yogas


def _collect_neech_bhang(
    strengths: Mapping[str, PlanetStrength],
    *,
    moon: PlanetStrength | None,
) -> list[YogaResult]:
    yogas: list[YogaResult] = []
    moon_index = moon.sign_index if moon else None
    for status in strengths.values():
        if not status.dignity.get("fall"):
            continue
        if not status.dispositor:
            continue
        disposer = strengths.get(status.dispositor)
        if disposer is None:
            continue
        kendra_from_lagna = disposer.house in KENDRA_HOUSES
        kendra_from_moon = (
            moon_index is not None
            and _is_kendra_from(moon_index, disposer.sign_index)
        )
        disposer_strong = disposer.dignity.get("domicile") or disposer.dignity.get("exaltation")
        if not (kendra_from_lagna or kendra_from_moon or disposer_strong):
            continue
        checks = {
            "strength": {
                "dispositor_house": disposer.house,
                "dispositor_house_class": disposer.house_class,
            },
            "dignity": {
                **status.dignity_flags(),
                "dispositor": disposer.dignity_flags(),
            },
            "lordship": {
                "dispositor": disposer.name,
                "debilitated_planet": status.name,
            },
            "house_ownership": {
                "debilitated_house": status.house,
                "dispositor_ruled_houses": disposer.ruled_houses,
            },
        }
        notes: list[str] = []
        if disposer_strong:
            notes.append("Dispositor dignified")
        if kendra_from_lagna:
            notes.append("Dispositor in kendra from ascendant")
        if kendra_from_moon:
            notes.append("Dispositor in kendra from Moon")
        yogas.append(
            YogaResult(
                name="Neech Bhang Raj Yoga",
                category="cancellation",
                participants=(status, disposer),
                checks=checks,
                notes=tuple(notes),
            )
        )
    return yogas


def _collect_kemadruma(strengths: Mapping[str, PlanetStrength]) -> list[YogaResult]:
    moon = strengths.get("Moon")
    if not moon:
        return []
    neighbors: list[str] = []
    kendra_from_moon: list[str] = []
    for planet, status in strengths.items():
        if planet == "Moon":
            continue
        diff = (status.sign_index - moon.sign_index) % 12
        if diff in (1, 11):
            neighbors.append(planet)
        if diff in (0, 3, 6, 9):
            kendra_from_moon.append(planet)
    if neighbors:
        return []
    checks = {
        "strength": {
            "moon_house": moon.house,
            "moon_house_class": moon.house_class,
        },
        "dignity": moon.dignity_flags(),
        "lordship": {
            "moon_dispositor": moon.dispositor,
        },
        "house_ownership": {
            "moon_rules": moon.ruled_houses,
        },
        "absence": {
            "adjacent_planets": tuple(neighbors),
            "kendra_from_moon": tuple(kendra_from_moon),
        },
    }
    return [
        YogaResult(
            name="Kemadruma Yoga",
            category="moon_affliction",
            participants=(moon,),
            checks=checks,
        )
    ]


def _collect_daridra(
    strengths: Mapping[str, PlanetStrength],
    house_lords: Mapping[int, str],
) -> list[YogaResult]:
    eleventh_lord = house_lords.get(11)
    if not eleventh_lord:
        return []
    lord_status = strengths.get(eleventh_lord)
    if not lord_status:
        return []
    if lord_status.house not in DUSTHANA_HOUSES:
        return []
    if lord_status.dignity.get("domicile") or lord_status.dignity.get("exaltation"):
        return []
    checks = {
        "strength": {
            "house": lord_status.house,
            "house_class": lord_status.house_class,
        },
        "dignity": lord_status.dignity_flags(),
        "lordship": {
            "eleventh_lord": eleventh_lord,
        },
        "house_ownership": {
            "ruled_houses": lord_status.ruled_houses,
        },
    }
    return [
        YogaResult(
            name="Daridra Yoga",
            category="financial",
            participants=(lord_status,),
            checks=checks,
        )
    ]


def _collect_bhandhan(
    strengths: Mapping[str, PlanetStrength],
    house_lords: Mapping[int, str],
) -> list[YogaResult]:
    lagna_lord = house_lords.get(1)
    if not lagna_lord:
        return []
    lagna_status = strengths.get(lagna_lord)
    if not lagna_status:
        return []
    malefics = [
        strengths.get("Mars"),
        strengths.get("Saturn"),
    ]
    malefics_in_kendra = [status for status in malefics if status and status.house in KENDRA_HOUSES]
    if not malefics_in_kendra:
        return []
    lagna_weak = lagna_status.house in DUSTHANA_HOUSES or lagna_status.dignity.get("fall") or lagna_status.dignity.get("detriment")
    if not lagna_weak:
        return []
    checks = {
        "strength": {
            "malefics_in_kendra": tuple((status.name, status.house) for status in malefics_in_kendra),
            "lagna_lord_house": lagna_status.house,
        },
        "dignity": {
            **lagna_status.dignity_flags(),
        },
        "lordship": {
            "lagna_lord": lagna_lord,
        },
        "house_ownership": {
            "lagna_lord_rules": lagna_status.ruled_houses,
        },
    }
    return [
        YogaResult(
            name="Bhandhan Yoga",
            category="imprisonment",
            participants=(lagna_status, *tuple(malefics_in_kendra)),
            checks=checks,
        )
    ]


def analyze_yogas(context: VedicChartContext) -> tuple[YogaResult, ...]:
    """Return detected yogas for ``context`` with diagnostic metadata."""

    strengths = _planet_strengths(context)
    if not strengths:
        return ()
    house_lords = _house_lords(context.chart.houses.ascendant)
    moon = strengths.get("Moon")
    results: list[YogaResult] = []
    results.extend(_collect_panch_mahapurusha(strengths))
    results.extend(_collect_neech_bhang(strengths, moon=moon))
    results.extend(_collect_kemadruma(strengths))
    results.extend(_collect_daridra(strengths, house_lords))
    results.extend(_collect_bhandhan(strengths, house_lords))
    return tuple(results)


__all__ = ["PlanetStrength", "YogaResult", "analyze_yogas"]
