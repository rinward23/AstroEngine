"""Lookup tables for horary house rulers and essential dignities."""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from ...scoring_legacy.dignity import load_dignities
from .models import DignityStatus
from .profiles import HoraryProfile

__all__ = [
    "SIGN_NAMES",
    "house_ruler",
    "sign_from_longitude",
    "degree_in_sign",
    "dignities_at",
    "reception_for",
]


SIGN_NAMES: tuple[str, ...] = (
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


def sign_from_longitude(longitude: float) -> str:
    idx = int((float(longitude) % 360.0) // 30.0)
    return SIGN_NAMES[idx]


def degree_in_sign(longitude: float) -> float:
    return float(longitude) % 30.0


def _title(name: str) -> str:
    return name.strip().title()


@lru_cache(maxsize=1)
def _build_dignity_tables() -> dict[str, object]:
    domiciles: dict[str, str] = {}
    detriments: dict[str, str] = {}
    falls: dict[str, str] = {}
    exaltations: dict[str, str] = {}
    trip_day: dict[str, str] = {}
    trip_night: dict[str, str] = {}
    trip_part: dict[str, str] = {}
    bounds: dict[str, list[tuple[float, float, str]]] = {sign: [] for sign in SIGN_NAMES}
    decans: dict[str, list[tuple[float, float, str]]] = {sign: [] for sign in SIGN_NAMES}

    for record in load_dignities():
        sign = _title(record.sign)
        planet = _title(record.planet)
        dtype = record.dignity_type.lower()
        if dtype == "rulership":
            domiciles[sign] = planet
        elif dtype == "detriment":
            detriments[sign] = planet
        elif dtype == "fall":
            falls[sign] = planet
        elif dtype == "exaltation":
            exaltations[sign] = planet
        elif dtype == "triplicity_day":
            trip_day[sign] = planet
        elif dtype == "triplicity_night":
            trip_night[sign] = planet
        elif dtype == "triplicity_participating":
            trip_part[sign] = planet
        elif dtype == "bounds_egyptian" and record.start_deg is not None:
            bounds[sign].append((record.start_deg, record.end_deg or 30.0, planet))
        elif dtype == "decans_chaldean" and record.start_deg is not None:
            decans[sign].append((record.start_deg, record.end_deg or 30.0, planet))

    for collection in (bounds, decans):
        for sign, items in collection.items():
            items.sort(key=lambda entry: entry[0])

    return {
        "domiciles": domiciles,
        "detriments": detriments,
        "falls": falls,
        "exaltations": exaltations,
        "triplicity_day": trip_day,
        "triplicity_night": trip_night,
        "triplicity_part": trip_part,
        "bounds": bounds,
        "decans": decans,
    }


def house_ruler(sign: str | int | float) -> str:
    """Return the domicile ruler for the supplied zodiac sign."""

    tables = _build_dignity_tables()
    if isinstance(sign, (int, float)):
        if isinstance(sign, int) and 1 <= sign <= 12:
            sign_name = SIGN_NAMES[int(sign) - 1]
        else:
            sign_name = sign_from_longitude(float(sign))
    else:
        sign_name = _title(sign)
    try:
        return tables["domiciles"][sign_name]
    except KeyError as exc:
        raise KeyError(f"Unknown sign '{sign}' for house ruler lookup") from exc


def _lookup_range(records: Iterable[tuple[float, float, str]], degree: float) -> str | None:
    for start, end, planet in records:
        if start <= degree < end:
            return planet
    return None


def _reception_candidates(sign: str, degree: float) -> dict[str, str | None]:
    tables = _build_dignity_tables()
    return {
        "domicile": tables["domiciles"].get(sign),
        "exaltation": tables["exaltations"].get(sign),
        "triplicity_day": tables["triplicity_day"].get(sign),
        "triplicity_night": tables["triplicity_night"].get(sign),
        "triplicity_part": tables["triplicity_part"].get(sign),
        "term": _lookup_range(tables["bounds"].get(sign, ()), degree),
        "face": _lookup_range(tables["decans"].get(sign, ()), degree),
        "detriment": tables["detriments"].get(sign),
        "fall": tables["falls"].get(sign),
    }


def dignities_at(
    body: str,
    longitude: float,
    *,
    profile: HoraryProfile,
    is_day_chart: bool,
) -> DignityStatus:
    """Return essential dignity metadata for ``body`` at ``longitude``."""

    body_name = _title(body)
    sign = sign_from_longitude(longitude)
    degree = degree_in_sign(longitude)
    info = _reception_candidates(sign, degree)

    if is_day_chart:
        triplicity = info.get("triplicity_day")
    else:
        triplicity = info.get("triplicity_night")
    if not triplicity:
        triplicity = info.get("triplicity_part")

    status = DignityStatus(
        domicile=info.get("domicile"),
        exaltation=info.get("exaltation"),
        triplicity=triplicity,
        term=info.get("term"),
        face=info.get("face"),
        detriment=info.get("detriment"),
        fall=info.get("fall"),
    )

    weights = profile.dignity_policy().weights
    score = 0.0
    if status.domicile == body_name:
        score += weights.get("domicile", 0.0)
    elif status.detriment == body_name:
        score += weights.get("detriment", 0.0)

    if status.exaltation == body_name:
        score += weights.get("exaltation", 0.0)
    elif status.fall == body_name:
        score += weights.get("fall", 0.0)

    if status.triplicity == body_name:
        score += weights.get("triplicity", 0.0)

    if status.term == body_name:
        score += weights.get("term", 0.0)

    if status.face == body_name:
        score += weights.get("face", 0.0)

    return DignityStatus(
        domicile=status.domicile,
        exaltation=status.exaltation,
        triplicity=status.triplicity,
        term=status.term,
        face=status.face,
        detriment=status.detriment,
        fall=status.fall,
        score=score,
    )


def reception_for(body: str, dignity: DignityStatus) -> tuple[str, ...]:
    """Return list of reception dignities offered to ``body`` by its dispositor."""

    target = _title(body)
    receptions: list[str] = []
    for key in ("domicile", "exaltation", "triplicity", "term", "face"):
        ruler = getattr(dignity, key)
        if ruler and ruler != target:
            receptions.append(key)
    return tuple(receptions)
