"""Optional adapters linking planetary data to tarot and numerology prompts."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from astroengine.utils.i18n import translate

from .numerology import MASTER_NUMBERS, NUMEROLOGY_NUMBERS, NumerologyNumber
from .tarot import TAROT_MAJORS

_ZODIAC_SIGNS = (
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

__all__ = ["tarot_mapper", "numerology_mapper"]


def _keywords_snippet(keywords: Iterable[str]) -> str:
    return ", ".join(list(keywords)[:3])


def _major_for_attribution(target: str) -> Any:
    target_lower = target.lower()
    for card in TAROT_MAJORS:
        if card.attribution.lower() == target_lower:
            return card
    return None


def tarot_mapper(
    *,
    planet: str | None = None,
    sign: str | None = None,
    house: int | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return tarot correspondences for the supplied placements."""

    payload: dict[str, Any] = {
        "disclaimer": translate("esoteric.tarot.disclaimer", locale=locale),
    }

    if planet:
        card = _major_for_attribution(planet)
        if card:
            payload["planet"] = {
                "target": planet,
                "card": card.name,
                "prompt": translate(
                    "esoteric.tarot.planet.prompt",
                    locale=locale,
                    planet=planet,
                    card=card.name,
                    keywords=_keywords_snippet(card.keywords),
                ),
            }
        else:
            payload["planet"] = {
                "target": planet,
                "card": None,
                "prompt": translate(
                    "esoteric.tarot.missing",
                    locale=locale,
                    target=planet,
                ),
            }

    if sign:
        card = _major_for_attribution(sign)
        if card:
            payload["sign"] = {
                "target": sign,
                "card": card.name,
                "prompt": translate(
                    "esoteric.tarot.sign.prompt",
                    locale=locale,
                    sign=sign,
                    card=card.name,
                    keywords=_keywords_snippet(card.keywords),
                ),
            }
        else:
            payload["sign"] = {
                "target": sign,
                "card": None,
                "prompt": translate(
                    "esoteric.tarot.missing",
                    locale=locale,
                    target=sign,
                ),
            }

    if house is not None:
        if 1 <= house <= 12:
            zodiac_sign = _ZODIAC_SIGNS[(house - 1) % len(_ZODIAC_SIGNS)]
            card = _major_for_attribution(zodiac_sign)
            if card:
                payload["house"] = {
                    "target": int(house),
                    "card": card.name,
                    "prompt": translate(
                        "esoteric.tarot.house.prompt",
                        locale=locale,
                        house=house,
                        card=card.name,
                        keywords=_keywords_snippet(card.keywords),
                    ),
                }
            else:
                payload["house"] = {
                    "target": int(house),
                    "card": None,
                    "prompt": translate(
                        "esoteric.tarot.missing",
                        locale=locale,
                        target=f"House {house}",
                    ),
                }
        else:
            payload["house"] = {
                "target": house,
                "card": None,
                "prompt": translate(
                    "esoteric.tarot.missing",
                    locale=locale,
                    target=f"House {house}",
                ),
            }

    return payload


def _digit_sum(value: int) -> int:
    return sum(int(ch) for ch in str(abs(value)))


def _reduce_number(value: int) -> int:
    while value > 9 and value not in {11, 22, 33}:
        value = _digit_sum(value)
    return value


def _lookup_number(value: int) -> NumerologyNumber | None:
    for table in (MASTER_NUMBERS, NUMEROLOGY_NUMBERS):
        for entry in table:
            if entry.value == value:
                return entry
    if value > 9:
        return _lookup_number(_reduce_number(value))
    return None


def _numerology_payload(
    *,
    label_key: str,
    value: int,
    raw: int,
    locale: str | None = None,
) -> dict[str, Any]:
    entry = _lookup_number(value)
    return {
        "label": translate(label_key, locale=locale),
        "value": value,
        "is_master": value in {11, 22, 33},
        "name": entry.name if entry else None,
        "planetary_ruler": entry.planetary_ruler if entry else None,
        "keywords": list(entry.keywords) if entry else [],
        "calculation": {
            translate("esoteric.numerology.calculation", locale=locale): {
                "raw": raw,
                "reduced": _reduce_number(raw),
            }
        },
    }


def numerology_mapper(
    date_of_birth: date,
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Return core numerology numbers derived from *date_of_birth*."""

    month = date_of_birth.month
    day = date_of_birth.day
    year = date_of_birth.year

    life_path_raw = _digit_sum(year) + _digit_sum(month) + _digit_sum(day)
    life_path = _reduce_number(life_path_raw)

    birth_day = _reduce_number(day)
    attitude_raw = month + day
    attitude = _reduce_number(attitude_raw)

    return {
        "disclaimer": translate("esoteric.numerology.disclaimer", locale=locale),
        "life_path": _numerology_payload(
            label_key="esoteric.numerology.label.life_path",
            value=life_path,
            raw=life_path_raw,
            locale=locale,
        ),
        "birth_day": _numerology_payload(
            label_key="esoteric.numerology.label.birth_day",
            value=birth_day,
            raw=day,
            locale=locale,
        ),
        "attitude": _numerology_payload(
            label_key="esoteric.numerology.label.attitude",
            value=attitude,
            raw=attitude_raw,
            locale=locale,
        ),
    }

