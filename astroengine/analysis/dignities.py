"""Lilly-style essential and accidental dignity scoring."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..chart.natal import NatalChart
from ..config import load_settings
from ..config.settings import DignitiesCfg
from ..detectors.ingresses import sign_index, sign_name
from ..engine.traditional.sect import sect_info
from ..jyotish.utils import degree_in_sign, house_index_for

__all__ = ["score_essential", "score_accidental", "condition_report"]


@dataclass(frozen=True)
class _DignitiesSettings:
    enabled: bool
    scoring: str


_TRIPLICITY_WEIGHTS: Mapping[str, int] = {
    "day": 3,
    "night": 3,
    "participating": 1,
}

_HOUSE_QUALITIES: Mapping[str, tuple[int, ...]] = {
    "angular": (1, 4, 7, 10),
    "succedent": (2, 5, 8, 11),
    "cadent": (3, 6, 9, 12),
}

_HOUSE_SCORES: Mapping[str, int] = {"angular": 5, "succedent": 2, "cadent": -5}

_DAY_PLANETS = {"sun", "jupiter", "saturn"}
_NIGHT_PLANETS = {"moon", "venus", "mars"}

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "dignities_lilly.json"


@lru_cache(maxsize=1)
def _load_dataset() -> Mapping[str, Any]:
    if not _DATA_PATH.exists():  # pragma: no cover - defensive
        raise FileNotFoundError(f"Dignities dataset not found at {_DATA_PATH}")
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "signs" not in data:
        raise ValueError("dignities_lilly.json missing 'signs' root key")
    return data


@lru_cache(maxsize=1)
def _dignities_config() -> _DignitiesSettings:
    try:
        settings = load_settings()
        cfg: DignitiesCfg = getattr(settings, "dignities", DignitiesCfg())
    except Exception:  # pragma: no cover - settings fallback
        cfg = DignitiesCfg()
    return _DignitiesSettings(enabled=bool(cfg.enabled), scoring=str(cfg.scoring))


def _normalize_planet(planet: str) -> str:
    return planet.strip().lower()


def _sign_payload(longitude: float) -> tuple[str, Mapping[str, Any], float]:
    dataset = _load_dataset()
    idx = sign_index(longitude)
    sign_key = sign_name(idx).lower()
    sign_data = dataset["signs"].get(sign_key)
    if not sign_data:
        raise KeyError(f"No dignity data available for sign '{sign_key}'")
    return sign_key, sign_data, degree_in_sign(longitude)


def _segment_for(degree: float, segments: Iterable[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for segment in segments:
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", 30.0))
        if start <= degree < end or (degree == 30.0 and end == 30.0):
            return segment
    return None


def _triplicity_component(
    planet_key: str, triplicity: Mapping[str, Any], is_day: bool | None
) -> dict[str, Any]:
    component = {
        "name": "triplicity",
        "applies": False,
        "role": None,
        "ruler": None,
        "score": 0,
        "rulers": {
            role: (str(ruler).title() if ruler else None)
            for role, ruler in triplicity.items()
        },
    }

    roles: tuple[str, ...]
    if is_day is None:
        roles = ("day", "night", "participating")
    else:
        roles = ("day", "participating") if is_day else ("night", "participating")

    for role in roles:
        ruler = triplicity.get(role)
        if not ruler:
            continue
        if planet_key == str(ruler).lower():
            component.update(
                {
                    "applies": True,
                    "role": role,
                    "ruler": str(ruler).title(),
                    "score": _TRIPLICITY_WEIGHTS.get(role, 0),
                }
            )
            return component

    # If sect-specific role failed but the planet matches another ruler, record it
    for role in ("day", "night", "participating"):
        ruler = triplicity.get(role)
        if ruler and planet_key == str(ruler).lower():
            component.update(
                {
                    "applies": True,
                    "role": role,
                    "ruler": str(ruler).title(),
                    "score": _TRIPLICITY_WEIGHTS.get(role, 0),
                }
            )
            break
    return component


def _essential_components(
    planet: str, longitude: float, *, is_day: bool | None
) -> list[dict[str, Any]]:
    planet_key = _normalize_planet(planet)
    _, sign_data, degree = _sign_payload(longitude)
    components: list[dict[str, Any]] = []

    rulers = [str(r).title() for r in sign_data.get("rulers", [])]
    domicile = {
        "name": "domicile",
        "applies": planet_key in {r.lower() for r in rulers},
        "rulers": rulers,
        "score": 5 if planet_key in {r.lower() for r in rulers} else 0,
    }
    components.append(domicile)

    detriments = [str(r).title() for r in sign_data.get("detriments", [])]
    detriment = {
        "name": "detriment",
        "applies": planet_key in {r.lower() for r in detriments},
        "rulers": detriments,
        "score": -5 if planet_key in {r.lower() for r in detriments} else 0,
    }
    components.append(detriment)

    exalt = sign_data.get("exaltation")
    exalt_planet = str(exalt.get("planet")).title() if exalt and exalt.get("planet") else None
    exalt_component = {
        "name": "exaltation",
        "applies": bool(exalt_planet and planet_key == exalt_planet.lower()),
        "planet": exalt_planet,
        "degree": float(exalt.get("degree", 0.0)) if exalt and exalt.get("degree") else None,
        "score": 4 if exalt_planet and planet_key == exalt_planet.lower() else 0,
    }
    components.append(exalt_component)

    fall = sign_data.get("fall")
    fall_planet = str(fall.get("planet")).title() if fall and fall.get("planet") else None
    fall_component = {
        "name": "fall",
        "applies": bool(fall_planet and planet_key == fall_planet.lower()),
        "planet": fall_planet,
        "degree": float(fall.get("degree", 0.0)) if fall and fall.get("degree") else None,
        "score": -4 if fall_planet and planet_key == fall_planet.lower() else 0,
    }
    components.append(fall_component)

    triplicity = sign_data.get("triplicity", {})
    components.append(_triplicity_component(planet_key, triplicity, is_day))

    term_segment = _segment_for(degree, sign_data.get("terms", ()))
    term_ruler = (
        str(term_segment.get("ruler")).title()
        if term_segment and term_segment.get("ruler")
        else None
    )
    term_component = {
        "name": "term",
        "applies": bool(term_ruler and planet_key == term_ruler.lower()),
        "ruler": term_ruler,
        "range": (
            [float(term_segment.get("start", 0.0)), float(term_segment.get("end", 30.0))]
            if term_segment
            else None
        ),
        "score": 2 if term_ruler and planet_key == term_ruler.lower() else 0,
    }
    components.append(term_component)

    face_segment = _segment_for(degree, sign_data.get("faces", ()))
    face_ruler = (
        str(face_segment.get("ruler")).title()
        if face_segment and face_segment.get("ruler")
        else None
    )
    face_component = {
        "name": "face",
        "applies": bool(face_ruler and planet_key == face_ruler.lower()),
        "ruler": face_ruler,
        "range": (
            [float(face_segment.get("start", 0.0)), float(face_segment.get("end", 30.0))]
            if face_segment
            else None
        ),
        "score": 1 if face_ruler and planet_key == face_ruler.lower() else 0,
    }
    components.append(face_component)

    return components


def _house_quality(house_idx: int) -> str:
    idx = ((int(house_idx) - 1) % 12) + 1
    for label, indices in _HOUSE_QUALITIES.items():
        if idx in indices:
            return label
    return "cadent"


def _sect_component(planet: str, sect: str) -> dict[str, Any]:
    planet_key = _normalize_planet(planet)
    sect_label = sect.strip().lower()
    if sect_label not in {"day", "night"}:
        sect_label = "day"

    if planet_key == "mercury":
        return {
            "name": "sect",
            "alignment": "neutral",
            "applies": False,
            "score": 0,
        }

    if sect_label == "day":
        if planet_key in _DAY_PLANETS:
            return {
                "name": "sect",
                "alignment": "in_sect",
                "applies": True,
                "score": 3,
            }
        if planet_key in _NIGHT_PLANETS:
            return {
                "name": "sect",
                "alignment": "out_of_sect",
                "applies": True,
                "score": -3,
            }
    else:  # night chart
        if planet_key in _NIGHT_PLANETS:
            return {
                "name": "sect",
                "alignment": "in_sect",
                "applies": True,
                "score": 3,
            }
        if planet_key in _DAY_PLANETS:
            return {
                "name": "sect",
                "alignment": "out_of_sect",
                "applies": True,
                "score": -3,
            }

    return {
        "name": "sect",
        "alignment": "neutral",
        "applies": False,
        "score": 0,
    }


def _accidental_components(
    planet: str, retrograde: bool, house_idx: int, sect: str
) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []

    quality = _house_quality(house_idx)
    components.append(
        {
            "name": "house",
            "quality": quality,
            "house": int(((house_idx - 1) % 12) + 1),
            "score": _HOUSE_SCORES.get(quality, 0),
        }
    )

    components.append(
        {
            "name": "motion",
            "state": "retrograde" if retrograde else "direct",
            "applies": retrograde,
            "score": -5 if retrograde else 0,
        }
    )

    components.append(_sect_component(planet, sect))
    return components


def score_essential(planet: str, lon: float) -> int:
    """Return the Lilly essential dignity score for ``planet`` at longitude ``lon``."""

    cfg = _dignities_config()
    if not cfg.enabled:
        return 0
    if cfg.scoring != "lilly":
        raise ValueError(f"Unsupported dignities scoring mode '{cfg.scoring}'")

    components = _essential_components(planet, lon, is_day=None)
    return int(sum(int(comp.get("score", 0)) for comp in components))


def score_accidental(planet: str, retrograde: bool, house_idx: int, sect: str) -> int:
    """Return Lilly accidental dignity score for ``planet``."""

    cfg = _dignities_config()
    if not cfg.enabled:
        return 0
    if cfg.scoring != "lilly":
        raise ValueError(f"Unsupported dignities scoring mode '{cfg.scoring}'")

    components = _accidental_components(planet, retrograde, house_idx, sect)
    return int(sum(int(comp.get("score", 0)) for comp in components))


def _chart_sect(chart: NatalChart) -> tuple[str, Mapping[str, Any]]:
    moment = chart.moment
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        moment = moment.replace(tzinfo=UTC)
    info = sect_info(moment, chart.location)
    label = "day" if info.is_day else "night"
    payload = {
        "is_day": bool(info.is_day),
        "label": label,
        "luminary": info.luminary_of_sect,
        "benefic": info.benefic_of_sect,
        "malefic": info.malefic_of_sect,
        "sun_altitude_deg": float(info.sun_altitude_deg),
    }
    return label, payload


def condition_report(chart: NatalChart) -> dict[str, Any]:
    """Return essential/accidental dignity breakdown for ``chart`` planets."""

    cfg = _dignities_config()
    report: dict[str, Any] = {
        "settings": {"enabled": cfg.enabled, "scoring": cfg.scoring},
        "planets": OrderedDict(),
        "totals": {"essential": 0, "accidental": 0, "overall": 0},
    }

    if not cfg.enabled:
        return report
    if cfg.scoring != "lilly":
        raise ValueError(f"Unsupported dignities scoring mode '{cfg.scoring}'")

    sect_label, sect_payload = _chart_sect(chart)
    moment = chart.moment
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        moment = moment.replace(tzinfo=UTC)

    chart_info = {
        "moment": moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "location": {
            "latitude": float(chart.location.latitude),
            "longitude": float(chart.location.longitude),
        },
        "house_system": chart.houses.system,
        "sect": sect_payload,
        "ascendant": float(chart.houses.ascendant),
        "midheaven": float(chart.houses.midheaven),
    }
    report["chart"] = chart_info

    total_essential = 0
    total_accidental = 0

    for planet, position in chart.positions.items():
        longitude = float(position.longitude)
        retrograde = float(position.speed_longitude) < 0
        house_idx = house_index_for(longitude, chart.houses)
        components_ess = _essential_components(planet, longitude, is_day=(sect_label == "day"))
        components_acc = _accidental_components(planet, retrograde, house_idx, sect_label)

        essential_score = int(sum(int(comp.get("score", 0)) for comp in components_ess))
        accidental_score = int(sum(int(comp.get("score", 0)) for comp in components_acc))

        total_essential += essential_score
        total_accidental += accidental_score

        planet_payload = {
            "longitude": longitude,
            "sign": sign_name(sign_index(longitude)),
            "degree_in_sign": degree_in_sign(longitude),
            "house": int(house_idx),
            "retrograde": retrograde,
            "essential": {"score": essential_score, "components": components_ess},
            "accidental": {"score": accidental_score, "components": components_acc},
            "total": essential_score + accidental_score,
        }
        report["planets"][planet] = planet_payload

    report["totals"] = {
        "essential": total_essential,
        "accidental": total_accidental,
        "overall": total_essential + total_accidental,
    }
    return report


def _clear_caches() -> None:  # pragma: no cover - debugging helper
    _dignities_config.cache_clear()
    _load_dataset.cache_clear()
